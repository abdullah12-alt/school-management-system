"""
Custom template tags and filters.
"""
from django import template
from django.urls import resolve

register = template.Library()


@register.simple_tag(takes_context=True)
def active_link(context, url_name):
    """
    Returns 'active' if the current URL matches the given URL name.
    Usage: {% active_link 'core:staff_list' %}
    """
    request = context.get('request')
    if request:
        try:
            current = resolve(request.path_info)
            if current.url_name == url_name.split(':')[-1]:
                return 'active'
        except Exception:
            pass
    return ''


@register.filter
def get_item(dictionary, key):
    """
    Get value from dictionary using key in templates.
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
