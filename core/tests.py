"""
Tests for tenant isolation, auth, account management, attendance, exams, fees, and access control.
"""
import datetime
from django.test import TestCase, Client
from django.urls import reverse
from django.db.utils import IntegrityError

from core.models import (
    School, User, Role, UserRole, Department,
    ClassRoom, Section, Subject, Student, Staff, Timetable,
    StudentAttendance, Exam, ExamResult, FeeStructure, Invoice
)
from core.managers import set_current_school, clear_current_school


class TenantIsolationTests(TestCase):
    """Test that tenant scoping correctly isolates data between schools."""

    def setUp(self):
        self.school_a = School.objects.create(name='Greenwood Academy', slug='greenwood', plan='premium')
        self.school_b = School.objects.create(name='Sunrise School', slug='sunrise', plan='basic')

        self.admin_a = User.objects.create_user(
            email='admin@greenwood.edu', password='testpass123',
            first_name='Admin', last_name='A', school=self.school_a, primary_role='school_admin'
        )
        self.admin_b = User.objects.create_user(
            email='admin@sunrise.edu', password='testpass123',
            first_name='Admin', last_name='B', school=self.school_b, primary_role='school_admin'
        )

        self.teacher_a = User.objects.create_user(
            email='teacher@greenwood.edu', password='testpass123',
            first_name='Teacher', last_name='A', school=self.school_a, primary_role='teacher'
        )
        self.teacher_b = User.objects.create_user(
            email='teacher@sunrise.edu', password='testpass123',
            first_name='Teacher', last_name='B', school=self.school_b, primary_role='teacher'
        )

        self.role_a = Role.unscoped.create(name='Coordinator', school=self.school_a)
        self.role_b = Role.unscoped.create(name='Coordinator', school=self.school_b)

        self.dept_a = Department.unscoped.create(name='Science', school=self.school_a)
        self.dept_b = Department.unscoped.create(name='Science', school=self.school_b)

    def tearDown(self):
        clear_current_school()

    def test_tenant_manager_filters_by_school(self):
        set_current_school(self.school_a)
        roles = Role.objects.all()
        self.assertEqual(roles.count(), 1)
        self.assertEqual(roles.first().school, self.school_a)

        set_current_school(self.school_b)
        roles = Role.objects.all()
        self.assertEqual(roles.count(), 1)
        self.assertEqual(roles.first().school, self.school_b)

    def test_unscoped_manager_returns_all(self):
        set_current_school(self.school_a)
        all_roles = Role.unscoped.all()
        self.assertEqual(all_roles.count(), 2)

    def test_chunk2_models_tenant_isolation(self):
        """Test tenant scoping across all Chunk 2 models (exams, attendance, fees)."""
        set_current_school(self.school_a)
        class_a = ClassRoom.objects.create(name='Grade 10', code='G10')
        sec_a = Section.objects.create(classroom=class_a, name='A')
        student_u_a = User.objects.create_user(email='st.a@greenwood.edu', password='pass', school=self.school_a, primary_role='student')
        student_a = Student.objects.create(user=student_u_a, section=sec_a, admission_number='GW1')
        exam_a = Exam.objects.create(section=sec_a, name='Midterm', date=datetime.date.today())
        fee_a = FeeStructure.objects.create(name='Tuition', amount=1000.00)
        inv_a = Invoice.objects.create(student=student_a, fee_structure=fee_a, amount_due=1000.00, due_date=datetime.date.today())

        set_current_school(self.school_b)
        class_b = ClassRoom.objects.create(name='Grade 11', code='G11')
        sec_b = Section.objects.create(classroom=class_b, name='B')
        student_u_b = User.objects.create_user(email='st.b@sunrise.edu', password='pass', school=self.school_b, primary_role='student')
        student_b = Student.objects.create(user=student_u_b, section=sec_b, admission_number='SR1')
        exam_b = Exam.objects.create(section=sec_b, name='Quiz', date=datetime.date.today())
        fee_b = FeeStructure.objects.create(name='Lab Fee', amount=200.00)
        inv_b = Invoice.objects.create(student=student_b, fee_structure=fee_b, amount_due=200.00, due_date=datetime.date.today())

        # Verify School A sees ONLY School A's records
        set_current_school(self.school_a)
        self.assertEqual(Exam.objects.count(), 1)
        self.assertEqual(Exam.objects.first().name, 'Midterm')
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(Invoice.objects.first().fee_structure.name, 'Tuition')

        # Verify School B sees ONLY School B's records
        set_current_school(self.school_b)
        self.assertEqual(Exam.objects.count(), 1)
        self.assertEqual(Exam.objects.first().name, 'Quiz')
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(Invoice.objects.first().fee_structure.name, 'Lab Fee')


