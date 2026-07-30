"""
Forms for authentication, account management, attendance, exams, and finance.
"""
from django import forms
from django.contrib.auth import authenticate

from .models import (
    School, User, Role, UserRole, PrimaryRoleChoices, STAFF_ROLES,
    ClassRoom, Section, Subject, Exam, Student, FeeStructure, Invoice,
    AttendanceStatusChoices, PlanChoices, SubscriptionPlan,
    Syllabus, SyllabusUnit, Timetable, Homework,
    PaymentRecord, Expense, StaffSalary,
    PaymentMethodChoices, ExpenseCategoryChoices,
    Announcement, AnnouncementPriorityChoices, AnnouncementAudienceChoices,
)


# ── Tailwind CSS classes for form widgets ────────────────────────────────────

INPUT_CSS = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 '
    'focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 '
    'transition duration-200 text-gray-800 text-sm bg-white '
    'placeholder:text-gray-400'
)

SELECT_CSS = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 '
    'focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 '
    'transition duration-200 text-gray-800 text-sm bg-white'
)

CHECKBOX_CSS = (
    'rounded border-gray-300 text-indigo-600 '
    'focus:ring-indigo-500 h-4 w-4'
)


# ── School Management Forms (Platform Superadmin) ───────────────────────────

class SchoolCreateForm(forms.ModelForm):
    """
    Form for Platform Superadmin to create a new School and provision
    its initial School Admin account.
    """
    admin_email = forms.EmailField(
        label='School Admin Email',
        widget=forms.EmailInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'admin@school.edu',
            'id': 'id_admin_email',
        }),
        required=True,
    )
    admin_first_name = forms.CharField(
        label='Admin First Name',
        widget=forms.TextInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'First Name',
            'id': 'id_admin_first_name',
        }),
        required=True,
    )
    admin_last_name = forms.CharField(
        label='Admin Last Name',
        widget=forms.TextInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'Last Name',
            'id': 'id_admin_last_name',
        }),
        required=True,
    )
    admin_password = forms.CharField(
        label='Admin Initial Password',
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'Min. 8 characters',
            'id': 'id_admin_password',
        }),
        required=True,
    )

    class Meta:
        model = School
        fields = ['name', 'slug', 'plan', 'currency', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g., Oakridge International School',
                'id': 'id_name',
            }),
            'slug': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'oakridge (leave blank to auto-slugify)',
                'id': 'id_slug',
            }),
            'plan': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_plan',
            }),
            'currency': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_currency',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': CHECKBOX_CSS,
                'id': 'id_is_active',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['is_active'].initial = True

    def clean_admin_password(self):
        password = self.cleaned_data.get('admin_password')
        if password and len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters.')
        return password

    def clean_admin_email(self):
        email = self.cleaned_data.get('admin_email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email address already exists.')
        return email


class SchoolEditForm(forms.ModelForm):
    """
    Form for Platform Superadmin to update school details.
    """
    class Meta:
        model = School
        fields = ['name', 'slug', 'subscription_plan', 'plan', 'currency', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'id': 'id_name',
            }),
            'slug': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'id': 'id_slug',
            }),
            'subscription_plan': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_subscription_plan',
            }),
            'plan': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_plan',
            }),
            'currency': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_currency',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': CHECKBOX_CSS,
                'id': 'id_is_active',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subscription_plan'].required = False
        self.fields['subscription_plan'].empty_label = '— Use Legacy Plan —'
        self.fields['subscription_plan'].queryset = SubscriptionPlan.objects.filter(is_active=True)


# ── Subscription Plan Management Form (Platform Superadmin) ───────────────────

