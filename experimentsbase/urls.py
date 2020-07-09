from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('taxa/', views.taxa, name='taxa'),
    path('taxa/<slug:taxon_id>', views.taxa_id, name='taxa'),
    path('experiments/', views.experiments),

]