"""
Middleware to set the current school in thread-local storage per request.
This powers the automatic tenant scoping in TenantManager.
"""
from .managers import set_current_school, clear_current_school


class CurrentSchoolMiddleware:
    """
    Sets the current school from the authenticated user into thread-local
    storage on every request. TenantManager reads this value to automatically
    scope all queries to the user's school.

    Must be placed AFTER AuthenticationMiddleware in MIDDLEWARE settings.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set current school if user is authenticated and has a school
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'school') and request.user.school:
                set_current_school(request.user.school)
            else:
                # Platform Super Admin — no school scoping
                clear_current_school()
        else:
            clear_current_school()

        response = self.get_response(request)

        # Always clear after the response to prevent leaking between requests
        clear_current_school()

        return response
