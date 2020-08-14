from django.urls import path

from . import views

# app_name = 'experiments_base'

urlpatterns = [
    path('', views.index, name='index'),
    path('taxons/', views.taxons, name='taxons'),
    path('taxon/search/', views.taxon_search, name='taxon_search'),
    path('taxons/<slug:taxon_id>/', views.taxons_id, name='taxons_id'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('experiments/', views.experiments, name='experiments'),
    # path('experiment/download/', views.experiment_download, name='experiment_download'),
    path('experiment/searchfile/<slug:experiment_id>/', views.search_file, name='search_file'),
    path('experiment/gettorrent/<slug:experiment_id>/<slug:torrent_index>/', views.get_torrent, name='get_torrent'),
    path('experiment/<slug:experiment_id>/', views.experiment, name='experiment'),
    path('find/metabolites/', views.find_by_metabolites, name='find_by_metabolites'),
    path('metabolite/<slug:metabolite_id>', views.metabolite, name='metabolite'),
]