class SubscriptionPlanForm(forms.ModelForm):
    """
    Form for Platform Superadmin to create or edit a SubscriptionPlan.

    Adds companion boolean checkboxes for Unlimited student/staff limits:
        - 'student_limit_unlimited' → if checked, student_limit is saved as NULL
        - 'staff_limit_unlimited'   → if checked, staff_limit is saved as NULL
    """
    student_limit_unlimited = forms.BooleanField(
        required=False,
        label='No student limit (Unlimited)',
        widget=forms.CheckboxInput(attrs={'class': CHECKBOX_CSS, 'id': 'id_student_limit_unlimited'}),
    )
    staff_limit_unlimited = forms.BooleanField(
        required=False,
        label='No staff limit (Unlimited)',
        widget=forms.CheckboxInput(attrs={'class': CHECKBOX_CSS, 'id': 'id_staff_limit_unlimited'}),
    )

    class Meta:
        model = SubscriptionPlan
        fields = ['name', 'slug', 'description', 'price_month', 'student_limit', 'staff_limit', 'is_active', 'order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g. Free, Basic, Enterprise',
                'id': 'id_name',
            }),
            'slug': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'Leave blank to auto-generate',
                'id': 'id_slug',
            }),
            'description': forms.Textarea(attrs={
                'class': INPUT_CSS,
                'rows': 3,
                'placeholder': 'Short description of this plan...',
                'id': 'id_description',
            }),
            'price_month': forms.NumberInput(attrs={
                'class': INPUT_CSS,
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
                'id': 'id_price_month',
            }),
            'student_limit': forms.NumberInput(attrs={
                'class': INPUT_CSS,
                'min': '0',
                'placeholder': 'e.g. 50',
                'id': 'id_student_limit',
            }),
            'staff_limit': forms.NumberInput(attrs={
                'class': INPUT_CSS,
                'min': '0',
                'placeholder': 'e.g. 5',
                'id': 'id_staff_limit',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': CHECKBOX_CSS,
                'id': 'id_is_active',
            }),
            'order': forms.NumberInput(attrs={
                'class': INPUT_CSS,
                'min': '0',
                'id': 'id_order',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['student_limit'].required = False
        self.fields['staff_limit'].required = False
        # Pre-check 'unlimited' boxes if existing instance has NULL limits
        if self.instance and self.instance.pk:
            if self.instance.student_limit is None:
                self.fields['student_limit_unlimited'].initial = True
            if self.instance.staff_limit is None:
                self.fields['staff_limit_unlimited'].initial = True

    def clean(self):
        cleaned = super().clean()
        # If 'Unlimited' checkbox is ticked, force the numeric limit field to None
        if cleaned.get('student_limit_unlimited'):
            cleaned['student_limit'] = None
        if cleaned.get('staff_limit_unlimited'):
            cleaned['staff_limit'] = None
        return cleaned


# ── Login Form ───────────────────────────────────────────────────────────────

class LoginForm(forms.Form):
    """Email + password login form with inline validation."""
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'you@school.edu',
            'autofocus': True,
            'id': 'id_email',
        }),
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CSS,
            'placeholder': '••••••••',
            'id': 'id_password',
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if user is None:
                raise forms.ValidationError(
                    'Invalid email or password. Please try again.'
                )
            if not user.is_active:
                raise forms.ValidationError(
                    'This account has been deactivated.'
                )
            if user.school and not user.school.is_active:
                raise forms.ValidationError(
                    'Your school account has been deactivated. '
                    'Please contact support.'
                )
            cleaned_data['user'] = user
        return cleaned_data


# ── Staff Create Form ────────────────────────────────────────────────────────

