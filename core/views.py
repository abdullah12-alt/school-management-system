"""
Views for authentication, dashboards, account management, academics, attendance, exams, and finance.
"""
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404, HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Sum, Q

from .forms import (
    LoginForm, StaffCreateForm, RoleAssignmentForm, RoleCreateForm,
    ExamCreateForm, InvoiceCreateForm, SchoolCreateForm, SchoolEditForm,
    SubscriptionPlanForm, ClassRoomForm, SectionForm, SubjectForm,
    SyllabusForm, SyllabusUnitForm, StudentCreateForm, StudentEditForm,
    SchoolPreferencesForm, ProfileUpdateForm, ChangePasswordForm, TimetableForm,
)
from .decorators import (
    school_admin_required, teacher_required, accountant_required,
    student_or_parent_required, can_access_student_data,
    get_teacher_sections, teacher_can_access_section,
    get_teacher_syllabus_options, teacher_can_manage_syllabus,
)
from .managers import get_current_school
from .models import (
    School, User, Role, UserRole, PrimaryRoleChoices, STAFF_ROLES,
    Section, Subject, Student, Staff, ClassRoom, Timetable,
    StudentAttendance, Exam, ExamResult, FeeStructure, Invoice,
    AttendanceStatusChoices, InvoiceStatusChoices, PlatformActivity,
    ActivityTypeChoices, PlanChoices, SubscriptionPlan,
    Syllabus, SyllabusUnit, DayOfWeekChoices,
)

def get_request_school(request):
    """
    Resolve the active school for school-scoped operations.
    Prefers impersonated school (platform admin), then user.school,
    then thread-local current school.
    """
    if getattr(request, 'impersonated_school', None):
        return request.impersonated_school
    if getattr(request.user, 'school', None):
        return request.user.school
    return get_current_school()


# ── Auth Views ───────────────────────────────────────────────────────────────

def login_view(request):
    """Handle user login with email and password."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.cleaned_data['user']
        login(request, user)
        messages.success(request, f'Welcome back, {user.get_full_name()}!')
        return redirect('core:dashboard')

    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    """Log out and redirect to login page."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('core:login')


# ── Dashboard Views ──────────────────────────────────────────────────────────

@login_required
def dashboard_redirect(request):
    """Redirect to the appropriate dashboard based on user role."""
    user = request.user

    if user.is_superuser:
        return redirect('core:dashboard_superadmin')

    role_dashboard_map = {
        'school_admin': 'core:dashboard_school_admin',
        'teacher': 'core:dashboard_teacher',
        'staff': 'core:dashboard_staff',
        'accountant': 'core:dashboard_accountant',
        'librarian': 'core:dashboard_librarian',
        'student': 'core:dashboard_student',
        'parent': 'core:dashboard_parent',
    }

    dashboard_name = role_dashboard_map.get(user.primary_role)
    if dashboard_name:
        return redirect(dashboard_name)

    return redirect('core:dashboard_staff')


@login_required
def dashboard_superadmin(request):
    """Platform Super Admin dashboard with health stats, search/filter, and activity feed."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    schools_qs = School.objects.all()
    total_schools = schools_qs.count()
    active_schools = schools_qs.filter(is_active=True).count()
    inactive_schools = schools_qs.filter(is_active=False).count()

    total_users = User.objects.count()

    # User role breakdown
    role_counts = {
        'school_admin': User.objects.filter(primary_role=PrimaryRoleChoices.SCHOOL_ADMIN).count(),
        'teacher': User.objects.filter(primary_role=PrimaryRoleChoices.TEACHER).count(),
        'student': User.objects.filter(primary_role=PrimaryRoleChoices.STUDENT).count(),
        'parent': User.objects.filter(primary_role=PrimaryRoleChoices.PARENT).count(),
        'accountant': User.objects.filter(primary_role=PrimaryRoleChoices.ACCOUNTANT).count(),
        'staff': User.objects.filter(primary_role__in=['staff', 'librarian']).count(),
    }

    # Search & Filter
    search_q = request.GET.get('q', '').strip()
    plan_filter = request.GET.get('plan', '')
    status_filter = request.GET.get('status', '')

    filtered_schools = schools_qs
    if search_q:
        filtered_schools = filtered_schools.filter(
            Q(name__icontains=search_q) | Q(slug__icontains=search_q)
        )
    if plan_filter in ['free', 'basic', 'premium']:
        filtered_schools = filtered_schools.filter(plan=plan_filter)
    if status_filter == 'active':
        filtered_schools = filtered_schools.filter(is_active=True)
    elif status_filter == 'inactive':
        filtered_schools = filtered_schools.filter(is_active=False)

    recent_activities = PlatformActivity.objects.select_related('school', 'actor')[:15]
    all_subscription_plans = SubscriptionPlan.objects.all()

    return render(request, 'core/dashboard_superadmin.html', {
        'total_schools': total_schools,
        'active_schools': active_schools,
        'inactive_schools': inactive_schools,
        'total_users': total_users,
        'role_counts': role_counts,
        'schools': filtered_schools,
        'recent_activities': recent_activities,
        'search_q': search_q,
        'plan_filter': plan_filter,
        'status_filter': status_filter,
        'plan_choices': PlanChoices.choices,
        'subscription_plans': all_subscription_plans,
    })


@login_required
def platform_school_create(request):
    """Platform Superadmin creates a new school and provisions its initial admin account."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    form = SchoolCreateForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        school = form.save()

        # Provision initial School Admin user
        admin_user = User.objects.create_user(
            email=form.cleaned_data['admin_email'],
            password=form.cleaned_data['admin_password'],
            first_name=form.cleaned_data['admin_first_name'],
            last_name=form.cleaned_data['admin_last_name'],
            school=school,
            primary_role=PrimaryRoleChoices.SCHOOL_ADMIN,
        )

        PlatformActivity.objects.create(
            school=school,
            actor=request.user,
            action_type=ActivityTypeChoices.SCHOOL_CREATED,
            description=f"Created school '{school.name}' ({school.get_plan_display()} Plan) and assigned admin {admin_user.email}."
        )

        messages.success(
            request,
            f"School '{school.name}' created successfully with Admin user {admin_user.email}."
        )
        return redirect('core:dashboard_superadmin')

    return render(request, 'core/platform_school_form.html', {
        'form': form,
        'title': 'Create New School',
        'is_edit': False,
    })


@login_required
def platform_school_edit(request, school_id):
    """Platform Superadmin edits a school's details."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    school = get_object_or_404(School, pk=school_id)
    form = SchoolEditForm(request.POST or None, instance=school)

    if request.method == 'POST' and form.is_valid():
        form.save()
        PlatformActivity.objects.create(
            school=school,
            actor=request.user,
            action_type=ActivityTypeChoices.SCHOOL_STATUS_CHANGED,
            description=f"Updated details for school '{school.name}'."
        )
        messages.success(request, f"Updated school '{school.name}' successfully.")
        return redirect('core:dashboard_superadmin')

    return render(request, 'core/platform_school_form.html', {
        'form': form,
        'school': school,
        'title': f"Edit School — {school.name}",
        'is_edit': True,
    })


@login_required
def platform_school_toggle_status(request, school_id):
    """Platform Superadmin toggles active/inactive status (suspend) of a school."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    school = get_object_or_404(School, pk=school_id)
    school.is_active = not school.is_active
    school.save()

    status_str = "Activated" if school.is_active else "Suspended"
    PlatformActivity.objects.create(
        school=school,
        actor=request.user,
        action_type=ActivityTypeChoices.SCHOOL_STATUS_CHANGED,
        description=f"{status_str} school '{school.name}'."
    )

    messages.success(request, f"School '{school.name}' is now {status_str.lower()}.")
    return redirect('core:dashboard_superadmin')


