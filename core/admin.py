"""
Django Admin configuration for Platform Super Admin and School Admins.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    School, Department, User, Role, UserRole,
    ClassRoom, Section, Subject, Student, Staff, Timetable,
    StudentAttendance, Exam, ExamResult, FeeStructure, Invoice,
    Syllabus, SyllabusUnit,
)


class ScopedAdminMixin:
    """
    Mixin for ModelAdmin to ensure Superusers see all records across schools,
    while School Admins only see records belonging to their assigned school.
    """
    def get_queryset(self, request):
        qs = self.model.unscoped.all()
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'school') and request.user.school:
            return qs.filter(school=request.user.school)
        return qs.none()

    def save_model(self, request, obj, form, change):
        if not change and hasattr(request.user, 'school') and request.user.school:
            obj.school = request.user.school
        super().save_model(request, obj, form, change)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'plan', 'currency', 'theme_color', 'is_active', 'created_at']
    list_filter = ['plan', 'currency', 'theme_color', 'is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'school', 'primary_role', 'is_active']
    list_filter = ['primary_role', 'school', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['email']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('School & Role', {'fields': ('school', 'primary_role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name',
                       'school', 'primary_role'),
        }),
    )

    def get_queryset(self, request):
        qs = User.objects.all()
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'school') and request.user.school:
            return qs.filter(school=request.user.school)
        return qs.none()


@admin.register(Department)
class DepartmentAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'school']
    list_filter = ['school']
    search_fields = ['name']


@admin.register(Role)
class RoleAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'school', 'description']
    list_filter = ['school']
    search_fields = ['name']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'assigned_at']
    list_filter = ['role__school']
    search_fields = ['user__email', 'role__name']

    def get_queryset(self, request):
        qs = UserRole.objects.all()
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'school') and request.user.school:
            return qs.filter(role__school=request.user.school)
        return qs.none()


@admin.register(ClassRoom)
class ClassRoomAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'code', 'school']
    list_filter = ['school']
    search_fields = ['name', 'code']


@admin.register(Section)
class SectionAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'classroom', 'class_teacher', 'school']
    list_filter = ['school', 'classroom']
    search_fields = ['name', 'classroom__name']


@admin.register(Subject)
class SubjectAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'code', 'school']
    list_filter = ['school']
    search_fields = ['name', 'code']


@admin.register(Student)
class StudentAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['admission_number', 'user', 'section', 'parent', 'school']
    list_filter = ['school', 'section']
    search_fields = ['admission_number', 'user__first_name', 'user__last_name', 'user__email']


@admin.register(Staff)
class StaffAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['user', 'designation', 'school']
    list_filter = ['school']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'designation']


@admin.register(Timetable)
class TimetableAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['section', 'subject', 'teacher', 'day_of_week', 'start_time', 'end_time', 'school']
    list_filter = ['school', 'day_of_week', 'section']
    search_fields = ['section__name', 'subject__name', 'teacher__email']


@admin.register(StudentAttendance)
class StudentAttendanceAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['student', 'section', 'date', 'status', 'marked_by', 'school']
    list_filter = ['school', 'status', 'date', 'section']
    search_fields = ['student__user__first_name', 'student__user__last_name', 'student__admission_number']


@admin.register(Exam)
class ExamAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'section', 'date', 'max_marks', 'school']
    list_filter = ['school', 'section', 'date']
    search_fields = ['name', 'section__name']


@admin.register(ExamResult)
class ExamResultAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['exam', 'student', 'subject', 'marks_obtained', 'school']
    list_filter = ['school', 'exam', 'subject']
    search_fields = ['student__user__first_name', 'student__user__last_name', 'exam__name']


@admin.register(FeeStructure)
class FeeStructureAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'amount', 'school']
    list_filter = ['school']
    search_fields = ['name']


@admin.register(Invoice)
class InvoiceAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['id', 'student', 'fee_structure', 'amount_due', 'amount_paid', 'due_date', 'status', 'school']
    list_filter = ['school', 'status', 'due_date']
    search_fields = ['student__user__first_name', 'student__user__last_name', 'student__admission_number']


class SyllabusUnitInline(admin.TabularInline):
    model = SyllabusUnit
    extra = 1


@admin.register(Syllabus)
class SyllabusAdmin(ScopedAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'classroom', 'subject', 'academic_year', 'school']
    list_filter = ['school', 'classroom', 'subject', 'academic_year']
    search_fields = ['title', 'subject__name', 'classroom__name']
    inlines = [SyllabusUnitInline]


@admin.register(SyllabusUnit)
class SyllabusUnitAdmin(admin.ModelAdmin):
    list_display = ['title', 'syllabus', 'order']
    list_filter = ['syllabus__school', 'syllabus']
    search_fields = ['title', 'syllabus__title']
