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

from .models import (
    School, User, Role, UserRole, PrimaryRoleChoices, STAFF_ROLES,
    Section, Subject, Student, Staff, ClassRoom, Timetable,
    StudentAttendance, Exam, ExamResult, FeeStructure, Invoice,
    AttendanceStatusChoices, InvoiceStatusChoices, PlatformActivity,
    ActivityTypeChoices, PlanChoices, SubscriptionPlan
)
from .forms import (
    LoginForm, StaffCreateForm, RoleAssignmentForm, RoleCreateForm,
    ExamCreateForm, InvoiceCreateForm, SchoolCreateForm, SchoolEditForm,
    SubscriptionPlanForm
)
from .decorators import (
    school_admin_required, teacher_required, accountant_required,
    student_or_parent_required, can_access_student_data
)


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

    # Get sections where user is class_teacher OR assigned in timetable
    managed_sections = Section.objects.filter(
        Q(class_teacher=user) | Q(timetables__teacher=user)
    ).distinct().select_related('classroom')

    return render(request, 'core/dashboard_teacher.html', {
        'sections': managed_sections,
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
        userrole__user=staff_member,
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

@teacher_required
def attendance_mark(request):
    """Teachers mark daily attendance for a section."""
    sections = Section.objects.all().select_related('classroom')
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
        students = Student.objects.filter(section=selected_section).select_related('user')
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
                        'school': request.user.school
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
    """List exams for the school."""
    exams = Exam.objects.all().select_related('section', 'section__classroom')
    return render(request, 'core/exam_list.html', {'exams': exams})


@teacher_required
def exam_create(request):
    """Create a new exam."""
    form = ExamCreateForm(request.POST or None, school=request.user.school)

    if request.method == 'POST' and form.is_valid():
        exam = form.save(commit=False)
        exam.school = request.user.school
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
