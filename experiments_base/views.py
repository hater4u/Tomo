from django.shortcuts import render, redirect
from django.contrib import auth
from django.template.context_processors import csrf
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import ObjectDoesNotExist

from tomo.settings import API_URL, SHARED_FILES_DIR, TORRENT_DIR, LOGGING
from .models import Taxon, Experiment, Prob, ProbMetabolite, Metabolite, MetaboliteName, InterfaceName

import requests
import os
import base64
import logging
import json
import zipfile
import random
import string
import shutil

logging.config.dictConfig(LOGGING)
experiments_base_logger = logging.getLogger('django')
# experiments_base_logger_admin = logging.getLogger('django.request')


# TODO: write normal index
def index(request):
    return redirect('taxons')


def login(request):
    args = {}
    args.update(csrf(request))

    if request.POST:
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        user = auth.authenticate(username=username, password=password)

        if user is not None:
            auth.login(request, user)
            return redirect('taxons')

        else:
            args['login_error'] = 'User is not found'
            return render(request, 'reg/login.html', args)
    else:
        return render(request, 'reg/login.html', args)


def logout(request):
    auth.logout(request)
    return redirect('index')


def check_auth_user(request, args):

    args['interface_taxons_name'] = InterfaceName.objects.get(search_name='taxons_name').value
    args['interface_experiments_name'] = InterfaceName.objects.get(search_name='experiments_name').value
    args['interface_find_by_metabolites_name'] = InterfaceName.objects.get(search_name='find_by_metabolites_name').value

    args['interface_taxons_page_root_taxon'] = InterfaceName.objects.get(search_name='root_taxon').value
    args['interface_taxons_page_popular_taxons'] = InterfaceName.objects.get(search_name='popular_taxons').value
    args['interface_taxons_page_children'] = InterfaceName.objects.get(search_name='children').value

    args['interface_experiments_page_title'] = InterfaceName.objects.get(search_name='experiments_title').value
    args['interface_experiments_page_hint_experiment_name'] = InterfaceName.objects.get(
        search_name='experiments_hint_experiment_name').value
    args['interface_experiments_page_hint_taxon_name'] = InterfaceName.objects.get(
        search_name='experiments_hint_taxon_name').value
    args['interface_experiments_page_hint_age'] = InterfaceName.objects.get(
        search_name='experiments_hint_age').value
    args['interface_experiments_page_hint_weight'] = InterfaceName.objects.get(
        search_name='experiments_hint_weight').value
    args['interface_experiments_page_hint_length'] = InterfaceName.objects.get(
        search_name='experiments_hint_length').value
    args['interface_experiments_page_hint_environmental_factors'] = InterfaceName.objects.get(
        search_name='experiments_hint_environmental_factors').value
    args['interface_experiments_page_hint_diseases'] = InterfaceName.objects.get(
        search_name='experiments_hint_diseases').value
    args['interface_experiments_page_hint_withdraw_place'] = InterfaceName.objects.get(
        search_name='experiments_hint_withdraw_place').value
    args['interface_experiments_page_hint_withdraw_date'] = InterfaceName.objects.get(
        search_name='experiments_hint_withdraw_date').value
    args['interface_experiments_page_hint_hours_post_mortem'] = InterfaceName.objects.get(
        search_name='experiments_hint_hours_post_mortem').value
    args['interface_experiments_page_hint_temperature'] = InterfaceName.objects.get(
        search_name='experiments_hint_temperature').value
    args['interface_experiments_page_hint_comments'] = InterfaceName.objects.get(
        search_name='experiments_hint_comments').value

    args['interface_find_metabolites_page_title'] = InterfaceName.objects.get(
        search_name='metabolites_search_title').value
    args['interface_find_metabolites_page_field'] = InterfaceName.objects.get(
        search_name='metabolites_search_field').value
    args['interface_find_metabolites_page_hint'] = InterfaceName.objects.get(
        search_name='metabolites_search_hint').value

    if request.user.is_authenticated:
        args['nickname'] = request.user.get_username()
        args['authenticated'] = True
        if request.user.is_staff:
            args['user_auth'] = True
    return args


