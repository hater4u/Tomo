from django.shortcuts import render, redirect
from django.contrib import auth
from django.template.context_processors import csrf
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User

from tomo.settings import API_URL, SHARED_FILES_DIR, LOGGING

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

#TODO delete
from django.views.decorators.csrf import csrf_exempt

logging.config.dictConfig(LOGGING)
experimentbase_logger = logging.getLogger('django')
# experimentbase_logger_admin = logging.getLogger('django.request')


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
    if request.user.is_authenticated:
        args['nickname'] = request.user.get_username()
        args['authenticated'] = True
        if request.user.is_staff:
            args['user_auth'] = True
    return args


def get_taxon_path(taxon_id):
    hierarchy = list()
    try:
        values = requests.get(API_URL + '/taxa', params={'id': taxon_id}).json()
        hierarchy.append({'id': taxon_id, 'name': values['value']['name']})
        parent_id = values['value']['parentId']
        while parent_id:
            values = requests.get(API_URL + '/taxa', params={'id': parent_id}).json()
            parent_name = values['value']['name']
            hierarchy.append({'id': parent_id, 'name': parent_name})
            parent_id = values['value']['parentId']
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
        headers = {'Content-type': 'application/json'}
        return requests.post(API_URL + '/experiments/search',
                             data=json.dumps(search_dict), headers=headers).json()['value']
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


# def translate_experiments(experiments_list):
#     way_of_life = {'DIURNAL': 'Дневное', 'NOCTURNAL': 'Ночное', 'TWILIGHT': 'Сумеречное', 'OTHER': 'Другое'}
#     habitat = {'WILD': 'Дикое', 'LABORATORY': 'Лабораторное', 'FARM': 'Фермерское', 'OTHER': 'Другое'}
#     gender = {'MALE': 'Мужской', 'FEMALE': 'Женский', 'OTHER': 'Другое'}
#
#     for el in experiments_list:
#         el['wayOfLife'] = way_of_life[el['wayOfLife']]
#         el['habitat'] = habitat[el['habitat']]
#         el['gender'] = gender[el['gender']]
#
#     return experiments_list


def taxons_id(request, taxon_id):
    args = dict()
    args.update(csrf(request))
    args['taxon_id'] = taxon_id
    hierarchy = get_taxon_path(taxon_id)
    hierarchy.reverse()
    args['hierarchy'] = hierarchy
    args['children'] = get_taxon_children(taxon_id)

    if taxon_id == '':
        args['index_taxons'] = True
        experiments_dict = []
    else:
        search_dict = {'taxonIds': [taxon_id]}
        experiments_dict = experiments_search(search_dict)

    # args['experiments'] = translate_experiments(experiments_dict)
    args['experiments'] = experiments_dict

    args = check_auth_user(request, args)

    return render(request, 'taxons.html', args)


def taxons(request):
    return taxons_id(request, '')


def taxon_parent_search(request):
    if request.POST:
        parent_name = request.POST['parentName']
        try:
            all_taxons = requests.get(API_URL + '/taxa/all').json()['value']
            taxons = []
            for el in all_taxons:
                if el['name'].startswith(parent_name):
                    taxons.append(el)
            return JsonResponse({'value': taxons})
        except Exception as e:
            experimentbase_logger.error('Taxon search error:' + str(e))
            return JsonResponse({'value': []})
    else:
        return redirect('taxons')


