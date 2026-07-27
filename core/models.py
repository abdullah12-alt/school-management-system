"""
Core models for the School Management System.

Hierarchy:
    School (tenant) → Department, Role, User, UserRole, ClassRoom, Section,
    Subject, Student, Staff, Timetable, StudentAttendance, Exam, ExamResult,
    FeeStructure, Invoice, Syllabus, SyllabusUnit.
    All school-owned models inherit from TenantModel for automatic scoping.
"""
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.text import slugify

from .managers import TenantManager, UnscopedManager, get_current_school


# ── Choices ──────────────────────────────────────────────────────────────────

class PlanChoices(models.TextChoices):
    FREE = 'free', 'Free'
    BASIC = 'basic', 'Basic'
    PREMIUM = 'premium', 'Premium'


class PrimaryRoleChoices(models.TextChoices):
    SCHOOL_ADMIN = 'school_admin', 'School Admin'
    TEACHER = 'teacher', 'Teacher'
    STAFF = 'staff', 'Staff'
    ACCOUNTANT = 'accountant', 'Accountant'
    LIBRARIAN = 'librarian', 'Librarian'
    STUDENT = 'student', 'Student'
    PARENT = 'parent', 'Parent'


class AttendanceStatusChoices(models.TextChoices):
    PRESENT = 'present', 'Present'
    ABSENT = 'absent', 'Absent'
    LATE = 'late', 'Late'
    LEAVE = 'leave', 'Leave'


class InvoiceStatusChoices(models.TextChoices):
    UNPAID = 'unpaid', 'Unpaid'
    PARTIAL = 'partial', 'Partial'
    PAID = 'paid', 'Paid'


class DayOfWeekChoices(models.TextChoices):
    MONDAY = 'monday', 'Monday'
    TUESDAY = 'tuesday', 'Tuesday'
    WEDNESDAY = 'wednesday', 'Wednesday'
    THURSDAY = 'thursday', 'Thursday'
    FRIDAY = 'friday', 'Friday'
    SATURDAY = 'saturday', 'Saturday'
    SUNDAY = 'sunday', 'Sunday'


class CurrencyChoices(models.TextChoices):
    USD = 'USD', 'US Dollar ($)'
    EUR = 'EUR', 'Euro (€)'
    GBP = 'GBP', 'British Pound (£)'
    PKR = 'PKR', 'Pakistani Rupee (Rs)'
    INR = 'INR', 'Indian Rupee (₹)'
    AED = 'AED', 'UAE Dirham (AED)'
    SAR = 'SAR', 'Saudi Riyal (SAR)'
    CAD = 'CAD', 'Canadian Dollar (C$)'
    AUD = 'AUD', 'Australian Dollar (A$)'


class ThemeColorChoices(models.TextChoices):
    INDIGO = 'indigo', 'Indigo'
    BLUE = 'blue', 'Blue'
    TEAL = 'teal', 'Teal'
    EMERALD = 'emerald', 'Emerald'
    ROSE = 'rose', 'Rose'
    AMBER = 'amber', 'Amber'
    VIOLET = 'violet', 'Violet'
    SLATE = 'slate', 'Slate'


CURRENCY_SYMBOLS = {
    CurrencyChoices.USD: '$',
    CurrencyChoices.EUR: '€',
    CurrencyChoices.GBP: '£',
    CurrencyChoices.PKR: 'Rs',
    CurrencyChoices.INR: '₹',
    CurrencyChoices.AED: 'AED',
    CurrencyChoices.SAR: 'SAR',
    CurrencyChoices.CAD: 'C$',
    CurrencyChoices.AUD: 'A$',
}