@login_required
def platform_school_change_plan(request, school_id):
    """Platform Superadmin changes the subscription plan of a school (now uses SubscriptionPlan FK)."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    school = get_object_or_404(School, pk=school_id)

    # Accept either subscription_plan_id (new) or legacy plan slug for backward compat
    plan_id = request.POST.get('subscription_plan_id')
    old_plan_name = school.plan_display_name

    if plan_id:
        try:
            new_plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
            school.subscription_plan = new_plan
            school.save()
            PlatformActivity.objects.create(
                school=school,
                actor=request.user,
                action_type=ActivityTypeChoices.PLAN_CHANGED,
                description=f"Changed plan for '{school.name}' from {old_plan_name} to {new_plan.name}."
            )
            messages.success(request, f"Changed plan for '{school.name}' to {new_plan.name}.")
        except SubscriptionPlan.DoesNotExist:
            messages.error(request, 'Invalid plan selected.')
    else:
        # Fallback: legacy text plan field
        new_plan_text = request.POST.get('plan')
        if new_plan_text in [p.value for p in PlanChoices]:
            school.plan = new_plan_text
            school.save()
            messages.success(request, f"Changed plan for '{school.name}' to {school.get_plan_display()}.")

    return redirect('core:dashboard_superadmin')


# ── Subscription Plan Management (Superadmin) ────────────────────────────────

@login_required
def platform_plan_list(request):
    """List all subscription plans with usage stats."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    plans = SubscriptionPlan.objects.prefetch_related('schools').all()
    return render(request, 'core/platform_plan_list.html', {'plans': plans})


@login_required
def platform_plan_create(request):
    """Create a new subscription plan."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    form = SubscriptionPlanForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        plan = form.save()
        PlatformActivity.objects.create(
            actor=request.user,
            action_type=ActivityTypeChoices.PLAN_CHANGED,
            description=f"Created new subscription plan '{plan.name}' (Students: {plan.student_limit_display}, Staff: {plan.staff_limit_display}, Price: ${plan.price_month}/mo)."
        )
        messages.success(request, f"Plan '{plan.name}' created successfully.")
        return redirect('core:platform_plan_list')

    return render(request, 'core/platform_plan_form.html', {
        'form': form,
        'title': 'Create Subscription Plan',
        'is_edit': False,
    })


@login_required
def platform_plan_edit(request, plan_id):
    """Edit an existing subscription plan."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    plan = get_object_or_404(SubscriptionPlan, pk=plan_id)
    form = SubscriptionPlanForm(request.POST or None, instance=plan)

    if request.method == 'POST' and form.is_valid():
        updated = form.save()
        PlatformActivity.objects.create(
            actor=request.user,
            action_type=ActivityTypeChoices.PLAN_CHANGED,
            description=f"Updated subscription plan '{updated.name}' (Students: {updated.student_limit_display}, Staff: {updated.staff_limit_display}, Price: ${updated.price_month}/mo)."
        )
        messages.success(request, f"Plan '{updated.name}' updated.")
        return redirect('core:platform_plan_list')

    return render(request, 'core/platform_plan_form.html', {
        'form': form,
        'plan': plan,
        'title': f'Edit Plan — {plan.name}',
        'is_edit': True,
    })


@login_required
def platform_plan_delete(request, plan_id):
    """Delete a subscription plan — blocked if any school is currently assigned to it."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    plan = get_object_or_404(SubscriptionPlan, pk=plan_id)

    if request.method == 'POST':
        if plan.school_count > 0:
            messages.error(
                request,
                f"Cannot delete plan '{plan.name}' — {plan.school_count} school(s) are currently assigned to it. "
                "Reassign those schools to another plan first."
            )
        else:
            plan_name = plan.name
            plan.delete()
            PlatformActivity.objects.create(
                actor=request.user,
                action_type=ActivityTypeChoices.PLAN_CHANGED,
                description=f"Deleted subscription plan '{plan_name}'."
            )
            messages.success(request, f"Plan '{plan_name}' deleted.")

    return redirect('core:platform_plan_list')


@login_required
def platform_school_impersonate(request, school_id):
    """Platform Superadmin enters impersonation mode for a school."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    school = get_object_or_404(School, pk=school_id)
    request.session['impersonated_school_id'] = school.id
    messages.info(request, f"Entered impersonation mode for '{school.name}'.")
    return redirect('core:dashboard_school_admin')


