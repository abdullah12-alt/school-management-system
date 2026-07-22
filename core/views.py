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
    User, Role, UserRole, PrimaryRoleChoices, STAFF_ROLES,
    Section, Subject, Student, Staff, ClassRoom, Timetable,
    StudentAttendance, Exam, ExamResult, FeeStructure, Invoice,
    AttendanceStatusChoices, InvoiceStatusChoices
)
from .forms import (
    LoginForm, StaffCreateForm, RoleAssignmentForm, RoleCreateForm,
    ExamCreateForm, InvoiceCreateForm
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
    """Platform Super Admin dashboard."""
    if not request.user.is_superuser:
        return redirect('core:dashboard')

    from .models import School
    schools = School.objects.all()
    total_users = User.objects.count()

    return render(request, 'core/dashboard_superadmin.html', {
        'schools': schools,
        'total_users': total_users,
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
    form = StaffCreateForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.save(school=request.user.school)
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