def taxon_add(request):
    args = dict()
    args = check_auth_user(request, args)
    args.update(csrf(request))
    if request.user.is_authenticated:
        if request.user.is_staff:
            if request.POST:
                if request.POST['taxonName'] == '':
                    args['success'] = False
                    args['message'] = 'Taxon name is missing'
                    return render(request, 'taxon/new.html', args)

                try:
                    all_taxons = requests.get(API_URL + '/taxa/all').json()['value']
                    all_taxons.append({'name': '', 'id': ''})
                    # experimentbase_logger.info('all taxons: ' + all_taxons)
                    for el in all_taxons:
                        if el['name'] == request.POST['taxonParentName']:
                            parent_id = el['id']
                            try:
                                headers = {'Content-Type': 'application/json'}
                                if requests.post(API_URL + '/taxa/add',
                                                 data=json.dumps({'name': request.POST['taxonName'],
                                                                  'parentId': parent_id}),
                                                 headers=headers,
                                                 auth=('docker_admin', '123qweasdzxc')).status_code == 200:
                                    args['success'] = True
                                    args['message'] = 'Taxon added successfully'
                                else:
                                    args['success'] = False
                                    args['message'] = 'Taxon has not been added. Contact the server administrator.'
                                return render(request, 'taxon/new.html', args)

                            except Exception as exp:
                                experimentbase_logger.error('Error add taxon:' + str(exp))
                                args['success'] = False
                                args['message'] = 'Taxon add problem. Contact the server administrator.'
                                return render(request, 'taxon/new.html', args)
                    args['success'] = False
                    args['message'] = 'No such taxon parent found'
                    return render(request, 'taxon/new.html', args)
                except Exception as e:
                    experimentbase_logger.error('Error add taxon:' + str(e))
                    args['success'] = False
                    args['message'] = 'API access problem. Contact the server administrator.'
                    return render(request, 'taxon/new.html', args)
            else:
                return render(request, 'taxon/new.html', args)
        else:
            return render(request, 'reg/403.html', args)
    else:
        return redirect('login')


