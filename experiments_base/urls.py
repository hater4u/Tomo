from django.urls import path

from . import views

# app_name = 'experiments_base'

urlpatterns = [
    path('', views.index, name='index'),
    path('taxa/', views.taxa, name='taxons'),
    path('taxon/search/', views.taxon_search, name='taxon_search'),
    path('taxa/<slug:taxon_id>/', views.taxa_id, name='taxons_id'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('403/', views.page_403, name='page_403'),
    path('experiments/', views.experiments, name='experiments'),
    path('experiment/download/', views.experiment_download, name='experiment_download'),
    path('experiment/gettorrent/<slug:experiment_id>/<slug:torrent_index>/', views.get_torrent, name='get_torrent'),
    path('experiment/<slug:experiment_id>/', views.experiment, name='experiment'),
    path('find/metabolites/', views.find_by_metabolites, name='find_by_metabolites'),
    path('metabolite/<slug:metabolite_id>', views.metabolite, name='metabolite'),
    path('tissue/search/', views.tissue_search, name='tissue_search')
]