@login_required
def platform_exit_impersonation(request):
    """Exits impersonation mode."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    request.session.pop('impersonated_school_id', None)
    messages.info(request, "Exited impersonation mode.")
    return redirect('core:dashboard_superadmin')


@login_required
def platform_user_list(request):
    """Global User List across all schools for Platform Superadmin."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    users_qs = User.objects.all().select_related('school')

    # Search and Filter
    search_q = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', '')
    school_filter = request.GET.get('school', '')
    status_filter = request.GET.get('status', '')

    if search_q:
        users_qs = users_qs.filter(
            Q(email__icontains=search_q) |
            Q(first_name__icontains=search_q) |
            Q(last_name__icontains=search_q)
        )
    if role_filter:
        users_qs = users_qs.filter(primary_role=role_filter)
    if school_filter:
        users_qs = users_qs.filter(school_id=school_filter)
    if status_filter == 'active':
        users_qs = users_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        users_qs = users_qs.filter(is_active=False)

    paginator = Paginator(users_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    schools = School.objects.all()

    return render(request, 'core/platform_user_list.html', {
        'users': page_obj,
        'page_obj': page_obj,
        'schools': schools,
        'search_q': search_q,
        'role_filter': role_filter,
        'school_filter': school_filter,
        'status_filter': status_filter,
        'role_choices': PrimaryRoleChoices.choices,
    })


@login_required
def platform_user_toggle_active(request, user_id):
    """Platform Superadmin activates or deactivates a user account."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    target_user = get_object_or_404(User, pk=user_id)
    if target_user.is_superuser:
        messages.error(request, "Cannot deactivate superadmin accounts.")
        return redirect('core:platform_user_list')

    target_user.is_active = not target_user.is_active
    target_user.save()

    status_str = "activated" if target_user.is_active else "deactivated"
    PlatformActivity.objects.create(
        school=target_user.school,
        actor=request.user,
        action_type=ActivityTypeChoices.USER_STATUS_CHANGED,
        description=f"{status_str.capitalize()} user account {target_user.email}."
    )
    messages.success(request, f"User {target_user.email} has been {status_str}.")
    return redirect('core:platform_user_list')


@login_required
def platform_user_reset_password(request, user_id):
    """Platform Superadmin resets password for a user."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    target_user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        if new_password and len(new_password) >= 8:
            target_user.set_password(new_password)
            target_user.save()
            messages.success(request, f"Password reset successfully for {target_user.email}.")
            return redirect('core:platform_user_list')
        else:
            messages.error(request, "Password must be at least 8 characters long.")

    return render(request, 'core/platform_user_reset_password.html', {
        'target_user': target_user,
    })


@login_required
def dashboard_school_admin(request):
    """School Admin dashboard with overview stats."""
    user = request.user
    if not user.is_school_admin and not user.is_superuser:
        return redirect('core:dashboard')

    staff_count = User.objects.filter(
        school=user.school,
        primary_role__in=[r.value for r in STAFF_ROLES],
    ).count()
    role_count = Role.objects.count()
    student_count = Student.objects.count()
    unpaid_invoice_count = Invoice.objects.filter(status__in=['unpaid', 'partial']).count()

    return render(request, 'core/dashboard_school_admin.html', {
        'staff_count': staff_count,
        'role_count': role_count,
        'student_count': student_count,
        'unpaid_invoice_count': unpaid_invoice_count,
    })


@login_required
def dashboard_teacher(request):
    """Teacher dashboard listing assigned sections and direct shortcuts."""
    user = request.user
    if user.primary_role != 'teacher' and not user.is_superuser:
        return redirect('core:dashboard')

    managed_sections = get_teacher_sections(user)
    today = datetime.date.today()
    today_key = today.strftime('%A').lower()  # monday, tuesday, ...
    today_slots = Timetable.objects.filter(
        teacher=user,
        day_of_week=today_key,
    ).select_related('section', 'section__classroom', 'subject').order_by('start_time')

    return render(request, 'core/dashboard_teacher.html', {
        'sections': managed_sections,
        'today_slots': today_slots,
        'today': today,
    })


@teacher_required
def attendance_mark(request):
    """Teachers mark daily attendance for a section they can access."""
    sections = get_teacher_sections(request.user)
    selected_section_id = request.GET.get('section_id') or (sections.first().id if sections.exists() else None)
    date_str = request.GET.get('date') or datetime.date.today().isoformat()

    try:
        selected_date = datetime.date.fromisoformat(date_str)
    except ValueError:
        selected_date = datetime.date.today()

    selected_section = None
    students = []
    attendance_map = {}

    if selected_section_id:
        selected_section = get_object_or_404(Section, pk=selected_section_id)
        if not teacher_can_access_section(request.user, selected_section):
            raise Http404("Section not found.")
        students = Student.objects.filter(section=selected_section, user__is_active=True).select_related('user')
        existing_attendances = StudentAttendance.objects.filter(
            section=selected_section,
            date=selected_date
        )
        for att in existing_attendances:
            attendance_map[att.student_id] = att.status

    if request.method == 'POST':
        if not selected_section:
            messages.error(request, 'Please select a section.')
            return redirect('core:attendance_mark')

        marked_count = 0
        school = get_request_school(request) or request.user.school
        for student in students:
            status_val = request.POST.get(f'status_{student.id}')
            if status_val in dict(AttendanceStatusChoices.choices):
                StudentAttendance.objects.update_or_create(
                    student=student,
                    date=selected_date,
                    defaults={
                        'section': selected_section,
                        'status': status_val,
                        'marked_by': request.user,
                        'school': school,
                    }
                )
                marked_count += 1

        messages.success(
            request,
            f'Attendance marked successfully for {marked_count} students on {selected_date}.'
        )
        return redirect(f"{request.path}?section_id={selected_section.id}&date={selected_date.isoformat()}")

    return render(request, 'core/attendance_mark.html', {
        'sections': sections,
        'selected_section': selected_section,
        'selected_date': selected_date,
        'students': students,
        'attendance_map': attendance_map,
        'status_choices': AttendanceStatusChoices.choices,
    })


@login_required
def dashboard_student(request):
    """Student dashboard showing recent attendance, exam results, and fee status."""
    user = request.user
    if user.primary_role != 'student' and not user.is_superuser:
        return redirect('core:dashboard')

    student = getattr(user, 'student_profile', None)
    if not student:
        messages.error(request, 'No student profile found for your account.')
        return render(request, 'core/dashboard_role.html', {'role_name': 'Student', 'role_icon': 'graduation-cap'})

    recent_attendance = StudentAttendance.objects.filter(student=student)[:10]
    recent_results = ExamResult.objects.filter(student=student).select_related('exam', 'subject')[:5]
    invoices = Invoice.objects.filter(student=student).select_related('fee_structure')

    total_due = invoices.aggregate(Sum('amount_due'))['amount_due__sum'] or Decimal('0.00')
    total_paid = invoices.aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')
    remaining_balance = total_due - total_paid

    return render(request, 'core/dashboard_student.html', {
        'student': student,
        'recent_attendance': recent_attendance,
        'recent_results': recent_results,
        'invoices': invoices,
        'total_due': total_due,
        'total_paid': total_paid,
        'remaining_balance': remaining_balance,
    })


@login_required
def dashboard_parent(request):
    """Parent dashboard showing linked children summaries."""
    user = request.user
    if user.primary_role != 'parent' and not user.is_superuser:
        return redirect('core:dashboard')

    children = user.children.all().select_related('section', 'section__classroom', 'user')

    children_data = []
    for child in children:
        recent_attendance = StudentAttendance.objects.filter(student=child)[:5]
        recent_results = ExamResult.objects.filter(student=child).select_related('exam', 'subject')[:5]
        invoices = Invoice.objects.filter(student=child)
        unpaid_invoices = invoices.filter(status__in=['unpaid', 'partial'])
        children_data.append({
            'child': child,
            'recent_attendance': recent_attendance,
            'recent_results': recent_results,
            'unpaid_count': unpaid_invoices.count(),
        })

    return render(request, 'core/dashboard_parent.html', {
        'children_data': children_data,
    })


# ── Student Portal Views (Timetable / Subjects / Study Materials) ───────
def _get_student_for_student_portal(request):
    """
    Resolve the Student instance for a student/parent user.
    Returns None when the request user does not map to a student.
    """
    user = request.user
    if user.primary_role == 'student':
        return getattr(user, 'student_profile', None)
    if user.primary_role == 'parent':
        return user.children.first()
    return None


@student_or_parent_required
def student_timetable(request):
    """Student/Parent: show weekly timetable for the student's section."""
    user = request.user
    if user.primary_role not in ['student', 'parent'] and not user.is_superuser:
        return redirect('core:dashboard')

    student = _get_student_for_student_portal(request)
    if not student or not student.section:
        messages.error(request, 'Student section not found.')
        return redirect('core:dashboard_student')

    slots = Timetable.objects.filter(section=student.section).select_related(
        'subject',
        'section',
        'section__classroom',
        'teacher',
    ).order_by('day_of_week', 'start_time')

    days = list(DayOfWeekChoices)
    timetable_by_day = {day.value: [] for day in days}
    for slot in slots:
        timetable_by_day[slot.day_of_week].append(slot)

    day_rows = [(day, timetable_by_day.get(day.value, [])) for day in days]

    return render(request, 'core/student_timetable.html', {
        'student': student,
        'day_rows': day_rows,
    })


@student_or_parent_required
def student_subjects(request):
    """Student/Parent: list subjects assigned via timetable for the section."""
    user = request.user
    if user.primary_role not in ['student', 'parent'] and not user.is_superuser:
        return redirect('core:dashboard')

    student = _get_student_for_student_portal(request)
    if not student or not student.section:
        messages.error(request, 'Student section not found.')
        return redirect('core:dashboard_student')

    subjects = Subject.objects.filter(timetables__section=student.section).distinct().order_by('name')
    return render(request, 'core/student_subjects.html', {
        'student': student,
        'subjects': subjects,
    })


@student_or_parent_required
def student_subject_detail(request, subject_id):
    """Student/Parent: show study material (Syllabus + units) for a subject."""
    user = request.user
    if user.primary_role not in ['student', 'parent'] and not user.is_superuser:
        return redirect('core:dashboard')

    student = _get_student_for_student_portal(request)
    if not student or not student.section:
        messages.error(request, 'Student section not found.')
        return redirect('core:dashboard_student')

    subject = get_object_or_404(Subject, pk=subject_id)

    # Ensure this subject is actually assigned to the student's section.
    if not Timetable.objects.filter(section=student.section, subject=subject).exists():
        raise Http404("Subject not assigned for this student.")

    syllabi = Syllabus.objects.filter(
        classroom=student.section.classroom,
        subject=subject,
    ).prefetch_related('units').order_by('-created_at')

    return render(request, 'core/student_subject_detail.html', {
        'student': student,
        'subject': subject,
        'syllabi': syllabi,
    })


@login_required
def dashboard_accountant(request):
    """Accountant dashboard listing outstanding invoices."""
    user = request.user
    if user.primary_role != 'accountant' and not user.is_superuser:
        return redirect('core:dashboard')

    outstanding_invoices = Invoice.objects.filter(
        status__in=['unpaid', 'partial']
    ).select_related('student__user', 'fee_structure')

    total_unpaid_sum = outstanding_invoices.aggregate(Sum('amount_due'))['amount_due__sum'] or Decimal('0.00')

    return render(request, 'core/dashboard_accountant.html', {
        'outstanding_invoices': outstanding_invoices,
        'total_unpaid_sum': total_unpaid_sum,
    })


@login_required
def dashboard_staff(request):
    return render(request, 'core/dashboard_role.html', {
        'role_name': 'Staff',
        'role_icon': 'briefcase',
    })


@login_required
def dashboard_librarian(request):
    return render(request, 'core/dashboard_role.html', {
        'role_name': 'Librarian',
        'role_icon': 'library',
    })


# ── Staff Management Views ──────────────────────────────────────────────────

@school_admin_required
def staff_list(request):
    """List all staff members in the current school with pagination."""
    staff_members = User.objects.filter(
        school=request.user.school,
        primary_role__in=[r.value for r in STAFF_ROLES],
    ).prefetch_related('user_roles__role')

    paginator = Paginator(staff_members, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/staff_list.html', {
        'staff_members': page_obj,
        'page_obj': page_obj,
    })