def taxon_rename_id(request, taxon_id):
    args = dict()
    args['taxon_id'] = taxon_id
    args = check_auth_user(request, args)
    args.update(csrf(request))
    if request.user.is_authenticated:
        if request.user.is_staff:

            try:
                args['taxon_name'] = requests.get(API_URL + '/taxa', params={'id': taxon_id}).json()['value']['name']
            except Exception as e:
                experimentbase_logger.error('API troubles: ' + str(e))
                args['success'] = False
                args['message'] = 'API access problem. Contact the server administrator.'
                return render(request, 'taxon/rename.html', args)

            if request.POST:
                if request.POST['taxonName'] == '':
                    args['success'] = False
                    args['message'] = 'Taxon name is missing'
                    return render(request, 'taxon/rename.html', args)

                try:
                    headers = {'Content-Type': 'application/json'}
                    if requests.post(API_URL + '/taxa/rename',
                                     data=json.dumps({'id': taxon_id, 'name': request.POST['taxonName']}),
                                     headers=headers,
                                     auth=('docker_admin', '123qweasdzxc')).status_code == 200:
                        args['success'] = True
                        args['message'] = 'Taxon name changed successfully'
                    else:
                        args['success'] = False
                        args['message'] = 'Taxon name has not been changed. Contact the server administrator.'
                    return render(request, 'taxon/rename.html', args)
                except Exception as e:
                    experimentbase_logger.error('Error rename taxon:' + str(e))
                    args['success'] = False
                    args['message'] = 'API access problem. Contact the server administrator.'
                    return render(request, 'taxon/rename.html', args)

            else:
                return render(request, 'taxon/rename.html', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def taxon_rename(request):
    return redirect('taxons')


def taxon_move_id(request, taxon_id):
    args = dict()
    args = check_auth_user(request, args)
    args.update(csrf(request))
    if request.user.is_authenticated:
        if request.user.is_staff:
            args['taxon_id'] = taxon_id
            try:
                values = requests.get(API_URL + '/taxa',
                                      params={'id': taxon_id}).json()['value']
                args['taxon_name'] = values['name']
                if values['parentId']:
                    args['taxon_parent_name'] = requests.get(API_URL + '/taxa',
                                                             params={'id': values['parentId']}).json()['value']['name']
                else:
                    args['taxon_parent_name'] = ''
            except Exception as e:
                experimentbase_logger.error('Error move taxon, getting taxon_parent_id :' + str(e))
                args['success'] = False
                args['message'] = 'API access problem. Contact the server administrator.'
                return render(request, 'taxon/move.html', args)

            if request.POST:
                try:
                    all_taxons = requests.get(API_URL + '/taxa/all').json()['value']
                    all_taxons.append({'name': '', 'id': ''})
                    # experimentbase_logger.info('all taxons: ' + all_taxons)
                    for el in all_taxons:
                        if el['name'] == request.POST['taxonParentName']:
                            parent_id = el['id']
                            try:
                                headers = {'Content-Type': 'application/json'}
                                if requests.post(API_URL + '/taxa/move',
                                                 data=json.dumps({'id': taxon_id,
                                                                  'parentId': parent_id}),
                                                 headers=headers,
                                                 auth=('docker_admin', '123qweasdzxc')).status_code == 200:
                                    args['success'] = True
                                    args['message'] = 'Taxon successfully moved'
                                else:
                                    args['success'] = False
                                    args['message'] = 'Taxon has not been moved. Contact the server administrator.'
                                return render(request, 'taxon/move.html', args)

                            except Exception as exp:
                                experimentbase_logger.error('Error move taxon:' + str(exp))
                                args['success'] = False
                                args['message'] = 'Taxon move problem. Contact the server administrator. '
                                return render(request, 'taxon/move.html', args)
                    args['success'] = False
                    args['message'] = 'No such taxon parent found'
                    return render(request, 'taxon/move.html', args)
                except Exception as e:
                    experimentbase_logger.error('Error add taxon:' + str(e))
                    args['success'] = False
                    args['message'] = 'API access problem. Contact the server administrator.'
                    return render(request, 'taxon/move.html', args)
            else:
                return render(request, 'taxon/move.html', args)
        else:
            return render(request, 'reg/403.html', args)
    else:
        return redirect('login')


def taxon_move(request):
    return redirect('taxons')


def taxon_delete_id(request, taxon_id):
    args = dict()
    # Terrible
    args = check_auth_user(request, args)
    args.update(csrf(request))
    if request.user.is_authenticated:
        if request.user.is_staff:
            args['taxon_id'] = taxon_id

            try:
                args['taxon_name'] = requests.get(API_URL + '/taxa', params={'id': taxon_id}).json()['value'][
                    'name']
            except Exception as e:
                experimentbase_logger.error('Error delete taxon, getting taxon_name :' + str(e))
                args['success'] = False
                args['message'] = 'API access problem. Contact the server administrator.'
                return render(request, 'taxon/delete.html', args)

            if request.POST:
                if request.POST['delete']:
                    try:
                        headers = {'Content-Type': 'application/json'}
                        req = requests.post(API_URL + '/taxa/delete',
                                         data=json.dumps({'id': taxon_id}),
                                         headers=headers,
                                         auth=('docker_admin', '123qweasdzxc'))
                        if req.status_code == 200:
                            args['success'] = True
                            args['message'] = 'Taxon deleted successfully'
                        else:
                            args['success'] = False
                            args['message'] = 'Taxon has not been deleted. Contact the server administrator.'
                        return render(request, 'taxon/delete.html', args)
                    except Exception as e:
                        experimentbase_logger.error('Error delete taxon, getting taxon_name :' + str(e))
                        args['success'] = False
                        args['message'] = 'API access problem. Contact the server administrator.'
                        return render(request, 'taxon/delete.html', args)
            else:
                return render(request, 'taxon/delete.html', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def taxon_delete(request):
    return redirect('taxons')


# @csrf_exempt
def searh_file(request, experiment_id):
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
    try:
        args = requests.get(API_URL + '/experiments', params={'id': experiment_id}).json()['value']
        # args = translate_experiments([args]).pop(0)
        args = check_auth_user(request, args)
        args['experiment_id'] = experiment_id
    except Exception as e:
        experimentbase_logger.error('Experiment error:' + str(e))
        args = {}
    return render(request, 'experiment.html', args)


def experiment_add(request):
    args = dict()
    args = check_auth_user(request, args)
    args.update(csrf(request))
    if request.user.is_authenticated:
        if request.user.is_staff:
            if request.method == 'POST':
                try:
                    data = json.loads(request.body)
                except ValueError as e:
                    experimentbase_logger.error('JSON parse error: ' + str(e))
                    args['success'] = False
                    args['message'] = 'Incorrect request form.'
                    return render(request, 'experiment/add.html', args)
                info_dict = check_experiments_data(data)
                if not info_dict['error']:
                    try:
                        headers = {'Content-Type': 'application/json'}
                        req = requests.post(API_URL + '/experiments/add', data=json.dumps(data),
                                            headers=headers,
                                            auth=('docker_admin', '123qweasdzxc'))
                        if req.status_code == 200:
                            info_dict['success'] = 'Experiment added successfully'
                        else:
                            info_dict['error'].append('Incorrect form data.')
                    except Exception as e:
                        info_dict['error'].append('API access problem. Contact the server administrator.')
                        experimentbase_logger.error('Problems with API')
                # return JsonResponse(json.dumps(info_dict))
                return JsonResponse(info_dict)
            else:
                return render(request, 'experiment/add.html', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))


def create_random_str(size):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))


