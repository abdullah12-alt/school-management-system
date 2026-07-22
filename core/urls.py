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
