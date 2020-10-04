from django.urls import path

from . import views

app_name = 'custom_admin'

urlpatterns = [
    path('admin/add_experiment_from_csv/', views.add_experiment_from_csv, name='add_experiment_from_csv'),
    path('admin/add_experiment_from_csv1/', views.add_experiment_from_csv1, name='add_experiment_from_csv1'),
]
