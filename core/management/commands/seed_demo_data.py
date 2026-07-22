"""
Management command to seed demo data for two schools.

Creates:
    - 2 schools: Greenwood Academy and Sunrise School
    - 1 Platform Super Admin
    - 1 School Admin, 1 Teacher, 1 Accountant, 1 Librarian, 1 Staff per school
    - 1 Parent + 1 Student (linked) per school
    - 2 custom roles per school
    - Classroom, Section, Subjects, Staff Profile
    - Timetable entry
    - 10 Attendance records per student
    - Fee Structure + Invoice
    - Exam + Exam Result

Run:
    python manage.py seed_demo_data
"""
import datetime
from django.core.management.base import BaseCommand

from core.models import (
    School, User, Role, UserRole, Department,
    ClassRoom, Section, Subject, Student, Staff, Timetable,
    StudentAttendance, Exam, ExamResult, FeeStructure, Invoice
)


class Command(BaseCommand):
    help = 'Seeds demo data for 2 schools with complete academic/financial records.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Seeding demo data...'))

        # ── Platform Super Admin ─────────────────────────────────────
        superadmin, created = User.objects.get_or_create(
            email='admin@schoolhub.com',
            defaults={
                'first_name': 'Platform',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            superadmin.set_password('admin123456')
            superadmin.save()
        self.stdout.write('  [+] Platform Admin: admin@schoolhub.com / admin123456')

        # ── School A: Greenwood Academy ──────────────────────────────
        school_a, _ = School.objects.get_or_create(
            slug='greenwood',
            defaults={'name': 'Greenwood Academy', 'plan': 'premium', 'is_active': True}
        )
        self.stdout.write(f'  [+] School A: {school_a.name}')

        # School Admin A
        admin_a, created = User.objects.get_or_create(
            email='admin@greenwood.edu',
            defaults={'first_name': 'Sarah', 'last_name': 'Johnson',
                      'school': school_a, 'primary_role': 'school_admin'}
        )
        if created:
            admin_a.set_password('greenwood123')
            admin_a.save()
        self.stdout.write('  [+] School Admin A: admin@greenwood.edu / greenwood123')

        # Teacher A
        teacher_a, created = User.objects.get_or_create(
            email='james.w@greenwood.edu',
            defaults={'first_name': 'James', 'last_name': 'Williams',
                      'school': school_a, 'primary_role': 'teacher', 'phone': '+1 555-0101'}
        )
        if created:
            teacher_a.set_password('teacher123')
            teacher_a.save()
        self.stdout.write('  [+] Teacher A: james.w@greenwood.edu / teacher123')

        # Accountant A
        acct_a, created = User.objects.get_or_create(
            email='mark.a@greenwood.edu',
            defaults={'first_name': 'Mark', 'last_name': 'Anderson',
                      'school': school_a, 'primary_role': 'accountant', 'phone': '+1 555-0103'}
        )
        if created:
            acct_a.set_password('account123')
            acct_a.save()
        self.stdout.write('  [+] Accountant A: mark.a@greenwood.edu / account123')

        # Librarian A
        lib_a, created = User.objects.get_or_create(
            email='lib.a@greenwood.edu',
            defaults={'first_name': 'Grace', 'last_name': 'Turner',
                      'school': school_a, 'primary_role': 'librarian'}
        )
        if created:
            lib_a.set_password('library123')
            lib_a.save()
        self.stdout.write('  [+] Librarian A: lib.a@greenwood.edu / library123')

        # Staff A
        staff_a_user, created = User.objects.get_or_create(
            email='staff.a@greenwood.edu',
            defaults={'first_name': 'Tom', 'last_name': 'Harris',
                      'school': school_a, 'primary_role': 'staff'}
        )
        if created:
            staff_a_user.set_password('staff123')
            staff_a_user.save()
        self.stdout.write('  [+] Staff A: staff.a@greenwood.edu / staff123')

        # Parent A
        parent_a, created = User.objects.get_or_create(
            email='parent.a@greenwood.edu',
            defaults={'first_name': 'Robert', 'last_name': 'Smith',
                      'school': school_a, 'primary_role': 'parent', 'phone': '+1 555-0199'}
        )
        if created:
            parent_a.set_password('parent123')
            parent_a.save()
        self.stdout.write('  [+] Parent A: parent.a@greenwood.edu / parent123')

        # Student A
        student_user_a, created = User.objects.get_or_create(
            email='student.a@greenwood.edu',
            defaults={'first_name': 'Alice', 'last_name': 'Smith',
                      'school': school_a, 'primary_role': 'student', 'phone': '+1 555-0188'}
        )
        if created:
            student_user_a.set_password('student123')
            student_user_a.save()
        self.stdout.write('  [+] Student A: student.a@greenwood.edu / student123')

        # Custom Roles A
        role_a1, _ = Role.unscoped.get_or_create(school=school_a, name='Class Coordinator', defaults={'description': 'Coordinates between classes and parents'})
        role_a2, _ = Role.unscoped.get_or_create(school=school_a, name='Sports Head', defaults={'description': 'Manages school sports activities'})
        UserRole.objects.get_or_create(user=teacher_a, role=role_a1)

        # Classroom & Section A
        class_a, _ = ClassRoom.unscoped.get_or_create(school=school_a, code='G10', defaults={'name': 'Grade 10'})
        section_a, _ = Section.unscoped.get_or_create(
            classroom=class_a, name='Section A',
            defaults={'school': school_a, 'class_teacher': teacher_a}
        )

        # Subjects A
        math_a, _ = Subject.unscoped.get_or_create(school=school_a, code='MATH101', defaults={'name': 'Mathematics'})
        sci_a, _ = Subject.unscoped.get_or_create(school=school_a, code='SCI101', defaults={'name': 'Science'})
        eng_a, _ = Subject.unscoped.get_or_create(school=school_a, code='ENG101', defaults={'name': 'English'})

        # Staff Profile A
        staff_profile_a, _ = Staff.unscoped.get_or_create(
            school=school_a, user=teacher_a,
            defaults={'designation': 'Senior Mathematics Teacher'}
        )
        staff_profile_a.subjects.set([math_a, sci_a])

        # Timetable A
        Timetable.unscoped.get_or_create(
            school=school_a, section=section_a, subject=math_a, teacher=teacher_a,
            day_of_week='monday',
            defaults={'start_time': '08:00', 'end_time': '09:00'}
        )
        Timetable.unscoped.get_or_create(
            school=school_a, section=section_a, subject=sci_a, teacher=teacher_a,
            day_of_week='tuesday',
            defaults={'start_time': '09:00', 'end_time': '10:00'}
        )

        # Student A Profile
        student_a, _ = Student.unscoped.get_or_create(
            school=school_a, user=student_user_a,
            defaults={'section': section_a, 'parent': parent_a, 'admission_number': 'GW-2026-001'}
        )

        # Attendance Records A (10 records, mix of statuses)
        today = datetime.date.today()
        attendance_data = [
            (today - datetime.timedelta(days=9), 'present'),
            (today - datetime.timedelta(days=8), 'present'),
            (today - datetime.timedelta(days=7), 'absent'),
            (today - datetime.timedelta(days=6), 'present'),
            (today - datetime.timedelta(days=5), 'late'),
            (today - datetime.timedelta(days=4), 'present'),
            (today - datetime.timedelta(days=3), 'present'),
            (today - datetime.timedelta(days=2), 'present'),
            (today - datetime.timedelta(days=1), 'leave'),
            (today, 'present'),
        ]
        for att_date, att_status in attendance_data:
            StudentAttendance.unscoped.get_or_create(
                school=school_a, student=student_a, date=att_date,
                defaults={'section': section_a, 'status': att_status, 'marked_by': teacher_a}
            )

        # Fee & Invoice A
        fee_a, _ = FeeStructure.unscoped.get_or_create(school=school_a, name='Tuition Fee Q1', defaults={'amount': 1500.00})
        Invoice.unscoped.get_or_create(
            school=school_a, student=student_a, fee_structure=fee_a,
            defaults={'amount_due': 1500.00, 'amount_paid': 500.00,
                      'due_date': today + datetime.timedelta(days=30), 'status': 'partial'}
        )

        # Second Invoice (fully paid)
        fee_activity, _ = FeeStructure.unscoped.get_or_create(school=school_a, name='Activity Fee', defaults={'amount': 200.00})
        Invoice.unscoped.get_or_create(
            school=school_a, student=student_a, fee_structure=fee_activity,
            defaults={'amount_due': 200.00, 'amount_paid': 200.00,
                      'due_date': today - datetime.timedelta(days=30), 'status': 'paid'}
        )

        # Exam A & Results
        exam_a, _ = Exam.unscoped.get_or_create(
            school=school_a, section=section_a, name='Midterm Exam 2026',
            defaults={'date': today - datetime.timedelta(days=14), 'max_marks': 100.00}
        )
        ExamResult.unscoped.get_or_create(school=school_a, exam=exam_a, student=student_a, subject=math_a, defaults={'marks_obtained': 92.50})
        ExamResult.unscoped.get_or_create(school=school_a, exam=exam_a, student=student_a, subject=sci_a, defaults={'marks_obtained': 88.00})
        ExamResult.unscoped.get_or_create(school=school_a, exam=exam_a, student=student_a, subject=eng_a, defaults={'marks_obtained': 79.00})

        exam_a2, _ = Exam.unscoped.get_or_create(
            school=school_a, section=section_a, name='Unit Test 1',
            defaults={'date': today - datetime.timedelta(days=30), 'max_marks': 50.00}
        )
        ExamResult.unscoped.get_or_create(school=school_a, exam=exam_a2, student=student_a, subject=math_a, defaults={'marks_obtained': 47.00})
        ExamResult.unscoped.get_or_create(school=school_a, exam=exam_a2, student=student_a, subject=eng_a, defaults={'marks_obtained': 41.00})

        # ── School B: Sunrise School ─────────────────────────────────
        school_b, _ = School.objects.get_or_create(
            slug='sunrise',
            defaults={'name': 'Sunrise School', 'plan': 'basic', 'is_active': True}
        )
        self.stdout.write(f'  [+] School B: {school_b.name}')

        admin_b, created = User.objects.get_or_create(
            email='admin@sunrise.edu',
            defaults={'first_name': 'Michael', 'last_name': 'Chen',
                      'school': school_b, 'primary_role': 'school_admin'}
        )
        if created:
            admin_b.set_password('sunrise123')
            admin_b.save()
        self.stdout.write('  [+] School Admin B: admin@sunrise.edu / sunrise123')

        teacher_b, created = User.objects.get_or_create(
            email='lisa.m@sunrise.edu',
            defaults={'first_name': 'Lisa', 'last_name': 'Martinez',
                      'school': school_b, 'primary_role': 'teacher'}
        )
        if created:
            teacher_b.set_password('teacher123')
            teacher_b.save()
        self.stdout.write('  [+] Teacher B: lisa.m@sunrise.edu / teacher123')

        parent_b, created = User.objects.get_or_create(
            email='parent.b@sunrise.edu',
            defaults={'first_name': 'David', 'last_name': 'Brown',
                      'school': school_b, 'primary_role': 'parent'}
        )
        if created:
            parent_b.set_password('parent123')
            parent_b.save()

        student_user_b, created = User.objects.get_or_create(
            email='student.b@sunrise.edu',
            defaults={'first_name': 'Bob', 'last_name': 'Brown',
                      'school': school_b, 'primary_role': 'student'}
        )
        if created:
            student_user_b.set_password('student123')
            student_user_b.save()

        class_b, _ = ClassRoom.unscoped.get_or_create(school=school_b, code='G11', defaults={'name': 'Grade 11'})
        section_b, _ = Section.unscoped.get_or_create(
            classroom=class_b, name='Section A',
            defaults={'school': school_b, 'class_teacher': teacher_b}
        )
        subject_b, _ = Subject.unscoped.get_or_create(school=school_b, code='ENG101', defaults={'name': 'English Literature'})

        student_b, _ = Student.unscoped.get_or_create(
            school=school_b, user=student_user_b,
            defaults={'section': section_b, 'parent': parent_b, 'admission_number': 'SR-2026-001'}
        )

        for att_date, att_status in attendance_data:
            StudentAttendance.unscoped.get_or_create(
                school=school_b, student=student_b, date=att_date,
                defaults={'section': section_b, 'status': att_status, 'marked_by': teacher_b}
            )

        fee_b, _ = FeeStructure.unscoped.get_or_create(school=school_b, name='Annual Fee', defaults={'amount': 2000.00})
        Invoice.unscoped.get_or_create(
            school=school_b, student=student_b, fee_structure=fee_b,
            defaults={'amount_due': 2000.00, 'amount_paid': 0.00,
                      'due_date': today + datetime.timedelta(days=15), 'status': 'unpaid'}
        )

        exam_b, _ = Exam.unscoped.get_or_create(
            school=school_b, section=section_b, name='Sunrise Quiz 1',
            defaults={'date': today - datetime.timedelta(days=5), 'max_marks': 50.00}
        )
        ExamResult.unscoped.get_or_create(school=school_b, exam=exam_b, student=student_b, subject=subject_b, defaults={'marks_obtained': 44.00})

        self.stdout.write(self.style.SUCCESS('\nDemo data seeded successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 55))
        self.stdout.write(self.style.SUCCESS('DEMO CREDENTIALS'))
        self.stdout.write(self.style.SUCCESS('=' * 55))
        self.stdout.write('  Platform Admin    | admin@schoolhub.com     | admin123456')
        self.stdout.write('  School Admin (GW) | admin@greenwood.edu     | greenwood123')
        self.stdout.write('  Teacher (GW)      | james.w@greenwood.edu   | teacher123')
        self.stdout.write('  Accountant (GW)   | mark.a@greenwood.edu    | account123')
        self.stdout.write('  Librarian (GW)    | lib.a@greenwood.edu     | library123')
        self.stdout.write('  Staff (GW)        | staff.a@greenwood.edu   | staff123')
        self.stdout.write('  Parent (GW)       | parent.a@greenwood.edu  | parent123')
        self.stdout.write('  Student (GW)      | student.a@greenwood.edu | student123')
        self.stdout.write('  School Admin (SR) | admin@sunrise.edu       | sunrise123')
        self.stdout.write('  Student (SR)      | student.b@sunrise.edu   | student123')
