from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('taxa/', views.taxa, name='taxa'),
    path('taxa/search', views.taxa_parent_search, name='taxa_search'),
    path('taxa/new', views.taxa_add, name='taxa_add'),
    path('taxa/rename/<slug:taxon_id>', views.taxa_rename, name='taxa_rename'),
    path('taxa/move/<slug:taxon_id>', views.taxa_move, name='taxa_move'),
    path('taxa/delete/<slug:taxon_id>', views.taxa_delete, name='taxa_delete'),
    path('taxa/<slug:taxon_id>', views.taxa_id, name='taxa_id'),
    path('login/', views.login, name='login'),
    path('experiments/', views.experiments),
    path('experiment/<slug:experiment_id>', views.experiment, name='experiment'),
]
