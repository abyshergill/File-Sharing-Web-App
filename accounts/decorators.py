from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """Allow only signed-in, active Admin users."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_app_admin:
            raise PermissionDenied("Admins only.")
        return view_func(request, *args, **kwargs)

    return wrapper
