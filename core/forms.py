"""
Forms for authentication, account management, attendance, exams, and finance.
"""
from django import forms
from django.contrib.auth import authenticate

from .models import (
    School, User, Role, UserRole, PrimaryRoleChoices, STAFF_ROLES,
    Section, Subject, Exam, Student, FeeStructure, Invoice,
    AttendanceStatusChoices, PlanChoices, SubscriptionPlan
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
        fields = ['name', 'slug', 'plan', 'is_active']
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
        fields = ['name', 'slug', 'subscription_plan', 'plan', 'is_active']
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