@school_admin_required
def staff_create(request):
    """Create a new staff member under the current school."""
    school = request.user.school
    if school and school.is_staff_limit_reached:
        messages.error(
            request,
            f'Staff limit reached for {school.name} ({school.staff_count}/{school.staff_limit} on {school.get_plan_display()} Plan). '
            'Please upgrade your plan to add more staff.'
        )
        return redirect('core:staff_list')

    form = StaffCreateForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save(school=school)
        messages.success(
            request,
            f'{user.get_full_name()} has been added as '
            f'{user.get_primary_role_display()}.'
        )
        return redirect('core:staff_list')

    return render(request, 'core/staff_create.html', {'form': form})


@school_admin_required
def staff_roles(request, user_id):
    """Assign extra roles to a staff member."""
    staff_member = get_object_or_404(
        User,
        pk=user_id,
        school=request.user.school,
        primary_role__in=[r.value for r in STAFF_ROLES],
    )

    school = request.user.school
    current_roles = Role.unscoped.filter(
        school=school,
        user_roles__user=staff_member,
    )

    if request.method == 'POST':
        form = RoleAssignmentForm(request.POST, school=school)
        if form.is_valid():
            selected_roles = form.cleaned_data['roles']
            UserRole.objects.filter(user=staff_member).exclude(
                role__in=selected_roles
            ).delete()
            for role in selected_roles:
                UserRole.objects.get_or_create(user=staff_member, role=role)

            messages.success(
                request,
                f'Roles updated for {staff_member.get_full_name()}.'
            )
            return redirect('core:staff_list')
    else:
        form = RoleAssignmentForm(
            school=school,
            initial={'roles': current_roles},
        )

    return render(request, 'core/staff_roles.html', {
        'form': form,
        'staff_member': staff_member,
    })


# ── Role Management Views ───────────────────────────────────────────────────

@school_admin_required
def role_list(request):
    """List all custom roles in the current school."""
    roles = Role.objects.all()
    return render(request, 'core/role_list.html', {'roles': roles})


@school_admin_required
def role_create(request):
    """Create a new custom role for the current school."""
    form = RoleCreateForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        role = form.save(commit=False)
        role.school = request.user.school
        role.save()
        messages.success(request, f'Role "{role.name}" has been created.')
        return redirect('core:role_list')

    return render(request, 'core/role_create.html', {'form': form})


# ── Attendance Views ─────────────────────────────────────────────────────────

@student_or_parent_required
def attendance_history(request, student_id=None):
    """View attendance records for a student or child with pagination."""
    user = request.user

    if student_id:
        target_student = get_object_or_404(Student, pk=student_id)
        if not can_access_student_data(user, target_student):
            raise Http404("Student record not found.")
        student = target_student
    else:
        if user.primary_role == 'student':
            student = getattr(user, 'student_profile', None)
        elif user.primary_role == 'parent':
            student = user.children.first()
        else:
            student = Student.objects.first()

        if not student:
            messages.error(request, 'No student record found.')
            return redirect('core:dashboard')

    attendances = StudentAttendance.objects.filter(student=student).select_related('section', 'marked_by')
    paginator = Paginator(attendances, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/attendance_history.html', {
        'student': student,
        'attendances': page_obj,
        'page_obj': page_obj,
    })


# ── Exam & Grading Views ─────────────────────────────────────────────────────

@login_required
def exam_list(request):
    """List exams for the school (teachers see exams in their sections)."""
    exams = Exam.objects.all().select_related('section', 'section__classroom')
    if request.user.primary_role == 'teacher' and not request.user.is_superuser:
        section_ids = get_teacher_sections(request.user).values_list('id', flat=True)
        exams = exams.filter(section_id__in=section_ids)
    return render(request, 'core/exam_list.html', {'exams': exams})


@teacher_required
def exam_create(request):
    """Create a new exam (teachers limited to their sections)."""
    school = get_request_school(request) or request.user.school
    form = ExamCreateForm(request.POST or None, school=school)
    if request.user.primary_role == 'teacher' and not request.user.is_superuser:
        form.fields['section'].queryset = get_teacher_sections(request.user)

    if request.method == 'POST' and form.is_valid():
        exam = form.save(commit=False)
        exam.school = school
        if not teacher_can_access_section(request.user, exam.section):
            messages.error(request, 'You cannot create an exam for that section.')
            return redirect('core:exam_list')
        exam.save()
        messages.success(request, f'Exam "{exam.name}" created successfully.')
        return redirect('core:exam_list')

    return render(request, 'core/exam_create.html', {'form': form})


@teacher_required
def exam_grade(request, exam_id):
    """Teachers enter/edit marks for an exam."""
    exam = get_object_or_404(Exam, pk=exam_id)
    students = Student.objects.filter(section=exam.section).select_related('user')
    subjects = Subject.objects.all()

    existing_results = ExamResult.objects.filter(exam=exam)
    results_map = {}
    for res in existing_results:
        results_map[(res.student_id, res.subject_id)] = res.marks_obtained

    if request.method == 'POST':
        updated_count = 0
        for student in students:
            for subject in subjects:
                val = request.POST.get(f'marks_{student.id}_{subject.id}')
                if val is not None and val != '':
                    try:
                        marks = float(val)
                        ExamResult.objects.update_or_create(
                            exam=exam,
                            student=student,
                            subject=subject,
                            defaults={
                                'marks_obtained': marks,
                                'school': request.user.school
                            }
                        )
                        updated_count += 1
                    except ValueError:
                        pass

        messages.success(request, f'Saved {updated_count} exam mark entries for {exam.name}.')
        return redirect('core:exam_list')

    return render(request, 'core/exam_grade.html', {
        'exam': exam,
        'students': students,
        'subjects': subjects,
        'results_map': results_map,
    })