class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(name='Test School', slug='test-school')
        self.school_admin = User.objects.create_user(
            email='admin@test.edu', password='testpass123',
            first_name='Test', last_name='Admin', school=self.school, primary_role='school_admin'
        )
        self.teacher = User.objects.create_user(
            email='teacher@test.edu', password='testpass123',
            first_name='Test', last_name='Teacher', school=self.school, primary_role='teacher'
        )

    def test_login_success(self):
        response = self.client.post(reverse('core:login'), {'email': 'admin@test.edu', 'password': 'testpass123'})
        self.assertEqual(response.status_code, 302)

    def test_logout(self):
        self.client.login(username='admin@test.edu', password='testpass123')
        response = self.client.get(reverse('core:logout'))
        self.assertRedirects(response, reverse('core:login'))


class Chunk2AccessControlTests(TestCase):
    """Test strict role-based access rules and URL protection."""

    def setUp(self):
        self.client = Client()
        self.school = School.objects.create(name='Access School', slug='access-school')

        self.admin = User.objects.create_user(email='admin@access.edu', password='password123', school=self.school, primary_role='school_admin')
        self.teacher = User.objects.create_user(email='teacher@access.edu', password='password123', school=self.school, primary_role='teacher')
        self.accountant = User.objects.create_user(email='acct@access.edu', password='password123', school=self.school, primary_role='accountant')
        self.student_u1 = User.objects.create_user(email='student1@access.edu', password='password123', school=self.school, primary_role='student')
        self.student_u2 = User.objects.create_user(email='student2@access.edu', password='password123', school=self.school, primary_role='student')

        set_current_school(self.school)
        self.classroom = ClassRoom.objects.create(name='Grade 10', code='G10')
        self.section = Section.objects.create(classroom=self.classroom, name='A')
        self.student1 = Student.objects.create(user=self.student_u1, section=self.section, admission_number='ACC01')
        self.student2 = Student.objects.create(user=self.student_u2, section=self.section, admission_number='ACC02')
        self.exam = Exam.objects.create(section=self.section, name='Test Exam', date=datetime.date.today())
        self.fee = FeeStructure.objects.create(name='Tuition', amount=500.00)
        self.invoice1 = Invoice.objects.create(student=self.student1, fee_structure=self.fee, amount_due=500.00, due_date=datetime.date.today())
        self.invoice2 = Invoice.objects.create(student=self.student2, fee_structure=self.fee, amount_due=500.00, due_date=datetime.date.today())
        clear_current_school()

    def test_teacher_cannot_access_finance_invoices(self):
        """Teacher must get 403 when attempting to access fee pages via URL."""
        self.client.login(username='teacher@access.edu', password='password123')
        response = self.client.get(reverse('core:invoice_list'))
        self.assertEqual(response.status_code, 403)

    def test_accountant_cannot_access_attendance_marking_or_grading(self):
        """Accountant must get 403 when attempting to access attendance marking or exam grading."""
        self.client.login(username='acct@access.edu', password='password123')

        res_att = self.client.get(reverse('core:attendance_mark'))
        self.assertEqual(res_att.status_code, 403)

        res_grade = self.client.get(reverse('core:exam_grade', args=[self.exam.id]))
        self.assertEqual(res_grade.status_code, 403)

    def test_accountant_can_access_invoices(self):
        """Accountant can view invoices list."""
        self.client.login(username='acct@access.edu', password='password123')
        response = self.client.get(reverse('core:invoice_list'))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access_other_student_attendance(self):
        """Student 1 attempting to view Student 2's attendance ID directly gets 404."""
        self.client.login(username='student1@access.edu', password='password123')
        response = self.client.get(reverse('core:attendance_history_student', args=[self.student2.id]))
        self.assertEqual(response.status_code, 404)

    def test_student_cannot_access_other_student_exam_results(self):
        """Student 1 attempting to view Student 2's exam results ID directly gets 404."""
        self.client.login(username='student1@access.edu', password='password123')
        response = self.client.get(reverse('core:exam_results_student', args=[self.student2.id]))
        self.assertEqual(response.status_code, 404)

    def test_student_cannot_access_other_student_invoices(self):
        """Student 1 attempting to view Student 2's invoices ID directly gets 404."""
        self.client.login(username='student1@access.edu', password='password123')
        response = self.client.get(reverse('core:my_invoices_student', args=[self.student2.id]))
        self.assertEqual(response.status_code, 404)

    def test_student_can_view_own_data(self):
        """Student 1 can view their own attendance, results, and invoices."""
        self.client.login(username='student1@access.edu', password='password123')

        res_att = self.client.get(reverse('core:attendance_history'))
        self.assertEqual(res_att.status_code, 200)

        res_exam = self.client.get(reverse('core:exam_results'))
        self.assertEqual(res_exam.status_code, 200)

        res_inv = self.client.get(reverse('core:my_invoices'))
        self.assertEqual(res_inv.status_code, 200)


