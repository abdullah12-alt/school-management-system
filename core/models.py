"""
Core models for the School Management System.

Hierarchy:
    School (tenant) → Department, Role, User, UserRole, ClassRoom, Section,
    Subject, Student, Staff, Timetable, StudentAttendance, Exam, ExamResult,
    FeeStructure, Invoice.
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


# Roles that School Admins can create
STAFF_ROLES = [
    PrimaryRoleChoices.TEACHER,
    PrimaryRoleChoices.STAFF,
    PrimaryRoleChoices.ACCOUNTANT,
    PrimaryRoleChoices.LIBRARIAN,
]


# ── School (Tenant) ─────────────────────────────────────────────────────────

class School(models.Model):
    """
    Top-level tenant model. Every school-owned record references this.
    """
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    logo = models.ImageField(upload_to='school_logos/', blank=True, null=True)
    plan = models.CharField(
        max_length=20,
        choices=PlanChoices.choices,
        default=PlanChoices.FREE,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


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
        return Role.unscoped.filter(userrole__user=self)


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
        return f"{self.name} (${self.amount})"


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
