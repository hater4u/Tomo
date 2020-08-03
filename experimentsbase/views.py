from django.shortcuts import render, redirect
from django.contrib import auth
from django.template.context_processors import csrf
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import model_to_dict

from tomo.settings import API_URL, SHARED_FILES_DIR, LOGGING
from .models import Taxon, Experiment, Prob, ProbMetabolite, MetaboliteName

import requests
import json
import os
import base64
import zipfile
import random
import string
import shutil
import logging
import logging.config

logging.config.dictConfig(LOGGING)
experimentbase_logger = logging.getLogger('django')
# experimentbase_logger_admin = logging.getLogger('django.request')


# TODO: write normal index
def index(request):
    return redirect('taxons/')


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
    except Exception:
        experimentbase_logger.warning('hierarchy found error, maybe it is root')
        return []


def get_taxon_children(taxon_id):
    try:
        return requests.get(API_URL + '/taxa/byParent', params={'parentId': taxon_id}).json()['value']
    except Exception:
        experimentbase_logger.error('children found error, maybe problems with API')
        return []


def experiments_search(search_dict):
    try:
        founded_experiments_qs = Experiment.objects.filter(**search_dict)

        return founded_experiments_qs
    except Exception as e:
        experimentbase_logger.error('experiments found error: ' + str(e))
        return []


def check_experiments_data(data_json):
    info_dict = dict()
    info_dict['error'] = []
    fields = {'experimentName': 'Experiment name is missing',
              'taxonSearchName': 'Taxon name is missing',
              'wayOfLife': 'Empty field value "Way of life"',
              'habitat': 'Empty field value "Habitat"',
              'gender': 'Empty field value "Gender"',
              'monthsAge': 'Empty field value "Age"',
              'weight': 'Empty field value "Weight"',
              'length': 'Empty field value "Length"',
              'withdrawDate': 'Empty field value "Withdraw date"',
              # 'withdrawPlace': 'Empty field value ""',
              'hoursPostMortem': 'Empty field value "Hours post mortem"',
              'temperature': 'Empty field value "Temperature"',
              }
    for key, value in fields.items():
        if data_json.get(key, False):
            if data_json[key] == '':
                info_dict['error'].append(value)
        else:
            info_dict['error'].append('Missing field ' + key)

    try:
        all_taxons = requests.get(API_URL + '/taxa/all').json()['value']
        found = False
        for el in all_taxons:
            if el['name'] == data_json['taxonSearchName']:
                data_json['taxonId'] = el['id']
                found = True
                break
        if not found:
            info_dict['error'] = ['Invalid taxon name']

            return info_dict
    except Exception as e:
        info_dict['error'] = ['API access problem. Contact the server administrator.']
        experimentbase_logger.error('Problems with API')
        return info_dict

    fields_lists = {
        'environmentalFactors': 'Empty value in fields "Environmental factors"',
        'diseases': 'Empty value in fields "Diseases"',
        'comments': 'Empty value in fields "Comments"',
        'filepaths': 'Empty value in fields "File paths"',
    }

    for key, value in fields_lists.items():
        if data_json.get(key, False):
            for el in data_json[key]:
                if el == '':
                    info_dict['error'].append(value)

    if data_json.get('additionalProperties', False):
        for el in data_json['additionalProperties']:
            for key, value in el.items():
                # for key, value in data_json['additionalProperties'].items():
                if key == '':
                    info_dict['error'].append('Empty key in add. properties')
                if value == '':
                    info_dict['error'].append('Empty value ' + key + ' in add. properties')

        add_props = dict()
        for el in data_json['additionalProperties']:
            for key, value in el.items():
                add_props[key] = value

        data_json['additionalProperties'] = add_props

    metabolit_fields = ['pubChemCid', 'metaName', 'concentration', 'analysisMethod']

    if data_json.get('metabolites', False):
        for el in data_json['metabolites']:
            empty_field = False
            for field in metabolit_fields:
                if not el.get(field, False):
                    info_dict['error'].append('Missing field ' + field + ' in metabolite')
                    empty_field = True
            if not empty_field:
                for field in metabolit_fields:
                    if el[field] == '':
                        info_dict['error'].append('Empty value ' + field + ' in metabolite')

        for el in data_json['metabolites']:
            el['name'] = el['metaName']
            el.pop('metaName', None)

    if data_json.get('csrfmiddlewaretoken', False):
        data_json.pop('csrfmiddlewaretoken', None)

    if data_json.get('taxonSearchName', False):
        data_json.pop('taxonSearchName', None)

    # File paths
    if data_json.get('withdrawDate', False):
        data_json['withdrawDate'] += " 00:00:00"
    if data_json.get('experimentName', False):
        data_json['name'] = data_json['experimentName']
        data_json.pop('experimentName', None)

    return info_dict


