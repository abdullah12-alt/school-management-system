"""
Middleware to set the current school in thread-local storage per request.
This powers the automatic tenant scoping in TenantManager.
Supports Platform Superadmin impersonation and inactive school access restriction.
"""
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout

from .managers import set_current_school, clear_current_school
from .models import School


class CurrentSchoolMiddleware:
    """
    Sets the current school from the authenticated user into thread-local
    storage on every request. TenantManager reads this value to automatically
    scope all queries to the user's school.

    Supports:
    - Superadmin impersonation mode (`request.session['impersonated_school_id']`)
    - Inactive school session enforcement for non-superadmin users
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user

            if user.is_superuser:
                # Check if superadmin is impersonating a school
                impersonated_id = request.session.get('impersonated_school_id')
                if impersonated_id:
                    try:
                        imp_school = School.objects.get(pk=impersonated_id)
                        set_current_school(imp_school)
                        request.impersonated_school = imp_school
                    except School.DoesNotExist:
                        request.session.pop('impersonated_school_id', None)
                        clear_current_school()
                else:
                    clear_current_school()
            else:
                # Standard school user
                if hasattr(user, 'school') and user.school:
                    if not user.school.is_active:
                        # Deactivated school: clear school and logout user
                        clear_current_school()
                        logout(request)
                        messages.error(
                            request,
                            'Your school account has been suspended. Please contact platform support.'
                        )
                        return redirect('core:login')
                    set_current_school(user.school)
                else:
                    clear_current_school()
        else:
            clear_current_school()

        response = self.get_response(request)

        # Always clear after response to prevent thread-local leaking
        clear_current_school()

        return response
