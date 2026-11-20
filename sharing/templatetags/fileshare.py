from django import template

register = template.Library()


@register.inclusion_tag("partials/pagination.html")
def pagination(page, query=""):
    return {"page": page, "query": query}