# Tailwind-compatible primary palettes for school branding
THEME_PALETTES = {
    ThemeColorChoices.INDIGO: {
        '50': '#eef2ff', '100': '#e0e7ff', '200': '#c7d2fe', '300': '#a5b4fc',
        '400': '#818cf8', '500': '#6366f1', '600': '#4f46e5', '700': '#4338ca',
        '800': '#3730a3', '900': '#312e81', '950': '#1e1b4b',
    },
    ThemeColorChoices.BLUE: {
        '50': '#eff6ff', '100': '#dbeafe', '200': '#bfdbfe', '300': '#93c5fd',
        '400': '#60a5fa', '500': '#3b82f6', '600': '#2563eb', '700': '#1d4ed8',
        '800': '#1e40af', '900': '#1e3a8a', '950': '#172554',
    },
    ThemeColorChoices.TEAL: {
        '50': '#f0fdfa', '100': '#ccfbf1', '200': '#99f6e4', '300': '#5eead4',
        '400': '#2dd4bf', '500': '#14b8a6', '600': '#0d9488', '700': '#0f766e',
        '800': '#115e59', '900': '#134e4a', '950': '#042f2e',
    },
    ThemeColorChoices.EMERALD: {
        '50': '#ecfdf5', '100': '#d1fae5', '200': '#a7f3d0', '300': '#6ee7b7',
        '400': '#34d399', '500': '#10b981', '600': '#059669', '700': '#047857',
        '800': '#065f46', '900': '#064e3b', '950': '#022c22',
    },
    ThemeColorChoices.ROSE: {
        '50': '#fff1f2', '100': '#ffe4e6', '200': '#fecdd3', '300': '#fda4af',
        '400': '#fb7185', '500': '#f43f5e', '600': '#e11d48', '700': '#be123c',
        '800': '#9f1239', '900': '#881337', '950': '#4c0519',
    },
    ThemeColorChoices.AMBER: {
        '50': '#fffbeb', '100': '#fef3c7', '200': '#fde68a', '300': '#fcd34d',
        '400': '#fbbf24', '500': '#f59e0b', '600': '#d97706', '700': '#b45309',
        '800': '#92400e', '900': '#78350f', '950': '#451a03',
    },
    ThemeColorChoices.VIOLET: {
        '50': '#f5f3ff', '100': '#ede9fe', '200': '#ddd6fe', '300': '#c4b5fd',
        '400': '#a78bfa', '500': '#8b5cf6', '600': '#7c3aed', '700': '#6d28d9',
        '800': '#5b21b6', '900': '#4c1d95', '950': '#2e1065',
    },
    ThemeColorChoices.SLATE: {
        '50': '#f8fafc', '100': '#f1f5f9', '200': '#e2e8f0', '300': '#cbd5e1',
        '400': '#94a3b8', '500': '#64748b', '600': '#475569', '700': '#334155',
        '800': '#1e293b', '900': '#0f172a', '950': '#020617',
    },
}

# Roles that School Admins can create
STAFF_ROLES = [
    PrimaryRoleChoices.TEACHER,
    PrimaryRoleChoices.STAFF,
    PrimaryRoleChoices.ACCOUNTANT,
    PrimaryRoleChoices.LIBRARIAN,
]


PLAN_LIMITS = {
    PlanChoices.FREE: {'students': 50, 'staff': 5},
    PlanChoices.BASIC: {'students': 200, 'staff': 25},
    PlanChoices.PREMIUM: {'students': 1000, 'staff': 100},
}


# ── Subscription Plan ────────────────────────────────────────────────────────

