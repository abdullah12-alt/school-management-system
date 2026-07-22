"""
Template context processors to inject global data into all templates.
"""


def global_context(request):
    """
    Inject the current user, school, and role information into every template.
    """
    context = {
        'current_school': None,
        'user_role_display': '',
        'is_school_admin': False,
        'is_platform_admin': False,
    }

    if hasattr(request, 'user') and request.user.is_authenticated:
        user = request.user
        context['current_school'] = user.school
        context['user_role_display'] = user.role_display
        context['is_school_admin'] = user.is_school_admin
        context['is_platform_admin'] = user.is_superuser

    return context
