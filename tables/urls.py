from django.urls import path
from . import views

app_name = 'tables'

urlpatterns = [
    path('', views.table_map, name='table_map'),
    path('create/', views.TableCreateView.as_view(), name='table_create'),
    path('<int:pk>/edit/', views.TableUpdateView.as_view(), name='table_update'),
    path('<int:pk>/delete/', views.TableDeleteView.as_view(), name='table_delete'),
    path('<int:pk>/status/', views.update_table_status, name='update_status'),
    path('<int:pk>/qr/', views.generate_table_qr, name='generate_qr'),
    path('areas/create/', views.TableAreaCreateView.as_view(), name='area_create'),
    path('areas/<int:pk>/edit/', views.TableAreaUpdateView.as_view(), name='area_update'),
    path('reservations/', views.ReservationListView.as_view(), name='reservation_list'),
    path('reservations/create/', views.ReservationCreateView.as_view(), name='reservation_create'),
    path('reservations/<int:pk>/edit/', views.ReservationUpdateView.as_view(), name='reservation_update'),
]
