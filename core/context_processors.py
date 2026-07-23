"""
Template context processors to inject global data into all templates.
"""


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

    return context
