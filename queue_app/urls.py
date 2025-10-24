from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('generate-token/', views.generate_token, name='generate_token'),
    path('status/<int:token_number>/', views.queue_status, name='queue_status'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('serve-next/', views.serve_next, name='serve_next'),
    path('reset-queue/', views.reset_queue, name='reset_queue'),
    path('create-counter/', views.create_counter, name='create_counter'),
    path('mark-served/<int:token_number>/', views.mark_served, name='mark_served'),
]