@student_or_parent_required
def exam_results_view(request, student_id=None):
    """View exam report card for a student or child with pagination."""
    user = request.user

    if student_id:
        target_student = get_object_or_404(Student, pk=student_id)
        if not can_access_student_data(user, target_student):
            raise Http404("Student record not found.")
        student = target_student
    else:
        if user.primary_role == 'student':
            student = getattr(user, 'student_profile', None)
        elif user.primary_role == 'parent':
            student = user.children.first()
        else:
            student = Student.objects.first()

        if not student:
            messages.error(request, 'No student record found.')
            return redirect('core:dashboard')

    results = ExamResult.objects.filter(student=student).select_related('exam', 'subject', 'exam__section')
    paginator = Paginator(results, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/exam_results.html', {
        'student': student,
        'results': page_obj,
        'page_obj': page_obj,
    })


# ── Fee & Finance Views ──────────────────────────────────────────────────────

@accountant_required
def invoice_list(request):
    """Accountant view of all school invoices with pagination."""
    invoices = Invoice.objects.all().select_related('student__user', 'fee_structure')
    status_filter = request.GET.get('status')
    if status_filter in ['unpaid', 'partial', 'paid']:
        invoices = invoices.filter(status=status_filter)

    paginator = Paginator(invoices, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/invoice_list.html', {
        'invoices': page_obj,
        'page_obj': page_obj,
        'current_status': status_filter,
        'status_choices': InvoiceStatusChoices.choices,
    })


@accountant_required
def invoice_create(request):
    """Accountant creates an invoice for a student."""
    form = InvoiceCreateForm(request.POST or None, school=request.user.school)

    if request.method == 'POST' and form.is_valid():
        invoice = form.save(commit=False)
        invoice.school = request.user.school
        invoice.save()
        messages.success(request, f'Invoice created for {invoice.student.user.get_full_name()}.')
        return redirect('core:invoice_list')

    return render(request, 'core/invoice_create.html', {'form': form})


@student_or_parent_required
def my_invoices(request, student_id=None):
    """View invoices for logged in student or parent's child with pagination."""
    user = request.user

    if student_id:
        target_student = get_object_or_404(Student, pk=student_id)
        if not can_access_student_data(user, target_student):
            raise Http404("Invoice record not found.")
        student = target_student
    else:
        if user.primary_role == 'student':
            student = getattr(user, 'student_profile', None)
        elif user.primary_role == 'parent':
            student = user.children.first()
        else:
            student = Student.objects.first()

        if not student:
            messages.error(request, 'No student record found.')
            return redirect('core:dashboard')

    invoices = Invoice.objects.filter(student=student).select_related('fee_structure')
    paginator = Paginator(invoices, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/my_invoices.html', {
        'student': student,
        'invoices': page_obj,
        'page_obj': page_obj,
    })


# ── Academic Structure: Classes ──────────────────────────────────────────────

@school_admin_required
def classroom_list(request):
    """List all classes/grades in the current school."""
    classrooms = ClassRoom.objects.prefetch_related('sections').all()
    return render(request, 'core/classroom_list.html', {
        'classrooms': classrooms,
    })


@school_admin_required
def classroom_create(request):
    """Create a new class/grade."""
    form = ClassRoomForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        classroom = form.save(commit=False)
        classroom.school = get_request_school(request)
        classroom.save()
        messages.success(request, f'Class "{classroom.name}" has been created.')
        return redirect('core:classroom_list')
    return render(request, 'core/classroom_form.html', {
        'form': form,
        'is_edit': False,
    })


@school_admin_required
def classroom_edit(request, classroom_id):
    """Edit an existing class/grade."""
    classroom = get_object_or_404(ClassRoom, pk=classroom_id)
    form = ClassRoomForm(request.POST or None, instance=classroom)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Class "{classroom.name}" has been updated.')
        return redirect('core:classroom_list')
    return render(request, 'core/classroom_form.html', {
        'form': form,
        'classroom': classroom,
        'is_edit': True,
    })


@school_admin_required
def classroom_delete(request, classroom_id):
    """Delete a class if it has no sections."""
    classroom = get_object_or_404(ClassRoom, pk=classroom_id)
    if request.method == 'POST':
        if classroom.sections.exists():
            messages.error(
                request,
                f'Cannot delete "{classroom.name}" because it has sections. '
                'Remove sections first.'
            )
        else:
            name = classroom.name
            classroom.delete()
            messages.success(request, f'Class "{name}" has been deleted.')
        return redirect('core:classroom_list')
    return redirect('core:classroom_list')


# ── Academic Structure: Sections ─────────────────────────────────────────────

@school_admin_required
def section_list(request):
    """List sections, optionally filtered by classroom."""
    classroom_id = request.GET.get('classroom', '')
    sections = Section.objects.select_related('classroom', 'class_teacher').all()
    if classroom_id.isdigit():
        sections = sections.filter(classroom_id=classroom_id)
    classrooms = ClassRoom.objects.all()
    return render(request, 'core/section_list.html', {
        'sections': sections,
        'classrooms': classrooms,
        'classroom_filter': classroom_id,
    })


@school_admin_required
def section_create(request):
    """Create a new section."""
    school = get_request_school(request)
    initial = {}
    classroom_id = request.GET.get('classroom')
    if classroom_id and classroom_id.isdigit():
        initial['classroom'] = classroom_id
    form = SectionForm(request.POST or None, school=school, initial=initial)
    if request.method == 'POST' and form.is_valid():
        section = form.save(commit=False)
        section.school = school
        section.save()
        messages.success(request, f'Section "{section}" has been created.')
        return redirect('core:section_list')
    return render(request, 'core/section_form.html', {
        'form': form,
        'is_edit': False,
    })


@school_admin_required
def section_edit(request, section_id):
    """Edit an existing section."""
    school = get_request_school(request)
    section = get_object_or_404(Section, pk=section_id)
    form = SectionForm(request.POST or None, school=school, instance=section)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Section "{section}" has been updated.')
        return redirect('core:section_list')
    return render(request, 'core/section_form.html', {
        'form': form,
        'section': section,
        'is_edit': True,
    })


@school_admin_required
def section_delete(request, section_id):
    """Delete a section if it has no students."""
    section = get_object_or_404(Section, pk=section_id)
    if request.method == 'POST':
        if section.students.exists():
            messages.error(
                request,
                f'Cannot delete "{section}" because it has students. '
                'Reassign students first.'
            )
        else:
            name = str(section)
            section.delete()
            messages.success(request, f'Section "{name}" has been deleted.')
        return redirect('core:section_list')
    return redirect('core:section_list')


# ── Academic Structure: Subjects ─────────────────────────────────────────────

@school_admin_required
def subject_list(request):
    """List all subjects in the current school."""
    subjects = Subject.objects.all()
    return render(request, 'core/subject_list.html', {'subjects': subjects})


@school_admin_required
def subject_create(request):
    """Create a new subject."""
    form = SubjectForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        subject = form.save(commit=False)
        subject.school = get_request_school(request)
        subject.save()
        messages.success(request, f'Subject "{subject.name}" has been created.')
        return redirect('core:subject_list')
    return render(request, 'core/subject_form.html', {
        'form': form,
        'is_edit': False,
    })