class StaffCreateForm(forms.ModelForm):
    """
    Form for School Admins to create staff accounts.
    The school field is NOT included — it is set server-side.
    """
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'Min. 8 characters',
            'id': 'id_password',
        }),
    )
    password_confirm = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'Re-enter password',
            'id': 'id_password_confirm',
        }),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'primary_role', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'First name',
                'id': 'id_first_name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'Last name',
                'id': 'id_last_name',
            }),
            'email': forms.EmailInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'staff@school.edu',
                'id': 'id_email',
            }),
            'primary_role': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_primary_role',
            }),
            'phone': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': '+1 (555) 123-4567',
                'id': 'id_phone',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['primary_role'].choices = [('', '— Select Role —')] + [
            (role.value, role.label) for role in STAFF_ROLES
        ]
        self.fields['primary_role'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwords do not match.')
        return password_confirm

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 8:
            raise forms.ValidationError(
                'Password must be at least 8 characters.'
            )
        return password

    def save(self, commit=True, school=None):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if school:
            user.school = school
        if commit:
            user.save()
        return user


# ── Role Assignment Form ─────────────────────────────────────────────────────

class RoleAssignmentForm(forms.Form):
    """Form for assigning extra roles to a staff member."""
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': CHECKBOX_CSS,
        }),
        required=False,
        label='Extra Roles',
    )

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            self.fields['roles'].queryset = Role.unscoped.filter(school=school)


# ── Role Create Form ─────────────────────────────────────────────────────────

class RoleCreateForm(forms.ModelForm):
    """Form for creating custom roles within a school."""

    class Meta:
        model = Role
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g., Class Coordinator',
                'id': 'id_role_name',
            }),
            'description': forms.Textarea(attrs={
                'class': INPUT_CSS + ' resize-none',
                'placeholder': 'Describe this role...',
                'rows': 3,
                'id': 'id_role_description',
            }),
        }


# ── Exam Create Form ─────────────────────────────────────────────────────────

class ExamCreateForm(forms.ModelForm):
    """Form for creating an exam for a section."""
    class Meta:
        model = Exam
        fields = ['section', 'name', 'date', 'max_marks']
        widgets = {
            'section': forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_section'}),
            'name': forms.TextInput(attrs={'class': INPUT_CSS, 'placeholder': 'e.g., Midterm Exam 2026', 'id': 'id_name'}),
            'date': forms.DateInput(attrs={'class': INPUT_CSS, 'type': 'date', 'id': 'id_date'}),
            'max_marks': forms.NumberInput(attrs={'class': INPUT_CSS, 'placeholder': '100.00', 'id': 'id_max_marks'}),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            self.fields['section'].queryset = Section.objects.all()


# ── Invoice Create Form ──────────────────────────────────────────────────────

class InvoiceCreateForm(forms.ModelForm):
    """Form for Accountants to create fee invoices."""
    class Meta:
        model = Invoice
        fields = ['student', 'fee_structure', 'amount_due', 'due_date']
        widgets = {
            'student': forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_student'}),
            'fee_structure': forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_fee_structure'}),
            'amount_due': forms.NumberInput(attrs={'class': INPUT_CSS, 'placeholder': '0.00', 'id': 'id_amount_due'}),
            'due_date': forms.DateInput(attrs={'class': INPUT_CSS, 'type': 'date', 'id': 'id_due_date'}),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            self.fields['student'].queryset = Student.objects.all()
            self.fields['fee_structure'].queryset = FeeStructure.objects.all()


# ── Academic Structure Forms ─────────────────────────────────────────────────

class ClassRoomForm(forms.ModelForm):
    """Create or edit a class/grade level."""

    class Meta:
        model = ClassRoom
        fields = ['name', 'code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g., Grade 10',
                'id': 'id_name',
            }),
            'code': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g., G10',
                'id': 'id_code',
            }),
        }


class SectionForm(forms.ModelForm):
    """Create or edit a section under a classroom."""

    class Meta:
        model = Section
        fields = ['classroom', 'name', 'class_teacher']
        widgets = {
            'classroom': forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_classroom'}),
            'name': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g., A',
                'id': 'id_name',
            }),
            'class_teacher': forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_class_teacher'}),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['class_teacher'].required = False
        self.fields['class_teacher'].empty_label = '— No class teacher —'
        if school:
            self.fields['classroom'].queryset = ClassRoom.objects.all()
            self.fields['class_teacher'].queryset = User.objects.filter(
                school=school,
                primary_role=PrimaryRoleChoices.TEACHER,
                is_active=True,
            )