def get_taxon_path(taxon_id):
    hierarchy = list()
    if taxon_id == '':
        return []

    try:
        taxon = Taxon.objects.get(pk=taxon_id)
        hierarchy.append({'id': taxon.pk, 'name': taxon.taxon_name})

        parent_taxon = taxon.parent_id
        while parent_taxon:
            hierarchy.append({'id': parent_taxon.pk, 'name': parent_taxon.taxon_name})
            parent_taxon = parent_taxon.parent_id
        return hierarchy
    except ObjectDoesNotExist:
        experiments_base_logger.warning('hierarchy found error, maybe it is root')
        return []
    except Exception:
        experiments_base_logger.error('get_taxon_path unknown error')
        return []


# def get_taxon_children(taxon_id):
#     try:
#         return requests.get(API_URL + '/taxa/byParent', params={'parentId': taxon_id}).json()['value']
#     except Exception:
#         experiments_base_logger.error('children found error, maybe problems with API')
#         return []


def get_sub_taxons(taxon_id):
    all_sub_taxons = []
    sub_taxons = Taxon.objects.filter(parent_id=taxon_id)
    all_sub_taxons += sub_taxons

    for el in sub_taxons:
        all_sub_taxons += get_sub_taxons(el.pk)

    return all_sub_taxons


def get_taxon_and_sub_taxon_experiments(taxon_id):
    try:
        all_sub_taxons = [Taxon.objects.get(pk=taxon_id)]
    except ObjectDoesNotExist:
        experiments_base_logger.error('get_taxon_and_sub_taxon_experiments error(ObjectDoesNotExist)')
        return []
    all_sub_taxons += get_sub_taxons(taxon_id)

    all_experiments = []
    for el in all_sub_taxons:
        all_experiments += Experiment.objects.filter(taxon_id=el.pk)

    return all_experiments


def get_taxon_children(taxon_id):
    children = Taxon.objects.filter(parent_id=taxon_id)

    if children.count():
        children_list = []
        for ch in children:
            children_list.append({'text': ch.taxon_name,
                                  'href': '/taxons/' + str(ch.pk),
                                  'nodes': get_taxon_children(ch.pk)})

        return children_list
    else:
        return []


def taxons_id(request, taxon_id):
    args = dict()
    args.update(csrf(request))
    args = check_auth_user(request, args)

    args['taxon_id'] = taxon_id

    hierarchy = get_taxon_path(taxon_id)
    hierarchy.reverse()
    args['hierarchy'] = hierarchy

    if taxon_id == '':
        args['index_taxons'] = True
        experiments_dict = []
        args['popular_taxons'] = Taxon.objects.filter(view_in_popular=True)
        args['taxon_tree'] = json.dumps(get_taxon_children(None))
    else:
        args['children'] = Taxon.objects.filter(parent_id=taxon_id)
        experiments_dict = get_taxon_and_sub_taxon_experiments(taxon_id)

    args['experiments'] = experiments_dict

    return render(request, 'taxons.html', args)


def taxons(request):
    return taxons_id(request, '')


def taxon_search(request):
    if request.POST:
        search_word = request.POST['taxonName']
        try:
            founded_taxons = Taxon.objects.filter(taxon_name__contains=search_word)
            taxon_names = []
            for el in founded_taxons:
                taxon_names.append(el.taxon_name)
            return JsonResponse({'value': taxon_names})
        except Exception as e:
            experiments_base_logger.error('Taxon search error:' + str(e))
            return JsonResponse({'value': []})
    else:
        return redirect('taxons')


