from django.shortcuts import render, redirect
from django.contrib import auth
from django.template.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

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
import collections
import csv

logging.config.dictConfig(LOGGING)
experiments_base_logger = logging.getLogger('django')
# experiments_base_logger_admin = logging.getLogger('django.request')


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


def page_403(request):
    return render(request, 'page_403.html', {})


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

    # All pages
    args['interface_experiment_name'] = InterfaceName.objects.get(search_name='experiment_name').value
    args['interface_environmental_factors'] = InterfaceName.objects.get(search_name='environmental_factors').value
    args['interface_diseases'] = InterfaceName.objects.get(search_name='diseases').value
    args['interface_way_of_life'] = InterfaceName.objects.get(search_name='way_of_life').value
    args['interface_habitat'] = InterfaceName.objects.get(search_name='habitat').value
    # args['interface_experiment_name'] = InterfaceName.objects.get(search_name='experiment_name').value

    # Experiment and experiments
    args['interface_taxon_name'] = InterfaceName.objects.get(search_name='taxon_name').value
    args['interface_gender'] = InterfaceName.objects.get(search_name='gender').value
    # args['interface_experiment_name'] = InterfaceName.objects.get(search_name='experiment_name').value

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
    except Exception as e:
        experiments_base_logger.error('get_taxon_path unknown error: ' + str(e))
        return []


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
            nodes = get_taxon_children(ch.pk)
            exps = Experiment.objects.filter(taxon_id=ch.pk)

            if nodes or exps:
                nodes += [{'text': exp.experiment_name,
                           'href': '/experiment/' + str(exp.pk),
                           'color': '#00ff00'} for exp in exps]

                children_list.append({'text': ch.taxon_name,
                                      'href': '/taxons/' + str(ch.pk),
                                      'color': '#ff0000' if ch.is_tissue else '#428bca',
                                      'nodes': nodes})
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
        if request.POST.get('query', False) is not False:
            search_word = request.POST['query']
            try:
                founded_taxons = Taxon.objects.filter(taxon_name__icontains=search_word)
                taxons_list = []
                for el in founded_taxons:
                    taxons_list.append({'id': el.id, 'name': el.taxon_name})
                return JsonResponse({'results': taxons_list})
            except Exception as e:
                experiments_base_logger.error('Taxon search error:' + str(e))
                return JsonResponse({'results': []})
        else:
            return JsonResponse({'results': []})
    else:
        return redirect('taxons')


def get_ordered_dict_of_metabolites(probs):
    prob_metabolites = ProbMetabolite.objects.filter(prob_id__in=probs)

    all_metabolites = [pm.metabolite_id for pm in prob_metabolites]
    all_metabolites = sorted(list(set(all_metabolites)), key=lambda x: x.metabolite_name)
    probs_length = probs.count()

    ordered_dict_of_metabolites = collections.OrderedDict()
    for m in all_metabolites:
        ordered_dict_of_metabolites[m.pk] = {'name': m.metabolite_name,
                                             'pub_chem_cid': m.pub_chem_cid,
                                             'concentrations': {x: '-' for x in range(probs_length)}}
    order_dict = {p_id: c for c, p_id in enumerate(sorted([x.pk for x in probs]))}

    for pm in prob_metabolites:
        ordered_dict_of_metabolites[pm.metabolite_id.pk]['concentrations'][order_dict[pm.prob_id.pk]] = \
            pm.concentration

    return ordered_dict_of_metabolites