class SubjectForm(forms.ModelForm):
    """Create or edit a subject."""

    class Meta:
        model = Subject
        fields = ['name', 'code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g., Mathematics',
                'id': 'id_name',
            }),
            'code': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g., MATH101',
                'id': 'id_code',
            }),
        }


class TimetableForm(forms.ModelForm):
    """Create or edit a timetable slot for a section."""

    class Meta:
        model = Timetable
        fields = ['section', 'subject', 'teacher', 'day_of_week', 'start_time', 'end_time']
        widgets = {
            'section': forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_section'}),
            'subject': forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_subject'}),
            'teacher': forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_teacher'}),
            'day_of_week': forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_day_of_week'}),
            'start_time': forms.TimeInput(attrs={
                'class': INPUT_CSS,
                'type': 'time',
                'id': 'id_start_time',
            }),
            'end_time': forms.TimeInput(attrs={
                'class': INPUT_CSS,
                'type': 'time',
                'id': 'id_end_time',
            }),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            self.fields['section'].queryset = Section.objects.select_related('classroom').all()
            self.fields['subject'].queryset = Subject.objects.all()
            self.fields['teacher'].queryset = User.objects.filter(
                school=school,
                primary_role=PrimaryRoleChoices.TEACHER,
                is_active=True,
            )

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_time')
        end = cleaned.get('end_time')
        if start and end and end <= start:
            self.add_error('end_time', 'End time must be after start time.')

        section = cleaned.get('section')
        teacher = cleaned.get('teacher')
        day = cleaned.get('day_of_week')
        if section and teacher and day and start and end:
            # Teacher overlap on same day
            teacher_conflicts = Timetable.objects.filter(
                teacher=teacher,
                day_of_week=day,
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
            for slot in teacher_conflicts:
                if start < slot.end_time and end > slot.start_time:
                    self.add_error(
                        'teacher',
                        f'Teacher already has a class at {slot.start_time.strftime("%H:%M")}-'
                        f'{slot.end_time.strftime("%H:%M")} ({slot.section}).'
                    )
                    break

            # Section overlap on same day
            section_conflicts = Timetable.objects.filter(
                section=section,
                day_of_week=day,
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
            for slot in section_conflicts:
                if start < slot.end_time and end > slot.start_time:
                    self.add_error(
                        'section',
                        f'This section already has {slot.subject.name} at '
                        f'{slot.start_time.strftime("%H:%M")}-{slot.end_time.strftime("%H:%M")}.'
                    )
                    break
        return cleaned


class SyllabusForm(forms.ModelForm):
    """Create or edit a syllabus for a class + subject."""

    class Meta:
        model = Syllabus
        fields = ['classroom', 'subject', 'title', 'academic_year', 'description']
        widgets = {
            'classroom': forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_classroom'}),
            'subject': forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_subject'}),
            'title': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g., Grade 10 Mathematics Syllabus',
                'id': 'id_title',
            }),
            'academic_year': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g., 2025-26',
                'id': 'id_academic_year',
            }),
            'description': forms.Textarea(attrs={
                'class': INPUT_CSS + ' resize-none',
                'rows': 3,
                'placeholder': 'Optional overview...',
                'id': 'id_description',
            }),
        }

    def __init__(self, *args, school=None, classrooms=None, subjects=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._school = school
        self.fields['academic_year'].required = False
        self.fields['description'].required = False
        if classrooms is not None:
            self.fields['classroom'].queryset = classrooms
        elif school:
            self.fields['classroom'].queryset = ClassRoom.objects.all()
        if subjects is not None:
            self.fields['subject'].queryset = subjects
        elif school:
            self.fields['subject'].queryset = Subject.objects.all()

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Always bind tenant from classroom — request/thread school can be unset
        # (e.g. platform admin without impersonation).
        if not instance.school_id:
            classroom = self.cleaned_data.get('classroom') or instance.classroom
            school_id = getattr(self._school, 'pk', None) or getattr(classroom, 'school_id', None)
            if not school_id and getattr(instance, 'classroom_id', None):
                school_id = (
                    ClassRoom.unscoped
                    .filter(pk=instance.classroom_id)
                    .values_list('school_id', flat=True)
                    .first()
                )
            if school_id:
                instance.school_id = school_id
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class SyllabusUnitForm(forms.ModelForm):
    """Add a chapter/unit to a syllabus."""

    class Meta:
        model = SyllabusUnit
        fields = ['title', 'description', 'order']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g., Algebra — Linear Equations',
                'id': 'id_unit_title',
            }),
            'description': forms.Textarea(attrs={
                'class': INPUT_CSS + ' resize-none',
                'rows': 2,
                'placeholder': 'Topics covered in this unit...',
                'id': 'id_unit_description',
            }),
            'order': forms.NumberInput(attrs={
                'class': INPUT_CSS,
                'min': '0',
                'id': 'id_unit_order',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['order'].required = False
        self.fields['order'].initial = 0


# ── Student Management Forms ─────────────────────────────────────────────────

class StudentCreateForm(forms.Form):
    """Create a student user account + student profile."""
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'First name',
            'id': 'id_first_name',
        }),
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'Last name',
            'id': 'id_last_name',
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'student@school.edu',
            'id': 'id_email',
        }),
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': INPUT_CSS,
            'placeholder': '+1 (555) 123-4567',
            'id': 'id_phone',
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'Min. 8 characters',
            'id': 'id_password',
        }),
    )
    password_confirm = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'Re-enter password',
            'id': 'id_password_confirm',
        }),
    )
    admission_number = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': INPUT_CSS,
            'placeholder': 'e.g., ADM-2026-001',
            'id': 'id_admission_number',
        }),
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        required=False,
        empty_label='— Unassigned —',
        widget=forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_section'}),
    )
    parent = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        empty_label='— No parent linked —',
        widget=forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_parent'}),
    )

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.school = school
        if school:
            self.fields['section'].queryset = Section.objects.select_related('classroom').all()
            self.fields['parent'].queryset = User.objects.filter(
                school=school,
                primary_role=PrimaryRoleChoices.PARENT,
                is_active=True,
            )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean_admission_number(self):
        admission_number = self.cleaned_data.get('admission_number')
        if admission_number and self.school:
            if Student.unscoped.filter(school=self.school, admission_number=admission_number).exists():
                raise forms.ValidationError('This admission number is already in use.')
        return admission_number

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters.')
        return password

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Passwords do not match.')
        return password_confirm

    def save(self, school):
        user = User.objects.create_user(
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            phone=self.cleaned_data.get('phone', ''),
            school=school,
            primary_role=PrimaryRoleChoices.STUDENT,
        )
        student = Student(
            user=user,
            school=school,
            admission_number=self.cleaned_data['admission_number'],
            section=self.cleaned_data.get('section'),
            parent=self.cleaned_data.get('parent'),
        )
        student.save()
        return student


