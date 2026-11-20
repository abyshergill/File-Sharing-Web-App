from .models import SiteSettings
from .services import can_download, can_upload


def site_settings(request):
    site = SiteSettings.load()
    user = getattr(request, "user", None)
    return {
        "site_settings": site,
        "user_can_upload": bool(user) and can_upload(user, site),
        "user_can_download": bool(user) and can_download(user, site),
    }