def search_file(request, experiment_id):
    if request.user.is_authenticated:
        if request.user.is_staff:
            if request.method == 'POST':

                try:
                    path = request.POST.get('path', False)
                except Exception as e:
                    experiments_base_logger.error('Incorrect path: ' + str(e))
                    return JsonResponse({'error': 'Incorrect path'})

                if path.find('.') != -1:
                    return JsonResponse({'error': 'Path contains forbidden characters'})

                try:
                    path = os.path.abspath(os.getcwd() + "/" + SHARED_FILES_DIR + '/' + path)
                    files_and_dirs = os.listdir(path)
                    dirs = []
                    files = []
                    for el in files_and_dirs:
                        if os.path.isfile(path + '/' + el):
                            files.append(el)
                            continue
                        if os.path.isdir(path + '/' + el):
                            dirs.append(el)
                            continue

                    return JsonResponse({'files': files, 'dirs': dirs})

                except FileNotFoundError as e:
                    experiments_base_logger.error('File not found: ' + str(e))
                    return JsonResponse({'error': 'File is not found'})

            else:
                return redirect('index')
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def experiment(request, experiment_id):
    args = dict()
    args = check_auth_user(request, args)
    try:
        args['experiment'] = Experiment.objects.get(pk=experiment_id)
        probs = Prob.objects.filter(experiment_id=experiment_id).order_by('pk')
        if probs.count() == 0:
            return render(request, 'experiment.html', args)

        args['probs'] = probs

        max_metabolites_num = 0
        max_metabolites_prob = None
        all_metabolites = []
        for prob in probs:
            pms = ProbMetabolite.objects.filter(prob_id=prob.pk)

            if pms.count() > max_metabolites_num:
                max_metabolites_prob = prob
                max_metabolites_num = pms.count()

            all_metabolites.append(pms)

        if max_metabolites_prob:
            meta_id_in_num = dict()
            prob_metabolites = ProbMetabolite.objects.filter(prob_id=max_metabolites_prob.pk). \
                order_by('metabolite_id__metabolite_name')

            for counter, m in enumerate(prob_metabolites):
                meta_id_in_num[m.metabolite_id] = counter

            dict_of_metabolites = {}
            for counter, m in enumerate(prob_metabolites):
                dict_of_metabolites[counter] = {'name': m.metabolite_id.metabolite_name,
                                                'pub_chem_cid': m.metabolite_id.pub_chem_cid,
                                                'concentrations': {x: '' for x in range(max_metabolites_num)}}

            for counter, pms in enumerate(all_metabolites):
                for m in pms:
                    dict_of_metabolites[meta_id_in_num[m.metabolite_id]]['concentrations'][counter] = m.concentration

            args['metabolites'] = dict_of_metabolites
        else:
            args['metabolites'] = []

    except ObjectDoesNotExist as e:
        args['error'] = 'Experiment not found'
        experiments_base_logger.error('Experiment error(ObjectDoesNotExist):' + str(e))
    except Exception as e:
        experiments_base_logger.error('Experiment error:' + str(e))
        args = {}
    return render(request, 'experiment.html', args)


def get_torrent(request, experiment_id, torrent_index):
    args = dict()
    args = check_auth_user(request, args)
    args.update(csrf(request))

    try:
        req = requests.get(API_URL + '/experiments', params={'id': experiment_id})
        torrent_path = req.json()['value']['fileInfos'][int(torrent_index)]['torrentFilePath']

        req = requests.get(API_URL + '/experiments/getTorrent', params={'torrentPath': torrent_path})
        torrent_file = base64.b64decode(req.json()['value'])

        response = HttpResponse(torrent_file)

        response['status_code'] = 200
        response['Content-Type'] = 'application/x-bittorrent'
        response['Content-Length'] = str(len(torrent_file))
        response['Content-Disposition'] = "attachment; filename=" + os.path.basename(torrent_path)

        return response

    except Exception as e:
        experiments_base_logger.error("getting torrent error: " + str(e))
        return redirect('index')


def experiments_search(search_dict):
    try:
        founded_experiments_qs = Experiment.objects.filter(**search_dict)

        return founded_experiments_qs
    except Exception as e:
        experiments_base_logger.error('experiments found error: ' + str(e))
        return []


