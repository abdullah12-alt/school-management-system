"""
Tenant-aware managers for automatic school-level data isolation.

TenantManager reads the current school from thread-local storage (set by
CurrentSchoolMiddleware) and automatically filters querysets. This ensures
that every school-owned model query is scoped to the logged-in user's school
without requiring developers to remember to filter manually.
"""
import threading

from django.db import models

# Thread-local storage for the current school
_thread_locals = threading.local()


def set_current_school(school):
    """Set the current school in thread-local storage."""
    _thread_locals.current_school = school


def get_current_school():
    """Get the current school from thread-local storage."""
    return getattr(_thread_locals, 'current_school', None)


def clear_current_school():
    """Clear the current school from thread-local storage."""
    _thread_locals.current_school = None


class TenantQuerySet(models.QuerySet):
    """QuerySet that can switch between scoped and unscoped modes."""
    pass


class TenantManager(models.Manager):
    """
    Manager that automatically filters querysets by the current school.

    Usage:
        class MyModel(TenantModel):
            ...
            # TenantManager is inherited from TenantModel

        # In a view (with middleware active):
        MyModel.objects.all()  # Automatically filtered by current school

        # For cross-tenant queries (Platform Super Admin only):
        MyModel.unscoped.all()  # Returns ALL records across all schools
    """

    def get_queryset(self):
        qs = TenantQuerySet(self.model, using=self._db)
        current_school = get_current_school()
        if current_school is not None:
            qs = qs.filter(school=current_school)
        return qs


class UnscopedManager(models.Manager):
    """
    Manager that bypasses tenant scoping entirely.
    Use ONLY for Platform Super Admin operations or management commands.
    """

    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)
