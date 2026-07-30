"""
URL patterns for the core app.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard_redirect, name='dashboard'),
    path('dashboard/super-admin/', views.dashboard_superadmin, name='dashboard_superadmin'),
    path('dashboard/school-admin/', views.dashboard_school_admin, name='dashboard_school_admin'),
    path('dashboard/teacher/', views.dashboard_teacher, name='dashboard_teacher'),
    path('dashboard/staff/', views.dashboard_staff, name='dashboard_staff'),
    path('dashboard/accountant/', views.dashboard_accountant, name='dashboard_accountant'),
    path('dashboard/librarian/', views.dashboard_librarian, name='dashboard_librarian'),
    path('dashboard/student/', views.dashboard_student, name='dashboard_student'),
    path('dashboard/parent/', views.dashboard_parent, name='dashboard_parent'),

    # Student Portal (Timetable / Subjects / Learning Materials)
    path('student/timetable/', views.student_timetable, name='student_timetable'),
    path('student/subjects/', views.student_subjects, name='student_subjects'),
    path('student/subjects/<int:subject_id>/', views.student_subject_detail, name='student_subject_detail'),

    # Platform Management (Superadmin)
    path('platform/schools/create/', views.platform_school_create, name='platform_school_create'),
    path('platform/schools/<int:school_id>/edit/', views.platform_school_edit, name='platform_school_edit'),
    path('platform/schools/<int:school_id>/toggle-status/', views.platform_school_toggle_status, name='platform_school_toggle_status'),
    path('platform/schools/<int:school_id>/change-plan/', views.platform_school_change_plan, name='platform_school_change_plan'),
    path('platform/schools/<int:school_id>/impersonate/', views.platform_school_impersonate, name='platform_school_impersonate'),
    path('platform/exit-impersonation/', views.platform_exit_impersonation, name='platform_exit_impersonation'),
    path('platform/users/', views.platform_user_list, name='platform_user_list'),
    path('platform/users/<int:user_id>/toggle-active/', views.platform_user_toggle_active, name='platform_user_toggle_active'),
    path('platform/users/<int:user_id>/reset-password/', views.platform_user_reset_password, name='platform_user_reset_password'),
    # Subscription Plan Management
    path('platform/plans/', views.platform_plan_list, name='platform_plan_list'),
    path('platform/plans/create/', views.platform_plan_create, name='platform_plan_create'),
    path('platform/plans/<int:plan_id>/edit/', views.platform_plan_edit, name='platform_plan_edit'),
    path('platform/plans/<int:plan_id>/delete/', views.platform_plan_delete, name='platform_plan_delete'),

    # Staff Management
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/create/', views.staff_create, name='staff_create'),
    path('staff/<int:user_id>/roles/', views.staff_roles, name='staff_roles'),

    # Role Management
    path('roles/', views.role_list, name='role_list'),
    path('roles/create/', views.role_create, name='role_create'),

    # Academics — Classes
    path('academics/classes/', views.classroom_list, name='classroom_list'),
    path('academics/classes/create/', views.classroom_create, name='classroom_create'),
    path('academics/classes/<int:classroom_id>/edit/', views.classroom_edit, name='classroom_edit'),
    path('academics/classes/<int:classroom_id>/delete/', views.classroom_delete, name='classroom_delete'),

    # Academics — Sections
    path('academics/sections/', views.section_list, name='section_list'),
    path('academics/sections/create/', views.section_create, name='section_create'),
    path('academics/sections/<int:section_id>/edit/', views.section_edit, name='section_edit'),
    path('academics/sections/<int:section_id>/delete/', views.section_delete, name='section_delete'),

    # Academics — Subjects
    path('academics/subjects/', views.subject_list, name='subject_list'),
    path('academics/subjects/create/', views.subject_create, name='subject_create'),
    path('academics/subjects/<int:subject_id>/edit/', views.subject_edit, name='subject_edit'),
    path('academics/subjects/<int:subject_id>/delete/', views.subject_delete, name='subject_delete'),

    # Academics — Syllabus
    path('academics/syllabus/', views.syllabus_list, name='syllabus_list'),
    path('academics/syllabus/create/', views.syllabus_create, name='syllabus_create'),
    path('academics/syllabus/<int:syllabus_id>/', views.syllabus_detail, name='syllabus_detail'),
    path('academics/syllabus/<int:syllabus_id>/edit/', views.syllabus_edit, name='syllabus_edit'),
    path('academics/syllabus/<int:syllabus_id>/delete/', views.syllabus_delete, name='syllabus_delete'),
    path('academics/syllabus/units/<int:unit_id>/delete/', views.syllabus_unit_delete, name='syllabus_unit_delete'),

    # Academics — Timetable
    path('academics/timetable/', views.timetable_list, name='timetable_list'),
    path('academics/timetable/create/', views.timetable_create, name='timetable_create'),
    path('academics/timetable/<int:slot_id>/edit/', views.timetable_edit, name='timetable_edit'),
    path('academics/timetable/<int:slot_id>/delete/', views.timetable_delete, name='timetable_delete'),

    # Students
    path('students/', views.student_list, name='student_list'),
    path('students/create/', views.student_create, name='student_create'),
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),
    path('students/<int:student_id>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:student_id>/toggle-active/', views.student_toggle_active, name='student_toggle_active'),
    path('students/<int:student_id>/delete/', views.student_delete, name='student_delete'),

    # School Preferences
    path('preferences/', views.school_preferences, name='school_preferences'),

    # Teacher Portal
    path('teacher/classes/', views.teacher_my_classes, name='teacher_my_classes'),
    path('teacher/timetable/', views.teacher_timetable, name='teacher_timetable'),
    path('teacher/attendance/history/', views.teacher_attendance_history, name='teacher_attendance_history'),
    path('teacher/students/', views.teacher_students, name='teacher_students'),
    path('teacher/students/<int:student_id>/', views.teacher_student_detail, name='teacher_student_detail'),
    path('teacher/syllabus/', views.teacher_syllabus_list, name='teacher_syllabus_list'),
    path('teacher/syllabus/create/', views.teacher_syllabus_create, name='teacher_syllabus_create'),
    path('teacher/syllabus/<int:syllabus_id>/', views.teacher_syllabus_detail, name='teacher_syllabus_detail'),
    path('teacher/syllabus/<int:syllabus_id>/edit/', views.teacher_syllabus_edit, name='teacher_syllabus_edit'),
    path('teacher/syllabus/units/<int:unit_id>/delete/', views.teacher_syllabus_unit_delete, name='teacher_syllabus_unit_delete'),
    
    # Teacher Homework
    path('teacher/homework/', views.teacher_homework_list, name='teacher_homework_list'),
    path('teacher/homework/create/', views.teacher_homework_create, name='teacher_homework_create'),
    path('teacher/homework/<int:pk>/edit/', views.teacher_homework_edit, name='teacher_homework_edit'),
    path('teacher/homework/<int:pk>/delete/', views.teacher_homework_delete, name='teacher_homework_delete'),

    path('profile/', views.profile_view, name='profile'),

    # Attendance
    path('attendance/mark/', views.attendance_mark, name='attendance_mark'),
    path('attendance/history/', views.attendance_history, name='attendance_history'),
    path('attendance/history/<int:student_id>/', views.attendance_history, name='attendance_history_student'),

    # Student Homework
    path('homework/', views.student_homework_list, name='student_homework_list'),
    path('homework/student/<int:student_id>/', views.student_homework_list, name='student_homework_list_student'),
    path('homework/<int:pk>/', views.student_homework_detail, name='student_homework_detail'),
    path('homework/<int:pk>/student/<int:student_id>/', views.student_homework_detail, name='student_homework_detail_student'),

    # Exams & Grading
    path('exams/', views.exam_list, name='exam_list'),
    path('exams/create/', views.exam_create, name='exam_create'),
    path('exams/<int:exam_id>/grade/', views.exam_grade, name='exam_grade'),
    path('exams/results/', views.exam_results_view, name='exam_results'),
    path('exams/results/<int:student_id>/', views.exam_results_view, name='exam_results_student'),

    # Fees & Invoices
    path('finance/invoices/', views.invoice_list, name='invoice_list'),
    path('finance/invoices/create/', views.invoice_create, name='invoice_create'),
    path('finance/invoices/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('finance/invoices/<int:invoice_id>/payment/', views.record_payment, name='record_payment'),
    path('finance/invoices/bulk/', views.bulk_invoice_create, name='bulk_invoice_create'),
    path('finance/my-invoices/', views.my_invoices, name='my_invoices'),
    path('finance/my-invoices/<int:student_id>/', views.my_invoices, name='my_invoices_student'),

    # Fee Structures
    path('finance/fee-structures/', views.fee_structure_list, name='fee_structure_list'),
    path('finance/fee-structures/create/', views.fee_structure_create, name='fee_structure_create'),
    path('finance/fee-structures/<int:pk>/edit/', views.fee_structure_edit, name='fee_structure_edit'),
    path('finance/fee-structures/<int:pk>/delete/', views.fee_structure_delete, name='fee_structure_delete'),

    # Finance Report
    path('finance/report/', views.finance_report, name='finance_report'),

    # Expenses
    path('finance/expenses/', views.expense_list, name='expense_list'),
    path('finance/expenses/create/', views.expense_create, name='expense_create'),
    path('finance/expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('finance/expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),

    # Salaries
    path('finance/salaries/', views.salary_list, name='salary_list'),
    path('finance/salaries/create/', views.salary_create, name='salary_create'),
    path('finance/salaries/<int:pk>/edit/', views.salary_edit, name='salary_edit'),
    path('finance/salaries/<int:pk>/delete/', views.salary_delete, name='salary_delete'),

    # Announcements
    path('announcements/', views.announcement_list, name='announcement_list'),
    path('announcements/create/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/', views.announcement_detail, name='announcement_detail'),
    path('announcements/<int:pk>/edit/', views.announcement_edit, name='announcement_edit'),
    path('announcements/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),
    path('announcements/<int:pk>/mark-read/', views.announcement_mark_read, name='announcement_mark_read'),
]
