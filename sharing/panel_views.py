"""Admin panel: dashboard, all files, activity logs, access settings, cleanup."""

from datetime import timedelta

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.template.defaultfilters import filesizeformat
from django.utils import timezone

from accounts.decorators import admin_required
from accounts.models import User

from .forms import CleanupForm, FileSearchForm, LogFilterForm, SiteSettingsForm
from .models import ActivityLog, SharedFile, SiteSettings
from .pagination import paginate
from .services import delete_shared_files, log_activity, old_files_queryset


@admin_required
def dashboard(request):
    since = timezone.now() - timedelta(days=7)
    totals = SharedFile.objects.aggregate(count=Count("id"), size=Sum("size"))
    week = ActivityLog.objects.filter(created_at__gte=since)
    context = {
        "file_count": totals["count"] or 0,
        "storage_used": totals["size"] or 0,
        "user_count": User.objects.count(),
        "admin_count": User.objects.filter(role=User.Role.ADMIN).count(),
        "uploads_week": week.filter(action=ActivityLog.Action.UPLOAD).count(),
        "downloads_week": week.filter(action=ActivityLog.Action.DOWNLOAD).count(),
        "failed_week": week.filter(action=ActivityLog.Action.FAILED_LOOKUP).count(),
        "recent_logs": ActivityLog.objects.all()[:10],
    }
    return render(request, "panel/dashboard.html", context)


@admin_required
def files(request):
    form = FileSearchForm(request.GET or None)
    qs = SharedFile.objects.select_related("uploaded_by")
    if form.is_valid() and form.cleaned_data["q"]:
        q = form.cleaned_data["q"].strip()
        qs = qs.filter(
            Q(original_name__icontains=q)
            | Q(share_code=q)
            | Q(uploaded_by__username__icontains=q)
            | Q(uploader_ip__startswith=q)
        )
    page, query = paginate(request, qs)
    return render(request, "panel/files.html", {"form": form, "page": page, "query": query})


@admin_required
def logs(request):
    form = LogFilterForm(request.GET or None)
    qs = ActivityLog.objects.all()
    if form.is_valid():
        if form.cleaned_data["action"]:
            qs = qs.filter(action=form.cleaned_data["action"])
        q = form.cleaned_data["q"].strip()
        if q:
            qs = qs.filter(
                Q(file_name__icontains=q)
                | Q(share_code=q)
                | Q(username__icontains=q)
                | Q(ip_address__startswith=q)
            )
    page, query = paginate(request, qs)
    return render(request, "panel/logs.html", {"form": form, "page": page, "query": query})


@admin_required
def site_settings(request):
    site = SiteSettings.load()
    form = SiteSettingsForm(request.POST or None, instance=site)
    if request.method == "POST" and form.is_valid():
        site = form.save(commit=False)
        site.updated_by = request.user
        site.save()
        log_activity(
            request,
            ActivityLog.Action.SETTINGS,
            details=f"public_upload={site.public_upload}, public_download={site.public_download}",
        )
        messages.success(request, "Access settings saved.")
        return redirect("panel:settings")
    return render(request, "panel/settings.html", {"form": form, "site": site})


@admin_required
def cleanup(request):
    form = CleanupForm(request.POST or request.GET or None)
    preview = None
    if form.is_valid():
        days = form.cleaned_data["days"]
        qs = old_files_queryset(days)
        if request.method == "POST" and request.POST.get("confirm") == "yes":
            count, freed = delete_shared_files(qs)
            log_activity(
                request,
                ActivityLog.Action.CLEANUP,
                details=f"Deleted {count} file(s) older than {days} days, freed {filesizeformat(freed)}",
            )
            messages.success(request, f"Deleted {count} file(s) older than {days} days ({filesizeformat(freed)} freed).")
            return redirect("panel:cleanup")
        totals = qs.aggregate(count=Count("id"), size=Sum("size"))
        preview = {
            "days": days,
            "count": totals["count"] or 0,
            "size": totals["size"] or 0,
            "sample": qs.select_related("uploaded_by")[:10],
        }
    return render(request, "panel/cleanup.html", {"form": form, "preview": preview})
