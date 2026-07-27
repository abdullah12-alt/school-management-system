"""
Access control decorators and permission helpers for role-based views.
"""
from functools import wraps

from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, Http404


def school_admin_required(view_func):
    """
    Decorator that ensures the user is authenticated AND has the
    'school_admin' primary_role. Redirects to login otherwise.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        if not request.user.is_school_admin and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def role_required(*roles):
    """
    Decorator that ensures the user has one of the given primary_roles.
    Also allows platform superusers through.

    Usage:
        @role_required('teacher', 'staff')
        def my_view(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('core:login')
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if request.user.primary_role not in roles:
                return HttpResponseForbidden("Permission denied: You do not have access to this resource.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def teacher_required(view_func):
    """
    Ensures user is a Teacher or School Admin or Superuser.
    Strictly blocks Accountants, Students, Parents, etc.
    """
    return role_required('teacher', 'school_admin')(view_func)


def accountant_required(view_func):
    """
    Ensures user is an Accountant or School Admin or Superuser.
    Strictly blocks Teachers, Students, Parents, etc.
    """
    return role_required('accountant', 'school_admin')(view_func)


def student_or_parent_required(view_func):
    """
    Ensures user is a Student, Parent, Teacher, School Admin, or Superuser.
    Teachers may view attendance/results for students in their sections
    (enforced further by can_access_student_data).
    """
    return role_required('student', 'parent', 'teacher', 'school_admin')(view_func)


def get_teacher_sections(user):
    """
    Sections a teacher can access: class teacher OR timetable assignment.
    School admins / superusers get all sections in scope.
    """
    from django.db.models import Q
    from .models import Section

    qs = Section.objects.select_related('classroom', 'class_teacher')
    if user.is_superuser or getattr(user, 'is_school_admin', False):
        return qs.all()
    return qs.filter(
        Q(class_teacher=user) | Q(timetables__teacher=user)
    ).distinct()


def teacher_can_access_section(user, section):
    """Whether the user may manage/view a given section."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or getattr(user, 'is_school_admin', False):
        return True
    if user.primary_role != 'teacher':
        return False
    if section.class_teacher_id == user.id:
        return True
    return section.timetables.filter(teacher=user).exists()


def can_access_student_data(user, student):
    """
    Check if a user can access a specific student's record.
    - Superusers and School Admins (in same school) can access.
    - Teachers teaching the student's section can access.
    - The Student themselves can access.
    - The Student's Parent can access.
    - Anyone else (other students, other parents, unrelated users) CANNOT.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if user.school != student.school:
        return False
    if user.is_school_admin:
        return True
    if user.primary_role == 'student' and student.user == user:
        return True
    if user.primary_role == 'parent' and student.parent == user:
        return True
    if user.primary_role == 'teacher':
        # Check if teacher manages student's section or teaches a timetable subject in student's section
        if student.section and (
            student.section.class_teacher == user or
            student.section.timetables.filter(teacher=user).exists()
        ):
            return True
    if user.primary_role == 'accountant':
        # Accountant can access student invoices/billing info
        return True
    return False
