from django.urls import path

from . import views

urlpatterns = [
    # ex: /tomo/
    path('', views.index, name='index'),
    # ex: /tomo/taxa/
    path('taxa/', views.taxa, name='taxa'),
    #
    path('taxa/<slug:taxon_id>', views.taxa_id, name='taxa')
]