@school_admin_required
def subject_edit(request, subject_id):
    """Edit an existing subject."""
    subject = get_object_or_404(Subject, pk=subject_id)
    form = SubjectForm(request.POST or None, instance=subject)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Subject "{subject.name}" has been updated.')
        return redirect('core:subject_list')
    return render(request, 'core/subject_form.html', {
        'form': form,
        'subject': subject,
        'is_edit': True,
    })


@school_admin_required
def subject_delete(request, subject_id):
    """Delete a subject if unused by timetables/syllabi."""
    subject = get_object_or_404(Subject, pk=subject_id)
    if request.method == 'POST':
        if subject.timetables.exists() or subject.syllabi.exists():
            messages.error(
                request,
                f'Cannot delete "{subject.name}" because it is used in '
                'timetables or syllabi.'
            )
        else:
            name = subject.name
            subject.delete()
            messages.success(request, f'Subject "{name}" has been deleted.')
        return redirect('core:subject_list')
    return redirect('core:subject_list')


# ── Timetable Management ─────────────────────────────────────────────────────

@school_admin_required
def timetable_list(request):
    """List timetable slots with optional section/day filters."""
    section_id = request.GET.get('section', '')
    day = request.GET.get('day', '')
    slots = Timetable.objects.select_related(
        'section', 'section__classroom', 'subject', 'teacher'
    ).all()
    if section_id.isdigit():
        slots = slots.filter(section_id=section_id)
    if day in dict(DayOfWeekChoices.choices):
        slots = slots.filter(day_of_week=day)

    return render(request, 'core/timetable_list.html', {
        'slots': slots,
        'sections': Section.objects.select_related('classroom').all(),
        'days': DayOfWeekChoices.choices,
        'section_filter': section_id,
        'day_filter': day,
    })


@school_admin_required
def timetable_create(request):
    """Create a new timetable slot."""
    school = get_request_school(request)
    initial = {}
    section_id = request.GET.get('section')
    if section_id and section_id.isdigit():
        initial['section'] = section_id
    form = TimetableForm(request.POST or None, school=school, initial=initial)
    if request.method == 'POST' and form.is_valid():
        slot = form.save(commit=False)
        slot.school = school
        slot.save()
        messages.success(request, f'Timetable slot created: {slot}.')
        return redirect('core:timetable_list')
    return render(request, 'core/timetable_form.html', {
        'form': form,
        'is_edit': False,
    })


@school_admin_required
def timetable_edit(request, slot_id):
    """Edit an existing timetable slot."""
    school = get_request_school(request)
    slot = get_object_or_404(Timetable, pk=slot_id)
    form = TimetableForm(request.POST or None, school=school, instance=slot)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Timetable slot updated: {slot}.')
        return redirect('core:timetable_list')
    return render(request, 'core/timetable_form.html', {
        'form': form,
        'slot': slot,
        'is_edit': True,
    })


@school_admin_required
def timetable_delete(request, slot_id):
    """Delete a timetable slot."""
    slot = get_object_or_404(Timetable, pk=slot_id)
    if request.method == 'POST':
        label = str(slot)
        slot.delete()
        messages.success(request, f'Timetable slot deleted: {label}.')
        return redirect('core:timetable_list')
    return redirect('core:timetable_list')


# ── Syllabus Management ──────────────────────────────────────────────────────

@school_admin_required
def syllabus_list(request):
    """List syllabi, optionally filtered by class or subject."""
    classroom_id = request.GET.get('classroom', '')
    subject_id = request.GET.get('subject', '')
    syllabi = Syllabus.objects.select_related('classroom', 'subject').prefetch_related('units')
    if classroom_id.isdigit():
        syllabi = syllabi.filter(classroom_id=classroom_id)
    if subject_id.isdigit():
        syllabi = syllabi.filter(subject_id=subject_id)
    return render(request, 'core/syllabus_list.html', {
        'syllabi': syllabi,
        'classrooms': ClassRoom.objects.all(),
        'subjects': Subject.objects.all(),
        'classroom_filter': classroom_id,
        'subject_filter': subject_id,
    })


@school_admin_required
def syllabus_create(request):
    """Create a new syllabus."""
    school = get_request_school(request)
    form = SyllabusForm(request.POST or None, school=school)
    if request.method == 'POST' and form.is_valid():
        syllabus = form.save(commit=False)
        if not syllabus.school_id:
            messages.error(
                request,
                'Could not determine school. Impersonate a school or ensure '
                'your account is linked to one, then try again.',
            )
            return redirect('core:syllabus_list')
        syllabus.save()
        messages.success(request, f'Syllabus "{syllabus.title}" has been created.')
        return redirect('core:syllabus_detail', syllabus_id=syllabus.pk)
    return render(request, 'core/syllabus_form.html', {
        'form': form,
        'is_edit': False,
    })


@school_admin_required
def syllabus_edit(request, syllabus_id):
    """Edit an existing syllabus."""
    school = get_request_school(request)
    syllabus = get_object_or_404(Syllabus, pk=syllabus_id)
    form = SyllabusForm(request.POST or None, school=school, instance=syllabus)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Syllabus "{syllabus.title}" has been updated.')
        return redirect('core:syllabus_detail', syllabus_id=syllabus.pk)
    return render(request, 'core/syllabus_form.html', {
        'form': form,
        'syllabus': syllabus,
        'is_edit': True,
    })


@school_admin_required
def syllabus_detail(request, syllabus_id):
    """View syllabus units and add new units."""
    syllabus = get_object_or_404(
        Syllabus.objects.select_related('classroom', 'subject'),
        pk=syllabus_id,
    )
    unit_form = SyllabusUnitForm(request.POST or None)
    if request.method == 'POST' and unit_form.is_valid():
        unit = unit_form.save(commit=False)
        unit.syllabus = syllabus
        if not unit.order:
            last = syllabus.units.order_by('-order').first()
            unit.order = (last.order + 1) if last else 1
        unit.save()
        messages.success(request, f'Unit "{unit.title}" added.')
        return redirect('core:syllabus_detail', syllabus_id=syllabus.pk)
    return render(request, 'core/syllabus_detail.html', {
        'syllabus': syllabus,
        'units': syllabus.units.all(),
        'unit_form': unit_form,
    })


@school_admin_required
def syllabus_delete(request, syllabus_id):
    """Delete a syllabus and its units."""
    syllabus = get_object_or_404(Syllabus, pk=syllabus_id)
    if request.method == 'POST':
        title = syllabus.title
        syllabus.delete()
        messages.success(request, f'Syllabus "{title}" has been deleted.')
        return redirect('core:syllabus_list')
    return redirect('core:syllabus_list')


@school_admin_required
def syllabus_unit_delete(request, unit_id):
    """Delete a syllabus unit."""
    school = get_request_school(request)
    unit = get_object_or_404(
        SyllabusUnit,
        pk=unit_id,
        syllabus__school=school,
    )
    syllabus_id = unit.syllabus_id
    if request.method == 'POST':
        title = unit.title
        unit.delete()
        messages.success(request, f'Unit "{title}" has been removed.')
    return redirect('core:syllabus_detail', syllabus_id=syllabus_id)


# ── Student Management ───────────────────────────────────────────────────────

