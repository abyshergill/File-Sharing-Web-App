"""Shared helpers: client IP, audit logging, access rules and code-guess throttling."""

import ipaddress
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .models import ActivityLog, SharedFile, SiteSettings


# --- Client info ---------------------------------------------------------------

def _valid_ip(value):
    try:
        return str(ipaddress.ip_address(value.strip()))
    except (ValueError, AttributeError):
        return None


def get_client_ip(request):
    if settings.FILESHARE_TRUST_X_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            # The left-most entry is the original client.
            ip = _valid_ip(forwarded.split(",")[0])
            if ip:
                return ip
    return _valid_ip(request.META.get("REMOTE_ADDR", ""))


def get_user_agent(request):
    return request.META.get("HTTP_USER_AGENT", "")[:512]


# --- Audit log -----------------------------------------------------------------

def log_activity(request, action, shared_file=None, details="", **snapshot):
    user = request.user if request.user.is_authenticated else None
    return ActivityLog.objects.create(
        action=action,
        shared_file=shared_file,
        file_name=snapshot.get("file_name", shared_file.original_name if shared_file else ""),
        share_code=snapshot.get("share_code", shared_file.share_code if shared_file else "")[:64],
        file_size=snapshot.get("file_size", shared_file.size if shared_file else None),
        user=user,
        username=user.username if user else "N/A",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details=details[:500],
    )


# --- Access rules --------------------------------------------------------------

def can_upload(user, site=None):
    site = site or SiteSettings.load()
    return site.public_upload or user.is_authenticated


def can_download(user, site=None):
    site = site or SiteSettings.load()
    return site.public_download or user.is_authenticated


def can_manage_file(user, shared_file):
    if not user.is_authenticated:
        return False
    return user.is_app_admin or shared_file.uploaded_by_id == user.id


# --- Brute-force protection for share codes -------------------------------------

def _throttle_key(ip):
    return f"fileshare:failed:{ip or 'unknown'}"


def lockout_remaining(request):
    """Seconds this client must still wait before trying another code (0 = allowed)."""
    data = cache.get(_throttle_key(get_client_ip(request)))
    if not data or not data.get("locked_until"):
        return 0
    remaining = (data["locked_until"] - timezone.now()).total_seconds()
    return max(0, int(remaining) + (1 if remaining % 1 else 0))


def register_failed_lookup(request):
    """Record a wrong code. Returns (attempts_left, lockout_seconds)."""
    key = _throttle_key(get_client_ip(request))
    data = cache.get(key) or {"failures": 0, "locked_until": None}
    data["failures"] += 1
    limit = settings.FILESHARE_MAX_FAILED_ATTEMPTS
    lockout = 0
    if data["failures"] >= limit:
        # Each failure past the limit doubles the wait (capped at 24h).
        over = data["failures"] - limit
        lockout = min(settings.FILESHARE_LOCKOUT_BASE_SECONDS * (2 ** over), 24 * 3600)
        data["locked_until"] = timezone.now() + timedelta(seconds=lockout)
    cache.set(key, data, timeout=24 * 3600)
    return max(0, limit - data["failures"]), lockout


def reset_failed_lookups(request):
    cache.delete(_throttle_key(get_client_ip(request)))


# --- Cleanup -----------------------------------------------------------------------

def old_files_queryset(days):
    cutoff = timezone.now() - timedelta(days=days)
    return SharedFile.objects.filter(created_at__lt=cutoff)


def delete_shared_files(queryset):
    """Delete records and their files on disk. Returns (count, bytes_freed)."""
    count = 0
    freed = 0
    for shared_file in queryset.iterator():
        size = shared_file.size
        with transaction.atomic():
            shared_file.delete()
        # Remove from disk only after the row is gone, so a failed DB delete
        # never leaves a record pointing at a missing file.
        shared_file.delete_file_from_disk()
        count += 1
        freed += size
    return count, freed
