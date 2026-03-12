from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.orders_dashboard, name='dashboard'),
    path('list/', views.OrderListView.as_view(), name='order_list'),
    path('create/', views.order_create, name='order_create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/status/', views.update_order_status, name='update_order_status'),
    path('<int:pk>/close/', views.close_order, name='close_order'),
    path('<int:order_pk>/add-item/', views.add_item_to_order, name='add_item'),
    path('<int:order_pk>/remove-item/<int:item_pk>/', views.remove_item_from_order, name='remove_item'),
    path('<int:order_pk>/update-item/<int:item_pk>/', views.update_item_quantity, name='update_item_quantity'),
    path('item/<int:item_pk>/status/', views.update_item_status, name='update_item_status'),
    path('kitchen/', views.kitchen_display, name='kitchen_display'),
    path('virtual/<uuid:token>/', views.virtual_waiter_menu, name='virtual_waiter_menu'),
    path('virtual/<uuid:token>/order/', views.virtual_waiter_order, name='virtual_waiter_order'),
]