@school_admin_required
def student_list(request):
    """List students with search and class/section filters."""
    q = request.GET.get('q', '').strip()
    classroom_id = request.GET.get('classroom', '')
    section_id = request.GET.get('section', '')
    status = request.GET.get('status', 'active')

    students = Student.objects.select_related(
        'user', 'section', 'section__classroom', 'parent'
    ).all()

    if status == 'active':
        students = students.filter(user__is_active=True)
    elif status == 'inactive':
        students = students.filter(user__is_active=False)

    if q:
        students = students.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__email__icontains=q)
            | Q(admission_number__icontains=q)
        )
    if section_id.isdigit():
        students = students.filter(section_id=section_id)
    elif classroom_id.isdigit():
        students = students.filter(section__classroom_id=classroom_id)

    paginator = Paginator(students, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    sections = Section.objects.select_related('classroom').all()
    if classroom_id.isdigit():
        sections = sections.filter(classroom_id=classroom_id)

    return render(request, 'core/student_list.html', {
        'students': page_obj,
        'page_obj': page_obj,
        'classrooms': ClassRoom.objects.all(),
        'sections': sections,
        'q': q,
        'classroom_filter': classroom_id,
        'section_filter': section_id,
        'status_filter': status,
    })


@school_admin_required
def student_create(request):
    """Create a new student account and profile."""
    school = get_request_school(request)
    if school and school.is_student_limit_reached:
        limit_label = school.student_limit if school.student_limit is not None else '∞'
        messages.error(
            request,
            f'Student limit reached for {school.name} '
            f'({school.student_count}/{limit_label}). '
            'Please upgrade your plan to add more students.'
        )
        return redirect('core:student_list')

    form = StudentCreateForm(request.POST or None, school=school)
    if request.method == 'POST' and form.is_valid():
        student = form.save(school=school)
        messages.success(
            request,
            f'{student.user.get_full_name()} has been enrolled '
            f'({student.admission_number}).'
        )
        return redirect('core:student_detail', student_id=student.pk)
    return render(request, 'core/student_form.html', {
        'form': form,
        'is_edit': False,
    })


@school_admin_required
def student_detail(request, student_id):
    """Student profile with fees summary and quick links."""
    student = get_object_or_404(
        Student.objects.select_related('user', 'section', 'section__classroom', 'parent'),
        pk=student_id,
    )
    invoices = Invoice.objects.filter(student=student).select_related('fee_structure')
    totals = invoices.aggregate(
        due=Sum('amount_due'),
        paid=Sum('amount_paid'),
    )
    amount_due = totals['due'] or Decimal('0.00')
    amount_paid = totals['paid'] or Decimal('0.00')
    return render(request, 'core/student_detail.html', {
        'student': student,
        'invoices': invoices[:10],
        'invoice_count': invoices.count(),
        'amount_due': amount_due,
        'amount_paid': amount_paid,
        'balance': amount_due - amount_paid,
        'unpaid_count': invoices.filter(status__in=['unpaid', 'partial']).count(),
    })


@school_admin_required
def student_edit(request, student_id):
    """Edit student profile and account details."""
    school = get_request_school(request)
    student = get_object_or_404(Student, pk=student_id)
    form = StudentEditForm(
        request.POST or None,
        school=school,
        student=student,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{student.user.get_full_name()} has been updated.')
        return redirect('core:student_detail', student_id=student.pk)
    return render(request, 'core/student_form.html', {
        'form': form,
        'student': student,
        'is_edit': True,
    })


@school_admin_required
def student_toggle_active(request, student_id):
    """Activate or deactivate a student account."""
    student = get_object_or_404(Student, pk=student_id)
    if request.method == 'POST':
        user = student.user
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        status = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'{user.get_full_name()} has been {status}.')
    return redirect('core:student_detail', student_id=student.pk)


@school_admin_required
def student_delete(request, student_id):
    """
    Soft-delete preferred: deactivate the student account.
    Hard-delete only when confirmed via POST with confirm=delete.
    """
    student = get_object_or_404(Student, pk=student_id)
    if request.method == 'POST':
        name = student.user.get_full_name()
        if request.POST.get('confirm') == 'delete':
            user = student.user
            student.delete()
            user.delete()
            messages.success(request, f'{name} and their account have been permanently deleted.')
            return redirect('core:student_list')
        # Default: deactivate
        student.user.is_active = False
        student.user.save(update_fields=['is_active'])
        messages.success(request, f'{name} has been deactivated.')
        return redirect('core:student_list')
    return redirect('core:student_detail', student_id=student.pk)


# ── School Preferences ───────────────────────────────────────────────────────

@school_admin_required
def school_preferences(request):
    """School Admin: update theme color and fee currency for their school."""
    school = get_request_school(request)
    if not school:
        messages.error(request, 'No school context available.')
        return redirect('core:dashboard')

    form = SchoolPreferencesForm(request.POST or None, instance=school)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request,
            'Preferences saved. Theme and currency are now active for your school.'
        )
        return redirect('core:school_preferences')

    return render(request, 'core/school_preferences.html', {
        'form': form,
        'school': school,
    })


# ── Teacher Portal ───────────────────────────────────────────────────────────

@teacher_required
def teacher_my_classes(request):
    """List sections assigned to the teacher."""
    sections = get_teacher_sections(request.user)
    section_data = []
    for section in sections:
        section_data.append({
            'section': section,
            'student_count': section.students.filter(user__is_active=True).count(),
            'is_class_teacher': section.class_teacher_id == request.user.id,
            'subjects': Subject.objects.filter(
                timetables__section=section,
                timetables__teacher=request.user,
            ).distinct() if request.user.primary_role == 'teacher' else Subject.objects.filter(
                timetables__section=section,
            ).distinct(),
        })
    return render(request, 'core/teacher_my_classes.html', {
        'section_data': section_data,
    })


@teacher_required
def teacher_timetable(request):
    """Weekly timetable for the logged-in teacher."""
    user = request.user
    if user.is_superuser or user.is_school_admin:
        slots = Timetable.objects.filter(
            section__in=get_teacher_sections(user)
        ).select_related('section', 'section__classroom', 'subject', 'teacher')
    else:
        slots = Timetable.objects.filter(teacher=user).select_related(
            'section', 'section__classroom', 'subject', 'teacher'
        )

    days = list(DayOfWeekChoices)
    timetable_by_day = {day.value: [] for day in days}
    for slot in slots.order_by('day_of_week', 'start_time'):
        timetable_by_day.setdefault(slot.day_of_week, []).append(slot)

    day_rows = [(day, timetable_by_day.get(day.value, [])) for day in days]

    return render(request, 'core/teacher_timetable.html', {
        'day_rows': day_rows,
    })


@teacher_required
def teacher_attendance_history(request):
    """Attendance history for teacher-accessible sections."""
    sections = get_teacher_sections(request.user)
    section_id = request.GET.get('section', '')
    date_from = request.GET.get('from', '')
    date_to = request.GET.get('to', '')

    attendances = StudentAttendance.objects.filter(
        section__in=sections,
    ).select_related('student', 'student__user', 'section', 'section__classroom', 'marked_by')

    selected_section = None
    if section_id.isdigit():
        selected_section = sections.filter(pk=section_id).first()
        if selected_section:
            attendances = attendances.filter(section=selected_section)

    if date_from:
        try:
            attendances = attendances.filter(date__gte=datetime.date.fromisoformat(date_from))
        except ValueError:
            date_from = ''
    if date_to:
        try:
            attendances = attendances.filter(date__lte=datetime.date.fromisoformat(date_to))
        except ValueError:
            date_to = ''

    paginator = Paginator(attendances.order_by('-date', 'student__admission_number'), 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'core/teacher_attendance_history.html', {
        'sections': sections,
        'selected_section': selected_section,
        'section_filter': section_id,
        'date_from': date_from,
        'date_to': date_to,
        'attendances': page_obj,
        'page_obj': page_obj,
    })