def experiment_download(request):

    if request.POST:
        try:
            experiments_list = json.loads(request.POST['experiments'])['experiments']

            folder = create_random_str(16)
            os.mkdir('/tmp/' + folder)

            for counter, el in enumerate(experiments_list):
                os.mkdir('/tmp/' + folder + '/experiment' + str(counter))

                i = 0
                while i < int(el['quantity']):
                    req = requests.get(API_URL + '/experiments', params={'id': el['id']})
                    value = req.json()['value']
                    torrent_path = value['fileInfos'][i]['torrentFilePath']
                    file_name = os.path.basename(value['fileInfos'][i]['filepath'])

                    req = requests.get(API_URL + '/experiments/getTorrent', params={'torrentPath': torrent_path})
                    torrent_file = base64.b64decode(req.json()['value'])

                    f1 = open('/tmp/' + folder + '/experiment' + str(counter) + '/' + file_name + str(i) + '.torrent', 'wb')
                    f1.write(torrent_file)
                    f1.close()

                    i += 1

            path_to_archive = '/tmp/experiment_torrents_' + folder + '.zip'

            zipf = zipfile.ZipFile(path_to_archive, 'w', zipfile.ZIP_DEFLATED)
            zipdir('/tmp/' + folder, zipf)
            zipf.close()

            archive = open(path_to_archive, 'rb').read()
            response = HttpResponse(archive)

            response['status_code'] = 200
            response['Content-Type'] = 'application/zip'
            response['Content-Length'] = os.path.getsize(path_to_archive)
            response['Content-Disposition'] = "attachment; filename=experiment_torrents.zip"

            os.remove(path_to_archive)
            shutil.rmtree('/tmp/' + folder)

            return response

        except Exception as e:
            experimentbase_logger.error('Creation zip archive error: ' + str(e))
            return JsonResponse({'error': 'cant create archive'})

    return render(request, '', {})


