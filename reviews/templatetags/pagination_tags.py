from django import template

register = template.Library()

@register.simple_tag
def page_range(paginator, current_page, delta=2):
    start = max(current_page - delta, 1)
    end = min(current_page + delta, paginator.num_pages)
    return range(start, end + 1)
