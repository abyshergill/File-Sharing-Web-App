from django.conf import settings
from django.core.paginator import Paginator


def paginate(request, queryset, per_page=None):
    paginator = Paginator(queryset, per_page or settings.FILESHARE_PAGE_SIZE)
    page = paginator.get_page(request.GET.get("page"))
    # Keep active filters in pagination links.
    params = request.GET.copy()
    params.pop("page", None)
    return page, params.urlencode()