class StudentEditForm(forms.Form):
    """Edit an existing student's profile and account details."""
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': INPUT_CSS, 'id': 'id_first_name'}),
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': INPUT_CSS, 'id': 'id_last_name'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': INPUT_CSS, 'id': 'id_email'}),
    )
    phone = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': INPUT_CSS, 'id': 'id_phone'}),
    )
    admission_number = forms.CharField(
        widget=forms.TextInput(attrs={'class': INPUT_CSS, 'id': 'id_admission_number'}),
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        required=False,
        empty_label='— Unassigned —',
        widget=forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_section'}),
    )
    parent = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        empty_label='— No parent linked —',
        widget=forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_parent'}),
    )

    def __init__(self, *args, school=None, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.school = school
        self.student = student
        if school:
            self.fields['section'].queryset = Section.objects.select_related('classroom').all()
            self.fields['parent'].queryset = User.objects.filter(
                school=school,
                primary_role=PrimaryRoleChoices.PARENT,
                is_active=True,
            )
        if student and not kwargs.get('data'):
            user = student.user
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            self.fields['phone'].initial = user.phone
            self.fields['admission_number'].initial = student.admission_number
            self.fields['section'].initial = student.section_id
            self.fields['parent'].initial = student.parent_id

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and self.student:
            qs = User.objects.filter(email__iexact=email).exclude(pk=self.student.user_id)
            if qs.exists():
                raise forms.ValidationError('A user with this email already exists.')
        return email

    def clean_admission_number(self):
        admission_number = self.cleaned_data.get('admission_number')
        if admission_number and self.school and self.student:
            qs = Student.unscoped.filter(
                school=self.school,
                admission_number=admission_number,
            ).exclude(pk=self.student.pk)
            if qs.exists():
                raise forms.ValidationError('This admission number is already in use.')
        return admission_number

    def save(self):
        user = self.student.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone', '')
        user.save()
        self.student.admission_number = self.cleaned_data['admission_number']
        self.student.section = self.cleaned_data.get('section')
        self.student.parent = self.cleaned_data.get('parent')
        self.student.save()
        return self.student


# ── School Preferences Form ──────────────────────────────────────────────────

class SchoolPreferencesForm(forms.ModelForm):
    """School Admin preferences: theme color and fee currency."""

    class Meta:
        model = School
        fields = ['theme_color', 'currency']
        widgets = {
            'theme_color': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_theme_color',
            }),
            'currency': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_currency',
            }),
        }