def get_sub_taxons(taxon_id):
    all_sub_taxons = []
    sub_taxons = Taxon.objects.filter(parent_id=taxon_id)
    all_sub_taxons += sub_taxons

    for el in sub_taxons:
        all_sub_taxons += get_sub_taxons(el.pk)

    return all_sub_taxons


def get_taxon_and_sub_taxon_experiments(taxon_id):
    all_sub_taxons = [Taxon.objects.get(pk=taxon_id)]
    all_sub_taxons += get_sub_taxons(taxon_id)

    all_experiments = []
    for el in all_sub_taxons:
        all_experiments += Experiment.objects.filter(taxon_id=el.pk)

    return all_experiments


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
    else:
        args['children'] = Taxon.objects.filter(parent_id=taxon_id)
        experiments_dict = get_taxon_and_sub_taxon_experiments(taxon_id)

    args['experiments'] = experiments_dict

    return render(request, 'taxons.html', args)


def taxons(request):
    return taxons_id(request, '')


# def taxon_parent_search(request):
#     if request.POST:
#         parent_name = request.POST['parentName']
#         try:
#             all_taxons = requests.get(API_URL + '/taxa/all').json()['value']
#             taxons = []
#             for el in all_taxons:
#                 if el['name'].startswith(parent_name):
#                     taxons.append(el)
#             return JsonResponse({'value': taxons})
#         except Exception as e:
#             experimentbase_logger.error('Taxon search error:' + str(e))
#             return JsonResponse({'value': []})
#     else:
#         return redirect('taxons')
#
#
# def taxon_add(request):
#     args = dict()
#     args = check_auth_user(request, args)
#     args.update(csrf(request))
#     if request.user.is_authenticated:
#         if request.user.is_staff:
#             if request.POST:
#                 if request.POST['taxonName'] == '':
#                     args['success'] = False
#                     args['message'] = 'Taxon name is missing'
#                     return render(request, 'taxon/new.html', args)
#
#                 try:
#                     all_taxons = requests.get(API_URL + '/taxa/all').json()['value']
#                     all_taxons.append({'name': '', 'id': ''})
#                     # experimentbase_logger.info('all taxons: ' + all_taxons)
#                     for el in all_taxons:
#                         if el['name'] == request.POST['taxonParentName']:
#                             parent_id = el['id']
#                             try:
#                                 headers = {'Content-Type': 'application/json'}
#                                 if requests.post(API_URL + '/taxa/add',
#                                                  data=json.dumps({'name': request.POST['taxonName'],
#                                                                   'parentId': parent_id}),
#                                                  headers=headers,
#                                                  auth=('docker_admin', '123qweasdzxc')).status_code == 200:
#                                     args['success'] = True
#                                     args['message'] = 'Taxon added successfully'
#                                 else:
#                                     args['success'] = False
#                                     args['message'] = 'Taxon has not been added. Contact the server administrator.'
#                                 return render(request, 'taxon/new.html', args)
#
#                             except Exception as exp:
#                                 experimentbase_logger.error('Error add taxon:' + str(exp))
#                                 args['success'] = False
#                                 args['message'] = 'Taxon add problem. Contact the server administrator.'
#                                 return render(request, 'taxon/new.html', args)
#                     args['success'] = False
#                     args['message'] = 'No such taxon parent found'
#                     return render(request, 'taxon/new.html', args)
#                 except Exception as e:
#                     experimentbase_logger.error('Error add taxon:' + str(e))
#                     args['success'] = False
#                     args['message'] = 'API access problem. Contact the server administrator.'
#                     return render(request, 'taxon/new.html', args)
#             else:
#                 return render(request, 'taxon/new.html', args)
#         else:
#             return render(request, 'reg/403.html', args)
#     else:
#         return redirect('login')
#
#
# def taxon_rename_id(request, taxon_id):
#     args = dict()
#     args['taxon_id'] = taxon_id
#     args = check_auth_user(request, args)
#     args.update(csrf(request))
#     if request.user.is_authenticated:
#         if request.user.is_staff:
#
#             try:
#                 args['taxon_name'] = requests.get(API_URL + '/taxa', params={'id': taxon_id}).json()['value']['name']
#             except Exception as e:
#                 experimentbase_logger.error('API troubles: ' + str(e))
#                 args['success'] = False
#                 args['message'] = 'API access problem. Contact the server administrator.'
#                 return render(request, 'taxon/rename.html', args)
#
#             if request.POST:
#                 if request.POST['taxonName'] == '':
#                     args['success'] = False
#                     args['message'] = 'Taxon name is missing'
#                     return render(request, 'taxon/rename.html', args)
#
#                 try:
#                     headers = {'Content-Type': 'application/json'}
#                     if requests.post(API_URL + '/taxa/rename',
#                                      data=json.dumps({'id': taxon_id, 'name': request.POST['taxonName']}),
#                                      headers=headers,
#                                      auth=('docker_admin', '123qweasdzxc')).status_code == 200:
#                         args['success'] = True
#                         args['message'] = 'Taxon name changed successfully'
#                     else:
#                         args['success'] = False
#                         args['message'] = 'Taxon name has not been changed. Contact the server administrator.'
#                     return render(request, 'taxon/rename.html', args)
#                 except Exception as e:
#                     experimentbase_logger.error('Error rename taxon:' + str(e))
#                     args['success'] = False
#                     args['message'] = 'API access problem. Contact the server administrator.'
#                     return render(request, 'taxon/rename.html', args)
#
#             else:
#                 return render(request, 'taxon/rename.html', args)
#         else:
#             return render(request, 'reg/403.html')
#     else:
#         return redirect('login')
#
#
# def taxon_rename(request):
#     return redirect('taxons')
#
#
# def taxon_move_id(request, taxon_id):
#     args = dict()
#     args = check_auth_user(request, args)
#     args.update(csrf(request))
#     if request.user.is_authenticated:
#         if request.user.is_staff:
#             args['taxon_id'] = taxon_id
#             try:
#                 values = requests.get(API_URL + '/taxa',
#                                       params={'id': taxon_id}).json()['value']
#                 args['taxon_name'] = values['name']
#                 if values['parentId']:
#                     args['taxon_parent_name'] = requests.get(API_URL + '/taxa',
#                                                              params={'id': values['parentId']}).json()['value']['name']
#                 else:
#                     args['taxon_parent_name'] = ''
#             except Exception as e:
#                 experimentbase_logger.error('Error move taxon, getting taxon_parent_id :' + str(e))
#                 args['success'] = False
#                 args['message'] = 'API access problem. Contact the server administrator.'
#                 return render(request, 'taxon/move.html', args)
#
#             if request.POST:
#                 try:
#                     all_taxons = requests.get(API_URL + '/taxa/all').json()['value']
#                     all_taxons.append({'name': '', 'id': ''})
#                     # experimentbase_logger.info('all taxons: ' + all_taxons)
#                     for el in all_taxons:
#                         if el['name'] == request.POST['taxonParentName']:
#                             parent_id = el['id']
#                             try:
#                                 headers = {'Content-Type': 'application/json'}
#                                 if requests.post(API_URL + '/taxa/move',
#                                                  data=json.dumps({'id': taxon_id,
#                                                                   'parentId': parent_id}),
#                                                  headers=headers,
#                                                  auth=('docker_admin', '123qweasdzxc')).status_code == 200:
#                                     args['success'] = True
#                                     args['message'] = 'Taxon successfully moved'
#                                 else:
#                                     args['success'] = False
#                                     args['message'] = 'Taxon has not been moved. Contact the server administrator.'
#                                 return render(request, 'taxon/move.html', args)
#
#                             except Exception as exp:
#                                 experimentbase_logger.error('Error move taxon:' + str(exp))
#                                 args['success'] = False
#                                 args['message'] = 'Taxon move problem. Contact the server administrator. '
#                                 return render(request, 'taxon/move.html', args)
#                     args['success'] = False
#                     args['message'] = 'No such taxon parent found'
#                     return render(request, 'taxon/move.html', args)
#                 except Exception as e:
#                     experimentbase_logger.error('Error add taxon:' + str(e))
#                     args['success'] = False
#                     args['message'] = 'API access problem. Contact the server administrator.'
#                     return render(request, 'taxon/move.html', args)
#             else:
#                 return render(request, 'taxon/move.html', args)
#         else:
#             return render(request, 'reg/403.html', args)
#     else:
#         return redirect('login')
#
#
# def taxon_move(request):
#     return redirect('taxons')
#
#
# def taxon_delete_id(request, taxon_id):
#     args = dict()
#     # Terrible
#     args = check_auth_user(request, args)
#     args.update(csrf(request))
#     if request.user.is_authenticated:
#         if request.user.is_staff:
#             args['taxon_id'] = taxon_id
#
#             try:
#                 args['taxon_name'] = requests.get(API_URL + '/taxa', params={'id': taxon_id}).json()['value'][
#                     'name']
#             except Exception as e:
#                 experimentbase_logger.error('Error delete taxon, getting taxon_name :' + str(e))
#                 args['success'] = False
#                 args['message'] = 'API access problem. Contact the server administrator.'
#                 return render(request, 'taxon/delete.html', args)
#
#             if request.POST:
#                 if request.POST['delete']:
#                     try:
#                         headers = {'Content-Type': 'application/json'}
#                         req = requests.post(API_URL + '/taxa/delete',
#                                          data=json.dumps({'id': taxon_id}),
#                                          headers=headers,
#                                          auth=('docker_admin', '123qweasdzxc'))
#                         if req.status_code == 200:
#                             args['success'] = True
#                             args['message'] = 'Taxon deleted successfully'
#                         else:
#                             args['success'] = False
#                             args['message'] = 'Taxon has not been deleted. Contact the server administrator.'
#                         return render(request, 'taxon/delete.html', args)
#                     except Exception as e:
#                         experimentbase_logger.error('Error delete taxon, getting taxon_name :' + str(e))
#                         args['success'] = False
#                         args['message'] = 'API access problem. Contact the server administrator.'
#                         return render(request, 'taxon/delete.html', args)
#             else:
#                 return render(request, 'taxon/delete.html', args)
#         else:
#             return render(request, 'reg/403.html')
#     else:
#         return redirect('login')
#
#
# def taxon_delete(request):
#     return redirect('taxons')


