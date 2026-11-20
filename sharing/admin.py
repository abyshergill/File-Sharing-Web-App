from django.contrib import admin

from .models import ActivityLog, SharedFile, SiteSettings


@admin.register(SharedFile)
class SharedFileAdmin(admin.ModelAdmin):
    list_display = ("original_name", "share_code", "size", "uploaded_by", "uploader_ip", "download_count", "created_at")
    search_fields = ("original_name", "share_code", "uploader_ip")
    list_filter = ("created_at",)


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "file_name", "username", "ip_address")
    list_filter = ("action",)
    search_fields = ("file_name", "share_code", "username", "ip_address")

    def has_change_permission(self, request, obj=None):
        return False  # Audit log is read-only.

    def has_add_permission(self, request):
        return False


admin.site.register(SiteSettings)