def experiment(request, experiment_id):
    args = dict()
    args = check_auth_user(request, args)
    try:
        args['experiment'] = Experiment.objects.get(pk=experiment_id)
        probs = Prob.objects.filter(experiment_id=experiment_id).order_by('pk')
        if probs.count() == 0:
            return render(request, 'experiment.html', args)

        args['probs'] = probs
        args['metabolites'] = get_ordered_dict_of_metabolites(probs)

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
        founded_experiments_qs = Experiment.objects.filter(**search_dict).distinct('pk')

        return founded_experiments_qs
    except Exception as e:
        experiments_base_logger.error('experiments found error: ' + str(e))
        return []


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

        fields = {'experimentName': 'experiment_name__contains', 'taxonSearchName': 'taxon_id',
                  'withdrawPlace': 'withdraw_place'}
        for field, filter_name in fields.items():
            if request.POST.get(field, False):
                search_dict[filter_name] = request.POST[field]

        checkbox_fields = {'way_of_life': {'diurnalWay': 0, 'nocturnalWay': 1, 'twilightWay': 2, 'otherWay': 3},
                           'habitat': {'wildHabitat': 0, 'laboratoryHabitat': 1, 'farmHabitat': 2, 'otherHabitat': 3},
                           'gender': {'maleGender': 0, 'femaleGender': 1, 'otherGender': 2}}
        for field, values in checkbox_fields.items():
            field_in = field + '__in' if field != 'gender' else 'prob__' + field + '__in'
            search_dict[field_in] = []
            for key, value in values.items():
                if request.POST.get(key + 'Checkbox', False):
                    search_dict[field_in].append(value)

            if not search_dict[field_in]:
                search_dict.pop(field_in)

        number_fields = {'ageFrom': 'prob__month_age__gte', 'ageTo': 'prob__month_age__lte',
                         'weightFrom': 'prob__weight__gte', 'weightTo': 'prob__weight__lte',
                         'lengthFrom': 'prob__length__gte', 'lengthTo': 'prob__length__lte',
                         'hoursPostMortemFrom': 'prob__hours_post_mortem__gte',
                         'hoursPostMortemTo': 'prob__hours_post_mortem__lte',
                         'temperatureFrom': 'prob__temperature__gte', 'temperatureTo': 'prob__temperature__lte'}
        for field, filter_name in number_fields.items():
            if request.POST.get(field, False):
                search_dict[filter_name] = request.POST[field]

        # TODO need withdraw conditions
        multiple_fields = {'environmentalFactors': 'environmental_factors__in', 'diseases': 'diseases__in',
                           'comments': 'comments'}
        for field, filter_name in multiple_fields.items():
            if request.POST.get(field, False):
                search_dict[filter_name] = [request.POST[field]]

        if request.POST['withdrawDateFrom'] != '':
            search_dict['withdraw_date__gte'] = request.POST['withdrawDateFrom'] + ' 00:00:00'

        if request.POST['withdrawDateTo'] != '':
            search_dict['withdraw_date__lte'] = request.POST['withdrawDateTo'] + ' 00:00:00'

        args['error'] = dict()
        try:
            if not args['error']:
                args['experiments'] = experiments_search(search_dict)
            else:
                args['experiments'] = {}
        except Exception as e:
            experiments_base_logger.error('Search error:' + str(e))
            args = {}

    return render(request, 'experiments.html', args)


def zip_dir(path, zip_handle):

    tmp_folder = os.path.dirname(path)
    os.chdir(tmp_folder)
    archive_folder = os.path.basename(path)

    # zip_handle is zipfile handle
    for root, dirs, files in os.walk(archive_folder):
        for file in files:
            zip_handle.write(os.path.join(root, file))


def create_random_str(size):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))


def archive_and_get_response(folder):
    path_to_archive = folder + '.zip'

    zip_h = zipfile.ZipFile(path_to_archive, 'w', zipfile.ZIP_DEFLATED)
    zip_dir(folder, zip_h)
    zip_h.close()

    archive = open(path_to_archive, 'rb').read()
    response = HttpResponse(archive)

    response['status_code'] = 200
    response['Content-Type'] = 'application/zip'
    response['Content-Length'] = os.path.getsize(path_to_archive)
    response['Content-Disposition'] = "attachment; filename={}".format(os.path.basename(path_to_archive))

    os.remove(path_to_archive)
    shutil.rmtree(folder)

    return response