@teacher_required
def teacher_students(request):
    """Students in the teacher's assigned sections."""
    sections = get_teacher_sections(request.user)
    section_id = request.GET.get('section', '')
    q = request.GET.get('q', '').strip()

    students = Student.objects.filter(
        section__in=sections,
        user__is_active=True,
    ).select_related('user', 'section', 'section__classroom', 'parent')

    if section_id.isdigit():
        students = students.filter(section_id=section_id)
    if q:
        students = students.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(admission_number__icontains=q)
            | Q(user__email__icontains=q)
        )

    paginator = Paginator(students.order_by('admission_number'), 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'core/teacher_students.html', {
        'students': page_obj,
        'page_obj': page_obj,
        'sections': sections,
        'section_filter': section_id,
        'q': q,
    })


@teacher_required
def teacher_student_detail(request, student_id):
    """Read-only student overview for teachers (no fee management)."""
    student = get_object_or_404(
        Student.objects.select_related('user', 'section', 'section__classroom', 'parent'),
        pk=student_id,
    )
    if not can_access_student_data(request.user, student):
        raise Http404("Student record not found.")

    recent_attendance = StudentAttendance.objects.filter(student=student)[:10]
    recent_results = ExamResult.objects.filter(student=student).select_related('exam', 'subject')[:10]

    return render(request, 'core/teacher_student_detail.html', {
        'student': student,
        'recent_attendance': recent_attendance,
        'recent_results': recent_results,
    })


@teacher_required
def teacher_syllabus_list(request):
    """Syllabi for classes the teacher teaches."""
    classrooms, subjects = get_teacher_syllabus_options(request.user)
    syllabi = Syllabus.objects.filter(
        classroom__in=classrooms,
    ).select_related('classroom', 'subject').prefetch_related('units')

    if request.user.primary_role == 'teacher' and not request.user.is_superuser:
        subject_ids = list(subjects.values_list('id', flat=True))
        if subject_ids:
            syllabi = syllabi.filter(subject_id__in=subject_ids)

    return render(request, 'core/teacher_syllabus_list.html', {
        'syllabi': syllabi.distinct(),
        'can_create': classrooms.exists() and subjects.exists(),
    })


@teacher_required
def teacher_syllabus_create(request):
    """Teacher creates a syllabus for an assigned class/subject."""
    school = get_request_school(request) or request.user.school
    classrooms, subjects = get_teacher_syllabus_options(request.user)
    if not classrooms.exists() or not subjects.exists():
        messages.error(
            request,
            'No assigned classes/subjects found. Contact your school admin '
            'to assign you on the timetable first.'
        )
        return redirect('core:teacher_syllabus_list')

    form = SyllabusForm(
        request.POST or None,
        school=school,
        classrooms=classrooms,
        subjects=subjects,
    )
    if request.method == 'POST' and form.is_valid():
        syllabus = form.save(commit=False)
        if not teacher_can_manage_syllabus(request.user, syllabus):
            messages.error(request, 'You cannot create a syllabus for that class/subject.')
            return redirect('core:teacher_syllabus_list')
        if not syllabus.school_id:
            messages.error(request, 'Could not determine school for this syllabus.')
            return redirect('core:teacher_syllabus_list')
        syllabus.save()
        messages.success(request, f'Syllabus "{syllabus.title}" has been created.')
        return redirect('core:teacher_syllabus_detail', syllabus_id=syllabus.pk)

    return render(request, 'core/teacher_syllabus_form.html', {
        'form': form,
        'is_edit': False,
    })


@teacher_required
def teacher_syllabus_edit(request, syllabus_id):
    """Teacher edits a syllabus they can manage."""
    school = get_request_school(request) or request.user.school
    syllabus = get_object_or_404(Syllabus, pk=syllabus_id)
    if not teacher_can_manage_syllabus(request.user, syllabus):
        raise Http404("Syllabus not found.")

    classrooms, subjects = get_teacher_syllabus_options(request.user)
    form = SyllabusForm(
        request.POST or None,
        school=school,
        classrooms=classrooms,
        subjects=subjects,
        instance=syllabus,
    )
    if request.method == 'POST' and form.is_valid():
        updated = form.save(commit=False)
        if not teacher_can_manage_syllabus(request.user, updated):
            messages.error(request, 'You cannot move this syllabus to that class/subject.')
            return redirect('core:teacher_syllabus_detail', syllabus_id=syllabus.pk)
        updated.save()
        messages.success(request, f'Syllabus "{updated.title}" has been updated.')
        return redirect('core:teacher_syllabus_detail', syllabus_id=updated.pk)

    return render(request, 'core/teacher_syllabus_form.html', {
        'form': form,
        'syllabus': syllabus,
        'is_edit': True,
    })


@teacher_required
def teacher_syllabus_detail(request, syllabus_id):
    """View syllabus units and allow teachers to add/remove units."""
    syllabus = get_object_or_404(
        Syllabus.objects.select_related('classroom', 'subject').prefetch_related('units'),
        pk=syllabus_id,
    )
    can_edit = teacher_can_manage_syllabus(request.user, syllabus)
    if not can_edit:
        sections = get_teacher_sections(request.user)
        if not sections.filter(classroom=syllabus.classroom).exists():
            if not (request.user.is_superuser or request.user.is_school_admin):
                raise Http404("Syllabus not found.")

    unit_form = SyllabusUnitForm(request.POST or None) if can_edit else None
    if can_edit and request.method == 'POST' and unit_form.is_valid():
        unit = unit_form.save(commit=False)
        unit.syllabus = syllabus
        if not unit.order:
            last = syllabus.units.order_by('-order').first()
            unit.order = (last.order + 1) if last else 1
        unit.save()
        messages.success(request, f'Unit "{unit.title}" added.')
        return redirect('core:teacher_syllabus_detail', syllabus_id=syllabus.pk)

    return render(request, 'core/teacher_syllabus_detail.html', {
        'syllabus': syllabus,
        'units': syllabus.units.all(),
        'unit_form': unit_form,
        'can_edit': can_edit,
    })


@teacher_required
def teacher_syllabus_unit_delete(request, unit_id):
    """Teacher removes a unit from a syllabus they manage."""
    unit = get_object_or_404(SyllabusUnit.objects.select_related('syllabus'), pk=unit_id)
    syllabus = unit.syllabus
    if not teacher_can_manage_syllabus(request.user, syllabus):
        raise Http404("Unit not found.")
    if request.method == 'POST':
        title = unit.title
        unit.delete()
        messages.success(request, f'Unit "{title}" has been removed.')
    return redirect('core:teacher_syllabus_detail', syllabus_id=syllabus.pk)


@login_required
def profile_view(request):
    """Update profile details and change password."""
    profile_form = ProfileUpdateForm(
        request.POST if request.POST.get('form_type') == 'profile' else None,
        instance=request.user,
    )
    password_form = ChangePasswordForm(
        request.user,
        request.POST if request.POST.get('form_type') == 'password' else None,
    )

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'profile' and profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('core:profile')
        if form_type == 'password' and password_form.is_valid():
            password_form.save()
            # Keep user logged in after password change
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully.')
            return redirect('core:profile')

    return render(request, 'core/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
    })