class SubscriptionPlan(models.Model):
    """
    Database-backed subscription plan managed by Platform Superadmin.
    Replaces the hardcoded PLAN_LIMITS dict — limits are now editable live
    from the Platform Admin dashboard without touching any code.

    student_limit / staff_limit = NULL means Unlimited (no restriction).
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price_month = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Monthly price in USD. Set to 0 for free plans.',
    )
    student_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum students allowed. Leave blank for Unlimited.',
    )
    staff_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum staff members allowed. Leave blank for Unlimited.',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Only active plans are selectable when assigning to a school.',
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text='Display order in lists (lower = shown first).',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from django.utils.text import slugify as _slugify
        if not self.slug:
            self.slug = _slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def student_limit_display(self):
        return '∞ Unlimited' if self.student_limit is None else str(self.student_limit)

    @property
    def staff_limit_display(self):
        return '∞ Unlimited' if self.staff_limit is None else str(self.staff_limit)

    @property
    def is_unlimited(self):
        return self.student_limit is None and self.staff_limit is None

    @property
    def school_count(self):
        return self.schools.count()


class ActivityTypeChoices(models.TextChoices):
    SCHOOL_CREATED = 'school_created', 'School Created'
    SCHOOL_STATUS_CHANGED = 'school_status_changed', 'School Status Changed'
    PLAN_CHANGED = 'plan_changed', 'Plan Changed'
    ADMIN_ASSIGNED = 'admin_assigned', 'Admin Assigned'
    LOGIN_FAILED = 'login_failed', 'Login Failed'
    USER_STATUS_CHANGED = 'user_status_changed', 'User Status Changed'


class PlatformActivity(models.Model):
    """
    Audit log for platform superadmin activities and tenant events.
    """
    school = models.ForeignKey(
        'School',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performed_activities',
    )
    action_type = models.CharField(
        max_length=35,
        choices=ActivityTypeChoices.choices,
    )
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_type_display()}: {self.description}"


# ── School (Tenant) ─────────────────────────────────────────────────────────

class School(models.Model):
    """
    Top-level tenant model. Every school-owned record references this.
    """
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)
    # Legacy plan field kept for backward-compat; subscription_plan is the live source of truth.
    plan = models.CharField(
        max_length=20,
        choices=PlanChoices.choices,
        default=PlanChoices.FREE,
    )
    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schools',
        help_text='The active subscription plan for this school. Overrides the legacy plan field.',
    )
    is_active = models.BooleanField(default=True)
    currency = models.CharField(
        max_length=3,
        choices=CurrencyChoices.choices,
        default=CurrencyChoices.USD,
        help_text='Currency used for fee invoices at this school.',
    )
    theme_color = models.CharField(
        max_length=20,
        choices=ThemeColorChoices.choices,
        default=ThemeColorChoices.INDIGO,
        help_text='Primary brand color for the school portal UI.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def currency_symbol(self):
        return CURRENCY_SYMBOLS.get(self.currency, self.currency)

    @property
    def theme_palette(self):
        return THEME_PALETTES.get(self.theme_color, THEME_PALETTES[ThemeColorChoices.INDIGO])

    @property
    def effective_plan(self):
        """Returns the SubscriptionPlan if set, otherwise falls back to legacy PLAN_LIMITS."""
        return self.subscription_plan
    @property
    def plan_display_name(self):
        if self.subscription_plan:
            return self.subscription_plan.name
        return self.get_plan_display()

    @property
    def student_count(self):
        return Student.unscoped.filter(school=self).count()

    @property
    def staff_count(self):
        return User.objects.filter(
            school=self,
            primary_role__in=[r.value for r in STAFF_ROLES]
        ).count()

    @property
    def unpaid_invoice_count(self):
        return Invoice.unscoped.filter(school=self, status__in=['unpaid', 'partial']).count()

    @property
    def unpaid_invoice_amount(self):
        return Invoice.unscoped.filter(school=self, status__in=['unpaid', 'partial']).aggregate(models.Sum('amount_due'))['amount_due__sum'] or 0.00

    @property
    def student_limit(self):
        """Returns student cap from linked SubscriptionPlan, or legacy PLAN_LIMITS, or None (unlimited)."""
        if self.subscription_plan is not None:
            return self.subscription_plan.student_limit  # None = unlimited
        return PLAN_LIMITS.get(self.plan, {}).get('students', 50)

    @property
    def staff_limit(self):
        """Returns staff cap from linked SubscriptionPlan, or legacy PLAN_LIMITS, or None (unlimited)."""
        if self.subscription_plan is not None:
            return self.subscription_plan.staff_limit  # None = unlimited
        return PLAN_LIMITS.get(self.plan, {}).get('staff', 5)

    @property
    def is_student_limit_reached(self):
        limit = self.student_limit
        if limit is None:
            return False  # Unlimited plan
        return self.student_count >= limit

    @property
    def is_staff_limit_reached(self):
        limit = self.staff_limit
        if limit is None:
            return False  # Unlimited plan
        return self.staff_count >= limit

    @property
    def student_usage_pct(self):
        limit = self.student_limit
        if not limit:
            return 0
        return min(100, int((self.student_count / limit) * 100))

    @property
    def staff_usage_pct(self):
        limit = self.staff_limit
        if not limit:
            return 0
        return min(100, int((self.staff_count / limit) * 100))


# ── TenantModel (Abstract Base) ─────────────────────────────────────────────

class TenantModel(models.Model):
    """
    Abstract base class for ALL school-scoped models.

    Provides:
        - Automatic query filtering via TenantManager (default manager)
        - An `unscoped` manager for cross-tenant queries
        - Auto-assignment of `school` on save if not already set

    Every model that belongs to a school MUST inherit from this class.
    """
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
    )

    # Default manager — automatically scoped to current school
    objects = TenantManager()

    # Explicit unscoped manager for cross-tenant queries
    unscoped = UnscopedManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Auto-assign school from thread-local if not set
        if not self.school_id:
            current_school = get_current_school()
            if current_school:
                self.school = current_school
        super().save(*args, **kwargs)


# ── Department ───────────────────────────────────────────────────────────────

class Department(TenantModel):
    """Academic or administrative department within a school."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        unique_together = ['school', 'name']

    def __str__(self):
        return self.name