# ── Profile / Password Forms ─────────────────────────────────────────────────

class ProfileUpdateForm(forms.ModelForm):
    """Update basic profile details for the logged-in user."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': INPUT_CSS, 'id': 'id_first_name'}),
            'last_name': forms.TextInput(attrs={'class': INPUT_CSS, 'id': 'id_last_name'}),
            'phone': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': '+1 (555) 123-4567',
                'id': 'id_phone',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True


class ChangePasswordForm(forms.Form):
    """Change password for the logged-in user."""
    current_password = forms.CharField(
        label='Current Password',
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CSS,
            'id': 'id_current_password',
            'placeholder': 'Current password',
        }),
    )
    new_password = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CSS,
            'id': 'id_new_password',
            'placeholder': 'Min. 8 characters',
        }),
    )
    new_password_confirm = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': INPUT_CSS,
            'id': 'id_new_password_confirm',
            'placeholder': 'Re-enter new password',
        }),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        current = self.cleaned_data.get('current_password')
        if current and not self.user.check_password(current):
            raise forms.ValidationError('Current password is incorrect.')
        return current

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if password and len(password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters.')
        return password

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get('new_password')
        confirm = cleaned.get('new_password_confirm')
        if new and confirm and new != confirm:
            self.add_error('new_password_confirm', 'Passwords do not match.')
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save()
        return self.user


# ── Finance: Fee Structure Form ─────────────────────────────────────────────

class FeeStructureForm(forms.ModelForm):
    """Create or edit a fee structure (fee type and default amount)."""

    class Meta:
        model = FeeStructure
        fields = ['name', 'amount', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g., Tuition Fee',
                'id': 'id_fs_name',
            }),
            'amount': forms.NumberInput(attrs={
                'class': INPUT_CSS,
                'placeholder': '0.00',
                'step': '0.01',
                'id': 'id_fs_amount',
            }),
            'description': forms.Textarea(attrs={
                'class': INPUT_CSS + ' resize-none',
                'placeholder': 'Optional description...',
                'rows': 3,
                'id': 'id_fs_description',
            }),
        }


# ── Finance: Record Payment Form ─────────────────────────────────────────────

class RecordPaymentForm(forms.ModelForm):
    """Record a payment against an invoice."""

    class Meta:
        model = PaymentRecord
        fields = ['amount', 'payment_date', 'payment_method', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': INPUT_CSS,
                'placeholder': '0.00',
                'step': '0.01',
                'id': 'id_payment_amount',
            }),
            'payment_date': forms.DateInput(attrs={
                'class': INPUT_CSS,
                'type': 'date',
                'id': 'id_payment_date',
            }),
            'payment_method': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_payment_method',
            }),
            'notes': forms.Textarea(attrs={
                'class': INPUT_CSS + ' resize-none',
                'placeholder': 'Optional notes...',
                'rows': 2,
                'id': 'id_payment_notes',
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Payment amount must be greater than zero.')
        return amount


# ── Finance: Bulk Invoice Form ───────────────────────────────────────────────

class BulkInvoiceForm(forms.Form):
    """Generate invoices for all students in a classroom/section."""
    classroom = forms.ModelChoiceField(
        queryset=ClassRoom.objects.none(),
        required=False,
        empty_label='All Classrooms',
        widget=forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_bi_classroom'}),
    )
    section = forms.ModelChoiceField(
        queryset=Section.objects.none(),
        required=False,
        empty_label='All Sections',
        widget=forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_bi_section'}),
    )
    fee_structure = forms.ModelChoiceField(
        queryset=FeeStructure.objects.none(),
        widget=forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_bi_fee_structure'}),
    )
    amount_due = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': INPUT_CSS,
            'placeholder': '0.00',
            'step': '0.01',
            'id': 'id_bi_amount_due',
        }),
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': INPUT_CSS,
            'type': 'date',
            'id': 'id_bi_due_date',
        }),
    )

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        if school:
            self.fields['classroom'].queryset = ClassRoom.objects.all()
            self.fields['section'].queryset = Section.objects.select_related('classroom').all()
            self.fields['fee_structure'].queryset = FeeStructure.objects.all()

    def clean(self):
        cleaned = super().clean()
        classroom = cleaned.get('classroom')
        section = cleaned.get('section')
        if section and classroom and section.classroom != classroom:
            self.add_error('section', 'Selected section does not belong to the selected classroom.')
        return cleaned


# ── Finance: Expense Form ────────────────────────────────────────────────────

class ExpenseForm(forms.ModelForm):
    """Create or edit a school expense."""

    class Meta:
        model = Expense
        fields = ['title', 'category', 'amount', 'expense_date', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g., Electricity Bill',
                'id': 'id_exp_title',
            }),
            'category': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_exp_category',
            }),
            'amount': forms.NumberInput(attrs={
                'class': INPUT_CSS,
                'placeholder': '0.00',
                'step': '0.01',
                'id': 'id_exp_amount',
            }),
            'expense_date': forms.DateInput(attrs={
                'class': INPUT_CSS,
                'type': 'date',
                'id': 'id_exp_date',
            }),
            'description': forms.Textarea(attrs={
                'class': INPUT_CSS + ' resize-none',
                'placeholder': 'Additional details...',
                'rows': 3,
                'id': 'id_exp_description',
            }),
        }


# ── Finance: Staff Salary Form ─────────────────────────────────────────────────

class StaffSalaryForm(forms.ModelForm):
    """Create or edit a staff salary record."""

    class Meta:
        model = StaffSalary
        fields = ['staff_user', 'month', 'base_salary', 'bonus', 'deductions', 'is_paid', 'paid_date', 'notes']
        widgets = {
            'staff_user': forms.Select(attrs={'class': SELECT_CSS, 'id': 'id_sal_staff'}),
            'month': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'YYYY-MM e.g. 2026-07',
                'id': 'id_sal_month',
            }),
            'base_salary': forms.NumberInput(attrs={
                'class': INPUT_CSS,
                'placeholder': '0.00',
                'step': '0.01',
                'id': 'id_sal_base',
            }),
            'bonus': forms.NumberInput(attrs={
                'class': INPUT_CSS,
                'placeholder': '0.00',
                'step': '0.01',
                'id': 'id_sal_bonus',
            }),
            'deductions': forms.NumberInput(attrs={
                'class': INPUT_CSS,
                'placeholder': '0.00',
                'step': '0.01',
                'id': 'id_sal_deductions',
            }),
            'is_paid': forms.CheckboxInput(attrs={
                'class': CHECKBOX_CSS,
                'id': 'id_sal_is_paid',
            }),
            'paid_date': forms.DateInput(attrs={
                'class': INPUT_CSS,
                'type': 'date',
                'id': 'id_sal_paid_date',
            }),
            'notes': forms.Textarea(attrs={
                'class': INPUT_CSS + ' resize-none',
                'placeholder': 'Optional notes...',
                'rows': 2,
                'id': 'id_sal_notes',
            }),
        }

    def __init__(self, *args, school=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['paid_date'].required = False
        self.fields['notes'].required = False
        if school:
            self.fields['staff_user'].queryset = User.objects.filter(
                school=school,
                primary_role__in=['teacher', 'staff', 'accountant', 'librarian'],
                is_active=True,
            )


class HomeworkForm(forms.ModelForm):
    """Form for teachers to assign daily homework."""
    class Meta:
        model = Homework
        fields = ['section', 'subject', 'title', 'due_date', 'description']
        widgets = {
            'section': forms.Select(attrs={'class': INPUT_CSS}),
            'subject': forms.Select(attrs={'class': INPUT_CSS}),
            'title': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g. Read Chapter 4',
            }),
            'due_date': forms.DateInput(attrs={
                'class': INPUT_CSS,
                'type': 'date',
            }),
            'description': forms.Textarea(attrs={
                'class': INPUT_CSS,
                'placeholder': 'Detailed instructions for the homework...',
                'rows': 4,
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.primary_role == 'teacher':
            # Limit to sections and subjects the teacher is assigned to in timetable
            self.fields['section'].queryset = Section.objects.filter(
                timetables__teacher=user
            ).distinct()
            self.fields['subject'].queryset = Subject.objects.filter(
                timetables__teacher=user
            ).distinct()
        elif user:
            # If admin or other, limit to the school
            self.fields['section'].queryset = Section.objects.filter(classroom__school=user.school)
            self.fields['subject'].queryset = Subject.objects.filter(school=user.school)


class AnnouncementForm(forms.ModelForm):
    """Form for creating / editing school announcements."""
    class Meta:
        model = Announcement
        fields = ['title', 'body', 'priority', 'audience', 'section', 'is_pinned', 'expires_at']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': INPUT_CSS,
                'placeholder': 'e.g. Midterm Exams Schedule Released',
                'id': 'id_title',
            }),
            'body': forms.Textarea(attrs={
                'class': INPUT_CSS,
                'placeholder': 'Write your announcement details here...',
                'rows': 5,
                'id': 'id_body',
            }),
            'priority': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_priority',
            }),
            'audience': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_audience',
            }),
            'section': forms.Select(attrs={
                'class': SELECT_CSS,
                'id': 'id_section',
            }),
            'is_pinned': forms.CheckboxInput(attrs={
                'class': CHECKBOX_CSS,
                'id': 'id_is_pinned',
            }),
            'expires_at': forms.DateTimeInput(attrs={
                'class': INPUT_CSS,
                'type': 'datetime-local',
                'id': 'id_expires_at',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['section'].required = False
        self.fields['expires_at'].required = False
        if user and hasattr(user, 'school') and user.school:
            self.fields['section'].queryset = Section.objects.filter(
                classroom__school=user.school
            ).select_related('classroom')
        self.fields['section'].empty_label = '— Select section —'

    def clean(self):
        cleaned_data = super().clean()
        audience = cleaned_data.get('audience')
        section = cleaned_data.get('section')
        if audience == AnnouncementAudienceChoices.SECTION and not section:
            self.add_error('section', 'You must select a section when audience is "Specific Section".')
        if audience != AnnouncementAudienceChoices.SECTION:
            cleaned_data['section'] = None
        return cleaned_data
