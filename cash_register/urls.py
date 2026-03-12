from django.urls import path
from . import views

app_name = 'cash_register'

urlpatterns = [
    path('', views.cash_register_dashboard, name='dashboard'),
    path('open/', views.open_session, name='open_session'),
    path('close/<int:pk>/', views.close_session, name='close_session'),
    path('movement/create/', views.CashMovementCreateView.as_view(), name='movement_create'),
    path('payment/<int:order_pk>/', views.process_payment, name='process_payment'),
    path('session/<int:pk>/report/', views.session_report, name='session_report'),
    path('registers/', views.CashRegisterListView.as_view(), name='register_list'),
    path('registers/create/', views.CashRegisterCreateView.as_view(), name='register_create'),
    path('registers/<int:pk>/edit/', views.CashRegisterUpdateView.as_view(), name='register_update'),
    path('daily-report/', views.daily_sales_report, name='daily_report'),
]