# TODO refactor search experiments
def experiments(request):
    args = dict()
    args = check_auth_user(request, args)
    args.update(csrf(request))
    if request.POST:
        search_dict = dict()

        args['filled_fields'] = dict()
        for key, value in request.POST.items():
            if request.POST[key] and request.POST[key] != '':
                args['filled_fields'][key] = value

        if not request.POST['experimentName'] == '':
            search_dict['experiment_name__contains'] = request.POST['experimentName']

        args['error'] = dict()
        if not request.POST['taxonSearchName'] == '':
            search_dict['taxon_id__taxon_name'] = request.POST['taxonSearchName']

        # Ways of life
        search_dict['way_of_life__in'] = []
        if request.POST.get('diurnalWayCheckbox', False):
            search_dict['way_of_life__in'].append(0)

        if request.POST.get('nocturnalWayCheckbox', False):
            search_dict['way_of_life__in'].append(1)

        if request.POST.get('twilightWayCheckbox', False):
            search_dict['way_of_life__in'].append(2)

        if request.POST.get('otherWayCheckbox', False):
            search_dict['way_of_life__in'].append(3)

        # TODO remove kostyls
        if not search_dict['way_of_life__in']:
            search_dict.pop('way_of_life__in')

        # Habitat
        search_dict['habitat__in'] = []
        if request.POST.get('wildHabitatCheckbox', False):
            search_dict['habitat__in'].append(0)

        if request.POST.get('laboratoryHabitatCheckbox', False):
            search_dict['habitat__in'].append(1)

        if request.POST.get('farmHabitatCheckbox', False):
            search_dict['habitat__in'].append(2)

        if request.POST.get('otherHabitatCheckbox', False):
            search_dict['habitat__in'].append(3)

        # TODO remove kostyls
        if not search_dict['habitat__in']:
            search_dict.pop('habitat__in')

        # Gender
        search_dict['prob__gender__in'] = []
        if request.POST.get('maleGenderCheckbox', False):
            search_dict['prob__gender__in'].append(0)

        if request.POST.get('femaleGenderCheckbox', False):
            search_dict['prob__gender__in'].append(1)

        if request.POST.get('otherGenderCheckbox', False):
            search_dict['prob__gender__in'].append(2)

        # TODO remove kostyls
        if not search_dict['prob__gender__in']:
            search_dict.pop('prob__gender__in')

        # Age
        if not request.POST['ageFrom'] == '':
            # search_dict['month_age__gte'] = 0
            # else:
            search_dict['prob__month_age__gte'] = request.POST['ageFrom']

        if not request.POST['ageTo'] == '':
            search_dict['prob__month_age__lte'] = request.POST['ageTo']

        # Weight
        if not request.POST['weightFrom'] == '':
            search_dict['prob__weight__gte'] = request.POST['weightFrom']

        if not request.POST['weightTo'] == '':
            search_dict['prob__weight__lte'] = request.POST['weightTo']

        # Length
        if not request.POST['lengthFrom'] == '':
            search_dict['prob__length__gte'] = request.POST['lengthFrom']

        if not request.POST['lengthTo'] == '':
            search_dict['prob__length__lte'] = request.POST['lengthTo']

        # Environmental factors
        if not request.POST['environmentalFactors'] == '':
            search_dict['environmental_factors__in'] = [request.POST['environmentalFactors']]

        # Diseases
        if not request.POST['diseases'] == '':
            search_dict['diseases__in'] = [request.POST['diseases']]

        # Withdraw place
        if not request.POST['withdrawPlace'] == '':
            search_dict['withdraw_place'] = request.POST['withdrawPlace']

        # Withdraw date
        if request.POST['withdrawDateFrom'] != '':
            #     search_dict['withdrawDateFrom'] = 'null'
            # else:
            search_dict['withdraw_date__gte'] = request.POST['withdrawDateFrom'] + ' 00:00:00'

        if request.POST['withdrawDateTo'] != '':
            #     search_dict['withdrawDateTo'] = 'null'
            # else:
            search_dict['withdraw_date__lte'] = request.POST['withdrawDateTo'] + ' 00:00:00'

        # Seconds post mortem
        if not request.POST['hoursPostMortemFrom'] == '':
            search_dict['prob__hours_post_mortem__gte'] = request.POST['secondsPostMortemFrom']

        if not request.POST['hoursPostMortemTo'] == '':
            search_dict['prob__hours_post_mortem__lte'] = request.POST['secondsPostMortemTo']

        # Temperature
        if not request.POST['temperatureFrom'] == '':
            search_dict['prob__temperature__gte'] = request.POST['temperatureFrom']

        if not request.POST['temperatureTo'] == '':
            search_dict['prob__temperature__lte'] = request.POST['temperatureTo']

        # Comments
        if not request.POST['comments'] == '':
            search_dict['comments'] = [request.POST['comments']]

        try:
            if not args['error']:
                args['experiments'] = experiments_search(search_dict)
            else:
                args['experiments'] = {}
        except Exception as e:
            experiments_base_logger.error('Search error:' + str(e))
            args = {}

    return render(request, 'experiments.html', args)


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))


def create_random_str(size):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))


def archive_and_get_response(folder):
    path_to_archive = folder + '.zip'

    zipf = zipfile.ZipFile(path_to_archive, 'w', zipfile.ZIP_DEFLATED)
    zipdir(folder, zipf)
    zipf.close()

    archive = open(path_to_archive, 'rb').read()
    response = HttpResponse(archive)

    response['status_code'] = 200
    response['Content-Type'] = 'application/zip'
    response['Content-Length'] = os.path.getsize(path_to_archive)
    response['Content-Disposition'] = "attachment; filename={}".format(os.path.basename(path_to_archive))

    os.remove(path_to_archive)
    shutil.rmtree(folder)

    return response