def search_file(request, experiment_id):
    if request.user.is_authenticated:
        if request.user.is_staff:
            if request.method == 'POST':

                try:
                    path = request.POST.get('path', False)
                except Exception as e:
                    experimentbase_logger.error('Incorrect path')
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
                    experimentbase_logger.error('File not found')
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
        max_metabolites_prob = 0
        all_metabolites = []
        for prob in probs:
            pms = ProbMetabolite.objects.filter(prob_id=prob.pk)

            if pms.count() > max_metabolites_num:
                max_metabolites_prob = prob
                max_metabolites_num = pms.count()

            all_metabolites.append(pms)

        meta_id_in_num = dict()
        prob_metabolites = ProbMetabolite.objects.filter(prob_id=max_metabolites_prob.pk). \
            order_by('metabolite_id__metabolite_name')

        for counter, m in enumerate(prob_metabolites):
            meta_id_in_num[m.metabolite_id] = counter

        dict_of_metabolites = {}
        for counter, m in enumerate(prob_metabolites):
            dict_of_metabolites[counter] = {'name': m.metabolite_id.metabolite_name,
                                            'pubchemcid': m.metabolite_id.pubchemcid,
                                            'consentrations': {x: '' for x in range(max_metabolites_num)}}

        for counter, pms in enumerate(all_metabolites):
            for m in pms:
                dict_of_metabolites[meta_id_in_num[m.metabolite_id]]['consentrations'][counter] = m.concentration

        args['metabolites'] = dict_of_metabolites

    except ObjectDoesNotExist as e:
        args['error'] = 'Experiment not found'
        experimentbase_logger.error('Experiment error(ObjectDoesNotExist):' + str(e))
    except Exception as e:
        experimentbase_logger.error('Experiment error:' + str(e))
        args = {}
    return render(request, 'experiment.html', args)


