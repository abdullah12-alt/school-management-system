"""
Template context processors to inject global data into all templates.
"""
import json

from django.db.models import Q

from .models import CURRENCY_SYMBOLS, THEME_PALETTES, ThemeColorChoices, CurrencyChoices


def global_context(request):
    """
    Inject the current user, school, role information, and impersonation state into every template.
    """
    context = {
        'current_school': None,
        'user_role_display': '',
        'is_school_admin': False,
        'is_platform_admin': False,
        'impersonated_school': None,
        'school_currency_symbol': CURRENCY_SYMBOLS[CurrencyChoices.USD],
        'school_theme_palette_json': json.dumps(THEME_PALETTES[ThemeColorChoices.INDIGO]),
        'unread_announcement_count': 0,
    }

    if hasattr(request, 'user') and request.user.is_authenticated:
        user = request.user
        context['user_role_display'] = user.role_display
        context['is_school_admin'] = user.is_school_admin
        context['is_platform_admin'] = user.is_superuser

        if user.is_superuser and hasattr(request, 'impersonated_school'):
            context['impersonated_school'] = request.impersonated_school
            context['current_school'] = request.impersonated_school
        else:
            context['current_school'] = user.school

        school = context['current_school']
        if school:
            context['school_currency_symbol'] = school.currency_symbol
            context['school_theme_palette_json'] = json.dumps(school.theme_palette)

        # Unread announcement count
        if school or user.is_superuser:
            try:
                from .views import _get_announcements_for_user
                from .models import AnnouncementReadReceipt
                visible = _get_announcements_for_user(user)
                read_ids = AnnouncementReadReceipt.objects.filter(
                    user=user,
                    announcement__in=visible,
                ).values_list('announcement_id', flat=True)
                context['unread_announcement_count'] = visible.exclude(id__in=read_ids).count()
            except Exception:
                context['unread_announcement_count'] = 0

    return context