# ── Custom User ──────────────────────────────────────────────────────────────

class UserManager(BaseUserManager):
    """Custom user manager that uses email as the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model with email login and role-based access.

    The `school` field is nullable ONLY for the Platform Super Admin.
    All other users must belong to exactly one school.
    """
    username = None  # Remove username field
    email = models.EmailField('email address', unique=True)
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
    )
    primary_role = models.CharField(
        max_length=20,
        choices=PrimaryRoleChoices.choices,
        blank=True,
    )
    phone = models.CharField(max_length=20, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # email & password are required by default

    objects = UserManager()

    class Meta:
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_primary_role_display()})"

    @property
    def is_school_admin(self):
        return self.primary_role == PrimaryRoleChoices.SCHOOL_ADMIN

    @property
    def is_platform_admin(self):
        return self.is_superuser

    @property
    def role_display(self):
        """Human-readable role label."""
        if self.is_superuser:
            return 'Platform Admin'
        return self.get_primary_role_display()

    def get_extra_roles(self):
        """Return extra Role objects assigned to this user."""
        return Role.unscoped.filter(user_roles__user=self)


# ── Role (Custom/Extra Roles) ───────────────────────────────────────────────

class Role(TenantModel):
    """
    Custom roles that a school can define (e.g., "Class Coordinator",
    "Sports Head"). These are EXTRA roles on top of the primary_role.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        unique_together = ['school', 'name']

    def __str__(self):
        return self.name


# ── UserRole (Many-to-Many through model) ───────────────────────────────────

class UserRole(models.Model):
    """
    Links users to extra roles. A user can hold multiple extra roles
    on top of their primary_role.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_roles',
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_roles',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'role']
        ordering = ['assigned_at']

    def __str__(self):
        return f"{self.user.get_full_name()} → {self.role.name}"


# ── Academic Structure Models ────────────────────────────────────────────────