def experiment_change(request, experiment_id):
    args = dict()
    args = check_auth_user(request, args)
    args.update(csrf(request))
    if request.user.is_authenticated:
        if request.user.is_staff:
            # get experiment fields and set them to inputs
            try:
                req = requests.get(API_URL + '/experiments', params={'id': experiment_id})
                args['experiment'] = req.json()['value']

                # get taxon_name from taxon_id
                req = requests.get(API_URL + '/taxa', params={'id': args['experiment']['taxonId']})
                args['experiment']['taxon_name'] = req.json()['value']['name']

                # get date from datetime - minus 9 symbols(' 00:00:00')
                args['experiment']['withdrawDate'] = args['experiment']['withdrawDate'][:-9]
            except Exception as e:
                experimentbase_logger.error('Incorrect experiment id or troubles with API ' + str(e))
                args['success'] = False
                args['message'] = 'Incorrect experiment id or troubles with API.'

            if request.method == 'POST':
                try:
                    data = json.loads(request.body)
                except ValueError as e:
                    experimentbase_logger.error('JSON parse error: ' + str(e))
                    args['success'] = False
                    args['message'] = 'Incorrect request form.'
                    return render(request, 'experiment/change.html', args)
                info_dict = check_experiments_data(data)
                if not info_dict['error']:
                    try:
                        data['id'] = experiment_id
                        headers = {'Content-Type': 'application/json'}
                        req = requests.post(API_URL + '/experiments/edit', params={'id': experiment_id}, data=json.dumps(data),
                                            headers=headers,
                                            auth=('docker_admin', '123qweasdzxc'))
                        if req.status_code == 200:
                            info_dict['success'] = 'Experiment succesfully changed'
                        else:
                            info_dict['error'].append('Incorrect form data')
                    except Exception as e:
                        info_dict['error'].append('API access problem. Contact the server administrator.')
                        experimentbase_logger.error('Problems with API')
                # return JsonResponse(json.dumps(info_dict))
                return JsonResponse(info_dict)
            else:
                return render(request, 'experiment/change.html', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def experiment_delete(request, experiment_id):
    args = dict()
    args = check_auth_user(request, args)
    args.update(csrf(request))
    if request.user.is_authenticated:
        if request.user.is_staff:
            args['experiment_id'] = experiment_id
            try:
                args['experiment_name'] = requests.get(API_URL + '/experiments', params={'id': experiment_id}).json()[
                    'value']['name']
            except Exception as e:
                experimentbase_logger.error('Error delete experiment, getting experiment_name :' + str(e))
                args['success'] = False
                args['message'] = 'API access problem. Contact the server administrator.'
                return render(request, 'experiment/delete.html', args)
            if request.POST:
                try:
                    headers = {'Content-Type': 'application/json'}
                    req = requests.post(API_URL + '/experiments/delete',
                                        data=json.dumps({'id': experiment_id}),
                                        headers=headers,
                                        auth=('docker_admin', '123qweasdzxc'))
                    if req.status_code == 200:
                        args['success'] = True
                        args['message'] = 'Experiment deleted successfully'
                    else:
                        args['success'] = False
                        args['message'] = 'Experiment has not been deleted. Contact the server administrator.'
                    return render(request, 'experiment/delete.html', args)
                except Exception as e:
                    experimentbase_logger.error('error delete experiment:' + str(e))
                    args['success'] = False
                    args['message'] = 'API access problem. Contact the server administrator.'
                    return render(request, 'experiment/delete.html', args)
            else:
                return render(request, 'experiment/delete.html', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


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
    if request.POST:
        args.update(csrf(request))
        search_dict = dict()

        args['filled_fields'] = dict()
        for key, value in request.POST.items():
            if request.POST[key] and request.POST[key] != '':
                args['filled_fields'][key] = value

        if not request.POST['experimentName'] == '':
            search_dict['name'] = request.POST['experimentName']

        args['error'] = dict()
        if not request.POST['taxonSearchName'] == '':
            try:
                all_taxons = requests.get(API_URL + '/taxa/all').json()['value']
                found = False
                for real_taxon in all_taxons:
                        if real_taxon['name'] == request.POST['taxonSearchName']:
                            search_dict['taxonIds'] = [real_taxon['id']]
                            found = True
                            break
                if not found:
                    args['error'] = 'Invalid taxon name'
            except Exception as e:
                args['error'] = 'API access problem. Contact the server administrator'
                experimentbase_logger.error('Problems with API or parse JSON ' + str(e))

        # Ways of life
        search_dict['waysOfLife'] = []
        if request.POST.get('diurnalWayCheckbox', False):
            search_dict['waysOfLife'].append('DIURNAL')

        if request.POST.get('nocturnalWayCheckbox', False):
            search_dict['waysOfLife'].append('NOCTURNAL')

        if request.POST.get('twilightWayCheckbox', False):
            search_dict['waysOfLife'].append('TWILIGHT')

        if request.POST.get('otherWayCheckbox', False):
            search_dict['waysOfLife'].append('OTHER')

        # Habitat
        search_dict['habitats'] = []
        if request.POST.get('wildHabitatCheckbox', False):
            search_dict['habitats'].append('WILD')

        if request.POST.get('laboratoryHabitatCheckbox', False):
            search_dict['habitats'].append('LABORATORY')

        if request.POST.get('farmHabitatCheckbox', False):
            search_dict['habitats'].append('FARM')

        if request.POST.get('otherHabitatCheckbox', False):
            search_dict['habitats'].append('OTHER')

        # Gender
        search_dict['genders'] = []
        if request.POST.get('maleGenderCheckbox', False):
            search_dict['genders'].append('MALE')

        if request.POST.get('femaleGenderCheckbox', False):
            search_dict['genders'].append('FEMALE')

        if request.POST.get('otherGenderCheckbox', False):
            search_dict['genders'].append('OTHER')

        # Age
        if request.POST['ageFrom'] == '':
            search_dict['ageFrom'] = 'null'
        else:
            search_dict['ageFrom'] = request.POST['ageFrom']

        if request.POST['ageTo'] == '':
            search_dict['ageTo'] = 'null'
        else:
            search_dict['ageTo'] = request.POST['ageTo']

        # Weight
        if request.POST['weightFrom'] == '':
            search_dict['weightFrom'] = 'null'
        else:
            search_dict['weightFrom'] = request.POST['weightFrom']

        if request.POST['weightTo'] == '':
            search_dict['weightTo'] = 'null'
        else:
            search_dict['weightTo'] = request.POST['weightTo']

        # Length
        if request.POST['lengthFrom'] == '':
            search_dict['lengthFrom'] = 'null'
        else:
            search_dict['lengthFrom'] = request.POST['lengthFrom']

        if request.POST['lengthTo'] == '':
            search_dict['lengthTo'] = 'null'
        else:
            search_dict['lengthTo'] = request.POST['lengthTo']

        # Environmental factors
        if not request.POST['environmentalFactors'] == '':
            search_dict['environmentalFactors'] = [request.POST['environmentalFactors']]

        # Diseases
        if not request.POST['diseases'] == '':
            search_dict['diseases'] = [request.POST['diseases']]

        # Withdraw place
        if not request.POST['withdrawPlace'] == '':
            search_dict['withdrawPlace'] = request.POST['withdrawPlace']

        # Withdraw date
        if request.POST['withdrawDateFrom'] != '':
            #     search_dict['withdrawDateFrom'] = 'null'
            # else:
            search_dict['withdrawDateFrom'] = request.POST['withdrawDateFrom'] + ' 00:00:00'

        if request.POST['withdrawDateTo'] != '':
            #     search_dict['withdrawDateTo'] = 'null'
            # else:
            search_dict['withdrawDateTo'] = request.POST['withdrawDateTo'] + ' 00:00:00'

        # Seconds post mortem
        if request.POST['hoursPostMortemFrom'] == '':
            search_dict['hoursPostMortemFrom'] = 'null'
        else:
            search_dict['hoursPostMortemFrom'] = request.POST['secondsPostMortemFrom']

        if request.POST['hoursPostMortemTo'] == '':
            search_dict['hoursPostMortemTo'] = 'null'
        else:
            search_dict['hoursPostMortemTo'] = request.POST['secondsPostMortemTo']

        # Temperature
        if request.POST['temperatureFrom'] == '':
            search_dict['temperatureFrom'] = 'null'
        else:
            search_dict['temperatureFrom'] = request.POST['temperatureFrom']

        if request.POST['temperatureTo'] == '':
            search_dict['temperatureTo'] = 'null'
        else:
            search_dict['temperatureTo'] = request.POST['temperatureTo']

        # Comments
        if not request.POST['comments'] == '':
            search_dict['comments'] = [request.POST['comments']]

        # Metabolite names
        if not request.POST['metaboliteNames'] == '':
            search_dict['metaboliteNames'] = [request.POST['metaboliteNames']]

        try:
            if not args['error']:
                # args['experiments'] = translate_experiments(experiments_search(search_dict))
                args['experiments'] = experiments_search(search_dict)
            else:
                args['experiments'] = {}
        except Exception as e:
            experimentbase_logger.error('Search error:' + str(e))
            args = {}

    return render(request, 'experiments.html', args)
