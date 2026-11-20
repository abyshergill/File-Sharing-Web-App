import os
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_share_code():
    """Unguessable code used in share links (~128 bits of randomness)."""
    return secrets.token_urlsafe(16)


def upload_to(instance, filename):
    # Store on disk under a random name; the original name is kept in the DB.
    # This avoids path traversal, name clashes and leaking names on disk.
    ext = os.path.splitext(filename)[1].lower()[:16]
    return f"{instance.created_at:%Y/%m}/{uuid.uuid4().hex}{ext}"


class SiteSettings(models.Model):
    """Single-row table holding admin-controlled access rules."""

    public_upload = models.BooleanField(
        default=False,
        help_text="If on, anyone (no login) can upload files. If off, only signed-in users can.",
    )
    public_download = models.BooleanField(
        default=False,
        help_text="If on, anyone with a share code can download. If off, only signed-in users can.",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SharedFile(models.Model):
    share_code = models.CharField(
        max_length=32, unique=True, default=generate_share_code, editable=False
    )
    file = models.FileField(upload_to=upload_to, max_length=255)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=127, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="shared_files",
    )
    uploader_ip = models.GenericIPAddressField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    last_downloaded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_name} ({self.share_code})"

    @property
    def uploader_display(self):
        return self.uploaded_by.username if self.uploaded_by else "N/A"

    def delete_file_from_disk(self):
        if self.file:
            self.file.delete(save=False)


class ActivityLog(models.Model):
    """Audit trail. Rows keep snapshots so they survive file/user deletion."""

    class Action(models.TextChoices):
        UPLOAD = "upload", "Upload"
        DOWNLOAD = "download", "Download"
        FAILED_LOOKUP = "failed_lookup", "Invalid code"
        DELETE = "delete", "Delete"
        CLEANUP = "cleanup", "Cleanup"
        SETTINGS = "settings", "Settings change"
        USER_ADMIN = "user_admin", "User management"

    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    shared_file = models.ForeignKey(
        SharedFile, null=True, blank=True, on_delete=models.SET_NULL, related_name="logs"
    )
    file_name = models.CharField(max_length=255, blank=True)
    share_code = models.CharField(max_length=64, blank=True)
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity",
    )
    # Username at the time of the event; "N/A" for anonymous visitors.
    username = models.CharField(max_length=150, default="N/A")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    details = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_action_display()} {self.file_name} by {self.username} from {self.ip_address}"
