from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_index, name='dashboard_index'),
    path('api/resumo/', views.resumo_dashboard, name='resumo_dashboard'),
]