class Chunk2AttendanceTests(TestCase):
    """Test attendance database constraints."""

    def setUp(self):
        self.school = School.objects.create(name='Att School', slug='att-school')
        set_current_school(self.school)
        self.classroom = ClassRoom.objects.create(name='Grade 10', code='G10')
        self.section = Section.objects.create(classroom=self.classroom, name='A')
        self.student_u = User.objects.create_user(email='st@att.edu', password='password', school=self.school, primary_role='student')
        self.student = Student.objects.create(user=self.student_u, section=self.section, admission_number='ATT01')

    def tearDown(self):
        clear_current_school()

    def test_attendance_duplicate_prevention_at_db_level(self):
        """Database constraint prevents duplicate attendance records for same student & date."""
        today = datetime.date.today()
        StudentAttendance.objects.create(student=self.student, section=self.section, date=today, status='present')

        with self.assertRaises(IntegrityError):
            StudentAttendance.objects.create(student=self.student, section=self.section, date=today, status='absent')


class PlatformAdminTests(TestCase):
    """Test Platform Superadmin management features, tenant control, and plan limits."""

    def setUp(self):
        self.superadmin = User.objects.create_superuser(
            email='platform@admin.com', password='password123'
        )
        self.school = School.objects.create(
            name='Test Academy', slug='test-academy', plan='free', is_active=True
        )
        self.school_admin = User.objects.create_user(
            email='admin@testacademy.edu', password='password123',
            school=self.school, primary_role='school_admin'
        )

    def test_superadmin_dashboard_access(self):
        """Platform Superadmin can view the platform overview dashboard."""
        self.client.login(username='platform@admin.com', password='password123')
        response = self.client.get(reverse('core:dashboard_superadmin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Academy')

    def test_school_create_with_initial_admin(self):
        """Platform Superadmin can create a new school and provision its admin."""
        self.client.login(username='platform@admin.com', password='password123')
        response = self.client.post(reverse('core:platform_school_create'), {
            'name': 'New Horizon School',
            'slug': 'new-horizon',
            'plan': 'basic',
            'currency': 'PKR',
            'is_active': True,
            'admin_email': 'admin@newhorizon.edu',
            'admin_first_name': 'Horizon',
            'admin_last_name': 'Admin',
            'admin_password': 'password123',
        })
        self.assertEqual(response.status_code, 302)
        new_school = School.objects.get(slug='new-horizon')
        self.assertEqual(new_school.name, 'New Horizon School')

        admin_user = User.objects.get(email='admin@newhorizon.edu')
        self.assertEqual(admin_user.school, new_school)
        self.assertEqual(admin_user.primary_role, 'school_admin')
        self.assertEqual(new_school.currency, 'PKR')

    def test_school_toggle_status_and_suspended_login_block(self):
        """Deactivating a school prevents users from logging in."""
        self.client.login(username='platform@admin.com', password='password123')
        toggle_res = self.client.post(reverse('core:platform_school_toggle_status', args=[self.school.id]))
        self.assertEqual(toggle_res.status_code, 302)

        self.school.refresh_from_db()
        self.assertFalse(self.school.is_active)

        # Attempt to log in as school admin of suspended school
        self.client.logout()
        login_res = self.client.post(reverse('core:login'), {
            'email': 'admin@testacademy.edu',
            'password': 'password123',
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertContains(login_res, 'Your school account has been deactivated')

    def test_impersonation_session_flow(self):
        """Superadmin can enter and exit impersonation mode for a school."""
        self.client.login(username='platform@admin.com', password='password123')
        
        # Enter impersonation
        imp_res = self.client.get(reverse('core:platform_school_impersonate', args=[self.school.id]))
        self.assertEqual(imp_res.status_code, 302)
        self.assertEqual(self.client.session.get('impersonated_school_id'), self.school.id)

        # Exit impersonation
        exit_res = self.client.get(reverse('core:platform_exit_impersonation'))
        self.assertEqual(exit_res.status_code, 302)
        self.assertNotIn('impersonated_school_id', self.client.session)

    def test_staff_limit_enforcement(self):
        """School on Free plan cannot exceed staff limit."""
        # Free plan limit is 5 staff
        for i in range(5):
            User.objects.create_user(
                email=f'staff{i}@testacademy.edu', password='password123',
                school=self.school, primary_role='teacher'
            )
        self.assertTrue(self.school.is_staff_limit_reached)

        # Attempt to create 6th staff member
        self.client.login(username='admin@testacademy.edu', password='password123')
        res = self.client.post(reverse('core:staff_create'), {
            'first_name': 'Extra', 'last_name': 'Staff',
            'email': 'extra@testacademy.edu', 'primary_role': 'teacher',
            'password': 'password123', 'password_confirm': 'password123',
        })
        self.assertEqual(res.status_code, 302)
        # Verify 6th staff was not created
        self.assertFalse(User.objects.filter(email='extra@testacademy.edu').exists())