# def experiment_add(request):
#     args = dict()
#     args = check_auth_user(request, args)
#     args.update(csrf(request))
#     if request.user.is_authenticated:
#         if request.user.is_staff:
#             if request.method == 'POST':
#                 try:
#                     data = json.loads(request.body)
#                 except ValueError as e:
#                     experimentbase_logger.error('JSON parse error: ' + str(e))
#                     args['success'] = False
#                     args['message'] = 'Incorrect request form.'
#                     return render(request, 'experiment/add.html', args)
#                 info_dict = check_experiments_data(data)
#                 if not info_dict['error']:
#                     try:
#                         headers = {'Content-Type': 'application/json'}
#                         req = requests.post(API_URL + '/experiments/add', data=json.dumps(data),
#                                             headers=headers,
#                                             auth=('docker_admin', '123qweasdzxc'))
#                         if req.status_code == 200:
#                             info_dict['success'] = 'Experiment added successfully'
#                         else:
#                             info_dict['error'].append('Incorrect form data.')
#                     except Exception as e:
#                         info_dict['error'].append('API access problem. Contact the server administrator.')
#                         experimentbase_logger.error('Problems with API')
#                 # return JsonResponse(json.dumps(info_dict))
#                 return JsonResponse(info_dict)
#             else:
#                 return render(request, 'experiment/add.html', args)
#         else:
#             return render(request, 'reg/403.html')
#     else:
#         return redirect('login')
#
#
# def zipdir(path, ziph):
#     # ziph is zipfile handle
#     for root, dirs, files in os.walk(path):
#         for file in files:
#             ziph.write(os.path.join(root, file))
#
#
# def create_random_str(size):
#     return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))
#
#
# def experiment_download(request):
#
#     if request.POST:
#         try:
#             experiments_list = json.loads(request.POST['experiments'])['experiments']
#
#             folder = create_random_str(16)
#             os.mkdir('/tmp/' + folder)
#
#             for counter, el in enumerate(experiments_list):
#                 os.mkdir('/tmp/' + folder + '/experiment' + str(counter))
#
#                 i = 0
#                 while i < int(el['quantity']):
#                     req = requests.get(API_URL + '/experiments', params={'id': el['id']})
#                     value = req.json()['value']
#                     torrent_path = value['fileInfos'][i]['torrentFilePath']
#                     file_name = os.path.basename(value['fileInfos'][i]['filepath'])
#
#                     req = requests.get(API_URL + '/experiments/getTorrent', params={'torrentPath': torrent_path})
#                     torrent_file = base64.b64decode(req.json()['value'])
#
#                     f1 = open('/tmp/' + folder + '/experiment' + str(counter) + '/' + file_name + str(i) + '.torrent', 'wb')
#                     f1.write(torrent_file)
#                     f1.close()
#
#                     i += 1
#
#             path_to_archive = '/tmp/experiment_torrents_' + folder + '.zip'
#
#             zipf = zipfile.ZipFile(path_to_archive, 'w', zipfile.ZIP_DEFLATED)
#             zipdir('/tmp/' + folder, zipf)
#             zipf.close()
#
#             archive = open(path_to_archive, 'rb').read()
#             response = HttpResponse(archive)
#
#             response['status_code'] = 200
#             response['Content-Type'] = 'application/zip'
#             response['Content-Length'] = os.path.getsize(path_to_archive)
#             response['Content-Disposition'] = "attachment; filename=experiment_torrents.zip"
#
#             os.remove(path_to_archive)
#             shutil.rmtree('/tmp/' + folder)
#
#             return response
#
#         except Exception as e:
#             experimentbase_logger.error('Creation zip archive error: ' + str(e))
#             return JsonResponse({'error': 'cant create archive'})
#
#     return render(request, '', {})
#
#
# def experiment_change(request, experiment_id):
#     args = dict()
#     args = check_auth_user(request, args)
#     args.update(csrf(request))
#     if request.user.is_authenticated:
#         if request.user.is_staff:
#             # get experiment fields and set them to inputs
#             try:
#                 req = requests.get(API_URL + '/experiments', params={'id': experiment_id})
#                 args['experiment'] = req.json()['value']
#
#                 # get taxon_name from taxon_id
#                 req = requests.get(API_URL + '/taxa', params={'id': args['experiment']['taxonId']})
#                 args['experiment']['taxon_name'] = req.json()['value']['name']
#
#                 # get date from datetime - minus 9 symbols(' 00:00:00')
#                 args['experiment']['withdrawDate'] = args['experiment']['withdrawDate'][:-9]
#             except Exception as e:
#                 experimentbase_logger.error('Incorrect experiment id or troubles with API ' + str(e))
#                 args['success'] = False
#                 args['message'] = 'Incorrect experiment id or troubles with API.'
#
#             if request.method == 'POST':
#                 try:
#                     data = json.loads(request.body)
#                 except ValueError as e:
#                     experimentbase_logger.error('JSON parse error: ' + str(e))
#                     args['success'] = False
#                     args['message'] = 'Incorrect request form.'
#                     return render(request, 'experiment/change.html', args)
#                 info_dict = check_experiments_data(data)
#                 if not info_dict['error']:
#                     try:
#                         data['id'] = experiment_id
#                         headers = {'Content-Type': 'application/json'}
#                         req = requests.post(API_URL + '/experiments/edit', params={'id': experiment_id}, data=json.dumps(data),
#                                             headers=headers,
#                                             auth=('docker_admin', '123qweasdzxc'))
#                         if req.status_code == 200:
#                             info_dict['success'] = 'Experiment succesfully changed'
#                         else:
#                             info_dict['error'].append('Incorrect form data')
#                     except Exception as e:
#                         info_dict['error'].append('API access problem. Contact the server administrator.')
#                         experimentbase_logger.error('Problems with API')
#                 # return JsonResponse(json.dumps(info_dict))
#                 return JsonResponse(info_dict)
#             else:
#                 return render(request, 'experiment/change.html', args)
#         else:
#             return render(request, 'reg/403.html')
#     else:
#         return redirect('login')
#
#
# def experiment_delete(request, experiment_id):
#     args = dict()
#     args = check_auth_user(request, args)
#     args.update(csrf(request))
#     if request.user.is_authenticated:
#         if request.user.is_staff:
#             args['experiment_id'] = experiment_id
#             try:
#                 args['experiment_name'] = requests.get(API_URL + '/experiments', params={'id': experiment_id}).json()[
#                     'value']['name']
#             except Exception as e:
#                 experimentbase_logger.error('Error delete experiment, getting experiment_name :' + str(e))
#                 args['success'] = False
#                 args['message'] = 'API access problem. Contact the server administrator.'
#                 return render(request, 'experiment/delete.html', args)
#             if request.POST:
#                 try:
#                     headers = {'Content-Type': 'application/json'}
#                     req = requests.post(API_URL + '/experiments/delete',
#                                         data=json.dumps({'id': experiment_id}),
#                                         headers=headers,
#                                         auth=('docker_admin', '123qweasdzxc'))
#                     if req.status_code == 200:
#                         args['success'] = True
#                         args['message'] = 'Experiment deleted successfully'
#                     else:
#                         args['success'] = False
#                         args['message'] = 'Experiment has not been deleted. Contact the server administrator.'
#                     return render(request, 'experiment/delete.html', args)
#                 except Exception as e:
#                     experimentbase_logger.error('error delete experiment:' + str(e))
#                     args['success'] = False
#                     args['message'] = 'API access problem. Contact the server administrator.'
#                     return render(request, 'experiment/delete.html', args)
#             else:
#                 return render(request, 'experiment/delete.html', args)
#         else:
#             return render(request, 'reg/403.html')
#     else:
#         return redirect('login')


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
        experimentbase_logger.error("getting torrent error")
        return redirect('index')


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
            search_dict['experiment_name'] = request.POST['experimentName']

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
        search_dict['gender__in'] = []
        if request.POST.get('maleGenderCheckbox', False):
            search_dict['gender__in'].append(0)

        if request.POST.get('femaleGenderCheckbox', False):
            search_dict['gender__in'].append(1)

        if request.POST.get('otherGenderCheckbox', False):
            search_dict['gender__in'].append(2)

        # TODO remove kostyls
        if not search_dict['gender__in']:
            search_dict.pop('gender__in')

        # Age
        if not request.POST['ageFrom'] == '':
            # search_dict['month_age__gte'] = 0
            # else:
            search_dict['month_age__gte'] = request.POST['ageFrom']

        if not request.POST['ageTo'] == '':
            search_dict['month_age__lte'] = request.POST['ageTo']

        # Weight
        if not request.POST['weightFrom'] == '':
            search_dict['weight__gte'] = request.POST['weightFrom']

        if not request.POST['weightTo'] == '':
            search_dict['weight__lte'] = request.POST['weightTo']

        # Length
        if not request.POST['lengthFrom'] == '':
            search_dict['length__gte'] = request.POST['lengthFrom']

        if not request.POST['lengthTo'] == '':
            search_dict['length__lte'] = request.POST['lengthTo']

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
            search_dict['hours_post_mortem__gte'] = request.POST['secondsPostMortemFrom']

        if not request.POST['hoursPostMortemTo'] == '':
            search_dict['hours_post_mortem__lte'] = request.POST['secondsPostMortemTo']

        # Temperature
        if not request.POST['temperatureFrom'] == '':
            search_dict['temperature__gte'] = request.POST['temperatureFrom']

        if not request.POST['temperatureTo'] == '':
            search_dict['temperature__lte'] = request.POST['temperatureTo']

        # Comments
        if not request.POST['comments'] == '':
            search_dict['comments'] = [request.POST['comments']]

        try:
            if not args['error']:
                args['experiments'] = experiments_search(search_dict)
            else:
                args['experiments'] = {}
        except Exception as e:
            experimentbase_logger.error('Search error:' + str(e))
            args = {}

    return render(request, 'experiments.html', args)


def find_by_metabolites(request):
    args = dict()
    args = check_auth_user(request, args)
    args.update(csrf(request))

    if request.POST:
        metabolite_names = request.POST.get('metaboliteNames', False)
        if metabolite_names:
            metabolite_names = metabolite_names.split(' AND ')
            meta_lenght = len(metabolite_names)

            found_names = set()
            not_found_names = []
            for el in metabolite_names:
                try:
                    query = MetaboliteName.objects.get(metabolite_synonym=el)
                    found_names.add(query.metabolite_id)
                except ObjectDoesNotExist as e:
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
                    if query.count() == meta_lenght:
                        exp_ids.add(el.experiment_id)

                if len(exp_ids) == 0:
                    args['error'] = 'Experiments with this conditions not found'
                else:
                    args['experiments'] = exp_ids

    return render(request, 'find_by_metabolites.html', args)