def create_csv_experiment_file(exp_id, folder):

    try:
        exp = Experiment.objects.get(pk=exp_id)
    except ObjectDoesNotExist:
        experiments_base_logger.warning('Exporting csv error: invalid id')
        return ''

    ways_o_life = ['diurnal', 'nocturnal', 'twilight', 'other']
    habitats = ['wild', 'laboratory', 'farm', 'other']
    genders = ['male', 'female', 'other']

    data = []
    exp_header = ['Имя эксперимента', 'Имя таксона', 'Way of life(diurnal, nocturnal,\ntwilight, other)',
                  'Habitat(wild, laboratory,\nfarm, other)', 'Withdraw place',
                  'Withdraw date\nФормат "21/11/06 16:30"', 'Comments']
    data.append(exp_header)

    exp_data = [exp.experiment_name, exp.taxon_id.taxon_name, ways_o_life[exp.way_of_life], habitats[exp.habitat],
                exp.withdraw_place,
                timezone.localtime(exp.withdraw_date).strftime('%d/%m/%y %H:%M') if exp.withdraw_date else '',
                exp.comments]
    data.append(exp_data)
    data.append([])

    probs = Prob.objects.filter(experiment_id=exp.pk).order_by('pk')
    prob_names = ['Имена проб']
    prob_genders = ['Пол(male, female, other)']
    prob_month_ages = ['Возраст(месяцы)']
    prob_hours_post_mortem = ['Время после смерти(часы)']
    prob_weights = ['Вес(кг)']
    prob_lengths = ['Рост(см)']
    prob_temperatures = ['Температура (°С)']
    prob_comments = ['Комментарии']

    for prob in probs:
        prob_names.append(prob.prob_name)
        prob_genders.append(genders[prob.gender])
        prob_month_ages.append(prob.month_age)
        prob_hours_post_mortem.append(prob.hours_post_mortem)
        prob_weights.append(prob.weight)
        prob_lengths.append(prob.length)
        prob_temperatures.append(prob.temperature)
        prob_comments.append(prob.comment)

    data.extend([prob_names, prob_genders, prob_month_ages, prob_hours_post_mortem, prob_weights, prob_lengths,
                 prob_temperatures, prob_comments, []])

    data.append([' Имена метаболитов', *[prob.prob_name for prob in probs]])
    ordered_dict_of_metabolites = get_ordered_dict_of_metabolites(probs)
    for key, value in ordered_dict_of_metabolites.items():
        data.append([value['name'], *[v if v is not None else 'undefined' for k, v in value['concentrations'].items()]])

    path = folder + exp.experiment_name + '_' + create_random_str(4) + '.csv'
    with open(path, "w", newline='', encoding='windows-1251') as csv_file:
        writer = csv.writer(csv_file, delimiter=';')
        for line in data:
            writer.writerow(line)

    return path


