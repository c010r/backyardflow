from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    path('', views.staff_dashboard, name='dashboard'),
    path('members/', views.StaffMemberListView.as_view(), name='member_list'),
    path('members/create/', views.staff_member_create, name='member_create'),
    path('members/<int:pk>/', views.StaffMemberDetailView.as_view(), name='member_detail'),
    path('members/<int:pk>/edit/', views.StaffMemberUpdateView.as_view(), name='member_update'),
    path('members/<int:member_pk>/shifts/', views.WorkShiftListView.as_view(), name='shift_list'),
    path('members/<int:member_pk>/shifts/create/', views.WorkShiftCreateView.as_view(), name='shift_create'),
    path('members/<int:member_pk>/settlement/', views.generate_settlement, name='generate_settlement'),
    path('shifts/create/', views.WorkShiftCreateView.as_view(), name='shift_create_general'),
    path('advances/create/', views.SalaryAdvanceCreateView.as_view(), name='advance_create'),
    path('settlements/', views.SalarySettlementListView.as_view(), name='settlement_list'),
    path('settlements/<int:pk>/', views.SalarySettlementDetailView.as_view(), name='settlement_detail'),
    path('settlements/<int:pk>/approve/', views.approve_settlement, name='settlement_approve'),
    path('settlements/<int:pk>/paid/', views.mark_settlement_paid, name='settlement_paid'),
    path('schedule/', views.work_schedule, name='work_schedule'),
]