class ClassRoom(TenantModel):
    """A grade or academic class level (e.g., Grade 10)."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)

    class Meta:
        ordering = ['name']
        unique_together = ['school', 'code']

    def __str__(self):
        return self.name


class Section(TenantModel):
    """A section of a classroom (e.g. Grade 10 - Section A)."""
    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name='sections'
    )
    name = models.CharField(max_length=100)
    class_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_sections'
    )

    class Meta:
        ordering = ['classroom__name', 'name']
        unique_together = ['classroom', 'name']

    def __str__(self):
        return f"{self.classroom.name} - {self.name}"


class Subject(TenantModel):
    """Academic subject taught at the school."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50)

    class Meta:
        ordering = ['name']
        unique_together = ['school', 'code']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Student(TenantModel):
    """Student profile linked to a User account."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        limit_choices_to={'primary_role': PrimaryRoleChoices.PARENT}
    )
    admission_number = models.CharField(max_length=100)

    class Meta:
        ordering = ['admission_number']
        unique_together = ['school', 'admission_number']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.admission_number})"


class Staff(TenantModel):
    """Staff profile linked to a User account."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )
    designation = models.CharField(max_length=100, blank=True)
    subjects = models.ManyToManyField(
        Subject,
        blank=True,
        related_name='teachers'
    )

    class Meta:
        ordering = ['user__first_name', 'user__last_name']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.designation}"


class Timetable(TenantModel):
    """Class schedule slot for a section."""
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='timetables'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='timetables'
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='timetables'
    )
    day_of_week = models.CharField(
        max_length=20,
        choices=DayOfWeekChoices.choices
    )
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.section} | {self.subject.name} | {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


# ── Attendance Models ────────────────────────────────────────────────────────

class StudentAttendance(TenantModel):
    """Daily attendance record per student."""
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=AttendanceStatusChoices.choices,
        default=AttendanceStatusChoices.PRESENT
    )
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendances'
    )
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['-date', 'student']
        unique_together = ['student', 'date']

    def __str__(self):
        return f"{self.student.user.get_full_name()} | {self.date} | {self.get_status_display()}"


# ── Exams & Grading Models ───────────────────────────────────────────────────

class Exam(TenantModel):
    """Examination event for a section."""
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='exams'
    )
    name = models.CharField(max_length=200)
    date = models.DateField()
    max_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)

    class Meta:
        ordering = ['-date', 'name']

    def __str__(self):
        return f"{self.name} ({self.section})"


class ExamResult(TenantModel):
    """Marks obtained by a student in a specific exam and subject."""
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='results'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='exam_results'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='exam_results'
    )
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['student', 'subject']
        unique_together = ['exam', 'student', 'subject']

    def __str__(self):
        return f"{self.student.user.get_full_name()} | {self.exam.name} | {self.subject.code}: {self.marks_obtained}/{self.exam.max_marks}"


# ── Fee & Finance Models ─────────────────────────────────────────────────────

class FeeStructure(TenantModel):
    """Defined fee type and default amount for a school."""
    name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.amount})"


class Invoice(TenantModel):
    """Student fee invoice record."""
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    fee_structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatusChoices.choices,
        default=InvoiceStatusChoices.UNPAID
    )

    class Meta:
        ordering = ['-due_date', '-id']

    def __str__(self):
        return f"Invoice #{self.id} | {self.student.user.get_full_name()} | {self.get_status_display()}"

    @property
    def remaining_balance(self):
        return self.amount_due - self.amount_paid


# ── Syllabus / Curriculum Models ─────────────────────────────────────────────

class Syllabus(TenantModel):
    """Syllabus for a subject taught at a class level."""
    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name='syllabi',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='syllabi',
    )
    title = models.CharField(max_length=200)
    academic_year = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['classroom__name', 'subject__name', 'title']
        verbose_name_plural = 'syllabi'
        unique_together = ['school', 'classroom', 'subject', 'academic_year']

    def __str__(self):
        year = f" ({self.academic_year})" if self.academic_year else ''
        return f"{self.title}{year}"


class SyllabusUnit(models.Model):
    """A chapter or unit within a syllabus."""
    syllabus = models.ForeignKey(
        Syllabus,
        on_delete=models.CASCADE,
        related_name='units',
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.order}. {self.title}"