def experiment_download(request):
    if request.POST:
        try:
            data = json.loads(request.POST['experiments'])
        except KeyError as e:
            experiments_base_logger.warning('Probs downloading error:' + str(e))
            return JsonResponse({'error': 'Invalid field'})

        if data.get('probs', False):

            try:
                prob_ids_nmr = [prob['id'] for prob in data['probs']['NMR']]
                prob_ids_ms = [prob['id'] for prob in data['probs']['MS']]
                prob_ids_csv = [prob['id'] for prob in data['probs']['CSV']]
            except KeyError as e:
                experiments_base_logger.warning('Downloading experiment error: '
                                                'Not found keys NMR, MS or CSV in json: ' + str(e))
                return JsonResponse({'error': 'Not found keys NMR, MS or CSV in json'})

            torrents = []
            try:
                for pr in prob_ids_nmr:
                    prob = Prob.objects.get(pk=pr)
                    if prob.prob_torrent_file_nmr and prob.prob_torrent_file_nmr != 'file_error':
                        torrents.append({'name': prob.prob_name + '_nmr',
                                         'path': TORRENT_DIR + str(prob.prob_torrent_file_nmr)})
            except ObjectDoesNotExist:
                return JsonResponse({'error': 'Invalid prob nmr id'})

            try:
                for pr in prob_ids_ms:
                    prob = Prob.objects.get(pk=pr)
                    if prob.prob_torrent_file_ms and prob.prob_torrent_file_ms != 'file_error':
                        torrents.append({'name': prob.prob_name + '_ms',
                                         'path': TORRENT_DIR + str(prob.prob_torrent_file_ms)})
            except ObjectDoesNotExist:
                return JsonResponse({'error': 'Invalid prob ms id'})

            csv_folder = '/tmp/csv_' + create_random_str(16) + '/'
            os.mkdir(csv_folder)
            csv_files = []
            for exp_id in prob_ids_csv:
                csv_file = create_csv_experiment_file(exp_id, csv_folder)
                if csv_file:
                    csv_files.append(csv_file)

            try:
                folder = '/tmp/probs_' + create_random_str(16) + '/'
                os.mkdir(folder)

                for t in torrents:
                    shutil.copy(t['path'], folder + t['name'] + '_' + os.path.basename(t['path']))

                for csv_file in csv_files:
                    shutil.copy(csv_file, folder + os.path.basename(csv_file))

                shutil.rmtree(csv_folder)
                return archive_and_get_response(folder[:-1])

            except Exception as e:
                shutil.rmtree(csv_folder)
                experiments_base_logger.error('Probs downloading error:' + str(e))
                return JsonResponse({'error': 'Cant create archive'})
        else:
            if data.get('experiments', False):
                try:
                    experiment_ids_nmr = [exp['id'] for exp in data['experiments']['NMR']]
                    experiment_ids_ms = [exp['id'] for exp in data['experiments']['MS']]
                    experiment_ids_csv = [exp['id'] for exp in data['experiments']['CSV']]
                except KeyError as e:
                    experiments_base_logger.warning('Downloading experiment error: '
                                                    'Not found keys NMR, MS or CSV in json: ' + str(e))
                    return JsonResponse({'error': 'Not found keys NMR, MS or CSV in json'})

                try:
                    folder = '/tmp/experiments_' + create_random_str(16) + '/'
                    os.mkdir(folder)

                    try:
                        for exp_id in list(set(experiment_ids_nmr + experiment_ids_ms + experiment_ids_csv)):
                            exp = Experiment.objects.get(pk=exp_id)
                            probs = Prob.objects.filter(experiment_id=exp_id)

                            exp_folder = folder + exp.experiment_name + '_' + create_random_str(4) + '/'
                            os.mkdir(exp_folder)

                            if probs.count() > 0:
                                for pr in probs:
                                    if exp_id in experiment_ids_nmr:
                                        if pr.prob_torrent_file_nmr and pr.prob_torrent_file_nmr != 'file_error':
                                            tp = TORRENT_DIR + str(pr.prob_torrent_file_nmr)
                                            shutil.copy(tp, exp_folder + pr.prob_name + '_nmr_' + os.path.basename(tp))
                                    if exp_id in experiment_ids_ms:
                                        if pr.prob_torrent_file_ms and pr.prob_torrent_file_ms != 'file_error':
                                            tp = TORRENT_DIR + str(pr.prob_torrent_file_ms)
                                            shutil.copy(tp, exp_folder + pr.prob_name + '_ms_' + os.path.basename(tp))

                            if exp_id in experiment_ids_csv:
                                csv_file = create_csv_experiment_file(exp_id, exp_folder)
                                if not csv_file:
                                    experiments_base_logger.warning('Experiments downloading error: '
                                                                    'csv file was not created')

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
                    query = MetaboliteName.objects.get(metabolite_synonym__iexact=el)
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
