from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('taxons/', views.taxons, name='taxons'),
    path('taxon/search/', views.taxon_parent_search, name='taxon_search'),
    path('taxon/new/', views.taxon_add, name='taxon_add'),
    path('taxon/rename/<slug:taxon_id>/', views.taxon_rename_id, name='taxon_rename_id'),
    path('taxon/rename/', views.taxon_rename, name='taxon_rename'),
    path('taxon/move/<slug:taxon_id>/', views.taxon_move_id, name='taxon_move_id'),
    path('taxon/move/', views.taxon_move, name='taxon_move'),
    path('taxon/delete/<slug:taxon_id>/', views.taxon_delete_id, name='taxon_delete_id'),
    path('taxon/delete/', views.taxon_delete, name='taxon_delete'),
    path('taxons/<slug:taxon_id>/', views.taxons_id, name='taxons_id'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('experiments/', views.experiments),
    path('experiment/<slug:experiment_id>/', views.experiment, name='experiment'),
]