def experiment_download(request):

    if request.POST:
        try:
            data = json.loads(request.POST['experiments'])
        except KeyError as e:
            experiments_base_logger.warning('Probs downloading error:' + str(e))
            return JsonResponse({'error': 'Invalid field'})

        if data.get('probs', False):
            prob_ids = [prob['id'] for prob in data['probs']]

            torrents = []
            try:
                for pr in prob_ids:
                    prob = Prob.objects.get(pk=pr)
                    torrents.append({'name': prob.prob_name, 'path': TORRENT_DIR + str(prob.prob_torrent_file)})
            except ObjectDoesNotExist:
                return JsonResponse({'error': 'Invalid prob id'})

            try:
                folder = '/tmp/probs_' + create_random_str(16) + '/'
                os.mkdir(folder)

                for t in torrents:
                    shutil.copy(t['path'], folder + t['name'] + '_' + os.path.basename(t['path']))

                return archive_and_get_response(folder[:-1])

            except Exception as e:
                experiments_base_logger.error('Probs downloading error:' + str(e))
                return JsonResponse({'error': 'Cant create archive'})
        else:
            if data.get('experiments', False):
                experiment_ids = [exp['id'] for exp in data['experiments']]

                try:
                    folder = '/tmp/experiments_' + create_random_str(16) + '/'
                    os.mkdir(folder)

                    try:
                        for exp_id in experiment_ids:
                            exp = Experiment.objects.get(pk=exp_id)
                            probs = Prob.objects.filter(experiment_id=exp_id)

                            if probs.count() > 0:
                                exp_folder = folder + exp.experiment_name + '_' + create_random_str(4) + '/'
                                os.mkdir(exp_folder)

                                for pr in probs:
                                    tp = TORRENT_DIR + str(pr.prob_torrent_file)
                                    shutil.copy(tp, exp_folder + pr.prob_name + '_' + os.path.basename(tp))

                    except ObjectDoesNotExist:
                        shutil.rmtree(folder)
                        return JsonResponse({'error': 'Invalid experiment id'})

                    return archive_and_get_response(folder[:-1])

                except Exception as e:
                    experiments_base_logger.error('Experiments downloading error:' + str(e))
                    return JsonResponse({'error': 'Cant create archive'})
            else:
                return JsonResponse({'error': 'Invalid data'})

    return render(request, '', {})


def find_by_metabolites(request):
    args = dict()
    args = check_auth_user(request, args)
    args.update(csrf(request))

    args['metabolites'] = Metabolite.objects.all().order_by('metabolite_name')

    if request.POST:
        metabolite_names = request.POST.get('metaboliteNames', False)
        if metabolite_names:
            metabolite_names = metabolite_names.split(' AND ')
            meta_length = len(metabolite_names)

            found_names = set()
            not_found_names = []
            for el in metabolite_names:
                try:
                    query = MetaboliteName.objects.get(metabolite_synonym=el)
                    found_names.add(query.metabolite_id)
                except ObjectDoesNotExist:
                    not_found_names.append(el)

            if len(not_found_names) > 0:
                args['error'] = 'Not found metabolites: ' + ', '.join(not_found_names)
            else:
                all_probs_with_metabolites = ProbMetabolite.objects.filter(metabolite_id__in=found_names)

                prob_ids = set()
                for el in all_probs_with_metabolites:
                    prob_ids.add(el.prob_id)

                exp_ids = set()
                for el in prob_ids:
                    query = all_probs_with_metabolites.filter(prob_id=el.pk)
                    if query.count() == meta_length:
                        exp_ids.add(el.experiment_id)

                if len(exp_ids) == 0:
                    args['error'] = 'Experiments with this conditions not found'
                else:
                    args['experiments'] = exp_ids

    return render(request, 'find_by_metabolites.html', args)


def metabolite(request, metabolite_id):
    args = dict()
    args = check_auth_user(request, args)
    try:
        args['metabolite'] = Metabolite.objects.get(pk=metabolite_id)
        names = MetaboliteName.objects.filter(metabolite_id=metabolite_id).order_by('metabolite_synonym')
        args['synonyms'] = [x.metabolite_synonym for x in names]
    except ObjectDoesNotExist as e:
        args['error'] = 'Metabolite not found'
        experiments_base_logger.error('Metabolite error(ObjectDoesNotExist):' + str(e))
    except Exception as e:
        experiments_base_logger.error('Metabolite error:' + str(e))
        args = {}
    return render(request, 'metabolite.html', args)
