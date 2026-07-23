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

    # Attendance
    path('attendance/mark/', views.attendance_mark, name='attendance_mark'),
    path('attendance/history/', views.attendance_history, name='attendance_history'),
    path('attendance/history/<int:student_id>/', views.attendance_history, name='attendance_history_student'),

    # Exams & Grading
    path('exams/', views.exam_list, name='exam_list'),
    path('exams/create/', views.exam_create, name='exam_create'),
    path('exams/<int:exam_id>/grade/', views.exam_grade, name='exam_grade'),
    path('exams/results/', views.exam_results_view, name='exam_results'),
    path('exams/results/<int:student_id>/', views.exam_results_view, name='exam_results_student'),

    # Fees & Invoices
    path('finance/invoices/', views.invoice_list, name='invoice_list'),
    path('finance/invoices/create/', views.invoice_create, name='invoice_create'),
    path('finance/my-invoices/', views.my_invoices, name='my_invoices'),
    path('finance/my-invoices/<int:student_id>/', views.my_invoices, name='my_invoices_student'),
]
