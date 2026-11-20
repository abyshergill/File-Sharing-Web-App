"""User management for admins (create admins / general users, edit, reset password, delete)."""

from django.contrib import messages
from django.contrib.auth.forms import SetPasswordForm
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from sharing.models import ActivityLog
from sharing.pagination import paginate
from sharing.services import log_activity

from .decorators import admin_required
from .forms import AdminUserCreateForm, AdminUserEditForm, is_last_active_admin
from .models import User


@admin_required
def user_list(request):
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    qs = User.objects.annotate(file_count=Count("shared_files")).order_by("username")
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
    if role in User.Role.values:
        qs = qs.filter(role=role)
    page, query = paginate(request, qs)
    return render(request, "accounts/user_list.html", {
        "page": page, "query": query, "q": q, "role": role, "roles": User.Role.choices,
    })


@admin_required
def user_create(request):
    form = AdminUserCreateForm(request.POST or None, initial={"role": request.GET.get("role", User.Role.GENERAL)})
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.created_by = request.user
        user.save()
        log_activity(request, ActivityLog.Action.USER_ADMIN,
                     details=f"Created {user.get_role_display()} '{user.username}'")
        messages.success(request, f"Created {user.get_role_display().lower()} “{user.username}”.")
        return redirect("accounts:user_list")
    return render(request, "accounts/user_form.html", {"form": form, "title": "Create user"})


@admin_required
def user_edit(request, pk):
    target = get_object_or_404(User, pk=pk)
    form = AdminUserEditForm(request.POST or None, instance=target, acting_user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_activity(request, ActivityLog.Action.USER_ADMIN,
                     details=f"Updated '{target.username}': role={target.role}, active={target.is_active}")
        messages.success(request, f"Saved “{target.username}”.")
        return redirect("accounts:user_list")
    return render(request, "accounts/user_form.html", {"form": form, "title": f"Edit {target.username}", "target": target})


@admin_required
def user_set_password(request, pk):
    target = get_object_or_404(User, pk=pk)
    form = SetPasswordForm(target, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        log_activity(request, ActivityLog.Action.USER_ADMIN, details=f"Reset password for '{target.username}'")
        messages.success(request, f"Password changed for “{target.username}”.")
        return redirect("accounts:user_list")
    return render(request, "accounts/user_form.html", {"form": form, "title": f"Set password for {target.username}", "target": target})


@require_POST
@admin_required
def user_delete(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account.")
    elif target.role == User.Role.ADMIN and is_last_active_admin(target):
        messages.error(request, "You cannot delete the last active admin.")
    else:
        username = target.username
        target.delete()  # Their files stay; uploader becomes N/A, logs keep the username.
        log_activity(request, ActivityLog.Action.USER_ADMIN, details=f"Deleted user '{username}'")
        messages.success(request, f"Deleted “{username}”. Their files were kept.")
    return redirect("accounts:user_list")
