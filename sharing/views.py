import mimetypes

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.db.models import F
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import ShareCodeForm, UploadForm
from .models import ActivityLog, SharedFile, SiteSettings
from .pagination import paginate
from .services import (
    can_download,
    can_manage_file,
    can_upload,
    get_client_ip,
    lockout_remaining,
    log_activity,
    register_failed_lookup,
    reset_failed_lookups,
)

SESSION_LAST_UPLOAD = "last_upload_ids"


def home(request):
    return render(request, "sharing/home.html", {"code_form": ShareCodeForm()})


def upload(request):
    if not can_upload(request.user):
        messages.info(request, "Please sign in to upload files.")
        return redirect_to_login(request.get_full_path())

    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        ip = get_client_ip(request)
        user = request.user if request.user.is_authenticated else None
        created = []
        for f in form.cleaned_data["files"]:
            content_type = getattr(f, "content_type", "") or mimetypes.guess_type(f.name)[0] or ""
            shared = SharedFile(
                original_name=f.name[:255],
                content_type=content_type[:127],
                size=f.size,
                uploaded_by=user,
                uploader_ip=ip,
            )
            shared.file.save(f.name, f, save=False)
            shared.save()
            log_activity(request, ActivityLog.Action.UPLOAD, shared)
            created.append(shared.pk)
        request.session[SESSION_LAST_UPLOAD] = created
        return redirect("sharing:upload_done")

    return render(request, "sharing/upload.html", {"form": form, "max_mb": settings.FILESHARE_MAX_UPLOAD_MB})


def upload_done(request):
    ids = request.session.get(SESSION_LAST_UPLOAD) or []
    files = SharedFile.objects.filter(pk__in=ids)
    if not files:
        return redirect("sharing:upload")
    return render(request, "sharing/upload_done.html", {"files": files})


def find_file(request):
    """Form where someone pastes a share code (or link)."""
    form = ShareCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        return redirect("sharing:file_detail", code=form.cleaned_data["code"])
    return render(request, "sharing/find.html", {"form": form, "lockout": lockout_remaining(request)})


def _resolve_code(request, code):
    """Look up a share code with brute-force protection.

    Returns (shared_file, error_response). Exactly one is not None.
    """
    wait = lockout_remaining(request)
    if wait:
        messages.error(request, f"Too many invalid codes. Try again in {wait} seconds.")
        return None, redirect("sharing:find")

    shared = SharedFile.objects.filter(share_code=code).select_related("uploaded_by").first()
    if shared is None:
        attempts_left, lockout = register_failed_lookup(request)
        log_activity(request, ActivityLog.Action.FAILED_LOOKUP, share_code=code[:64],
                     details=f"{attempts_left} attempts left")
        if lockout:
            messages.error(request, f"Invalid code. Too many failed attempts — locked for {lockout} seconds.")
        else:
            messages.error(request, f"Invalid code. {attempts_left} attempt(s) left before a temporary lockout.")
        return None, redirect("sharing:find")

    reset_failed_lookups(request)
    return shared, None


def file_detail(request, code):
    if not can_download(request.user):
        messages.info(request, "Please sign in to download files.")
        return redirect_to_login(request.get_full_path())
    shared, error = _resolve_code(request, code)
    if error:
        return error
    share_url = request.build_absolute_uri(reverse("sharing:file_detail", args=[shared.share_code]))
    return render(request, "sharing/file_detail.html", {
        "file": shared,
        "share_url": share_url,
        "can_manage": can_manage_file(request.user, shared),
    })


def download(request, code):
    if not can_download(request.user):
        messages.info(request, "Please sign in to download files.")
        return redirect_to_login(reverse("sharing:file_detail", args=[code]))
    shared, error = _resolve_code(request, code)
    if error:
        return error
    try:
        handle = shared.file.open("rb")
    except FileNotFoundError:
        raise Http404("The stored file is missing.")

    SharedFile.objects.filter(pk=shared.pk).update(
        download_count=F("download_count") + 1, last_downloaded_at=timezone.now()
    )
    log_activity(request, ActivityLog.Action.DOWNLOAD, shared)
    return FileResponse(
        handle,
        as_attachment=True,
        filename=shared.original_name,
        content_type=shared.content_type or "application/octet-stream",
    )


@login_required
def my_files(request):
    files = SharedFile.objects.filter(uploaded_by=request.user)
    page, query = paginate(request, files)
    return render(request, "sharing/my_files.html", {"page": page, "query": query})


@require_POST
@login_required
def delete_file(request, pk):
    shared = get_object_or_404(SharedFile, pk=pk)
    if not can_manage_file(request.user, shared):
        raise Http404
    log_activity(request, ActivityLog.Action.DELETE, shared,
                 details=f"Uploaded by {shared.uploader_display} on {shared.created_at:%Y-%m-%d}")
    name = shared.original_name
    shared.delete()
    shared.delete_file_from_disk()
    messages.success(request, f"Deleted “{name}”.")
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}, request.is_secure()):
        return redirect(next_url)
    return redirect("sharing:my_files")
