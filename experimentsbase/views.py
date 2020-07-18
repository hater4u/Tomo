from django.shortcuts import render, redirect
from django.contrib import auth
from django.template.context_processors import csrf
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User

from tomo.settings import API_URL, SHARED_FILES_DIR

import requests
import json
import os

#TODO delete
from django.views.decorators.csrf import csrf_exempt


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
            args['login_error'] = 'Пользователь не найден'
            return render(request, 'reg/login.html', args)
    else:
        return render(request, 'reg/login.html', args)


def logout(request):
    auth.logout(request)
    return redirect('index')


def check_auth_user(request, args):
    if request.user.is_authenticated:
        args['nickname'] = request.user.get_username()
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
        print('hierarchy found error')
        return []


def get_taxon_children(taxon_id):
    try:
        return requests.get(API_URL + '/taxa/byParent', params={'parentId': taxon_id}).json()['value']
    except Exception:
        print('children found error')
        return []


def experiments_search(search_dict):
    try:
        headers = {'Content-type': 'application/json'}
        return requests.post(API_URL + '/experiments/search',
                             data=json.dumps(search_dict), headers=headers).json()['value']
    except Exception as e:
        print('experiments found error: ' + str(e))
        return []


def check_experiments_data(data_json):
    info_dict = dict()
    info_dict['error'] = []
    fields = {'experimentName': 'Пустое имя эксперимента',
              'taxonSearchName': 'Пустое имя таксона',
              'wayOfLife': 'Пустое значение поля "Образ жизни"',
              'habitat': 'Пустое значение поля "Ареал обитания"',
              'gender': 'Пустое значение поля "Пол"',
              'monthsAge': 'Пустое значение поля "Возраст"',
              'weight': 'Пустое значение поля "Вес"',
              'length': 'Пустое значение поля "Длина"',
              'withdrawDate': 'Пустое значение поля "Дата забора"',
              # 'withdrawPlace': 'Пустое значение поля ""',
              'hoursPostMortem': 'Пустое значение поля "Время после смерти"',
              'temperature': 'Пустое значение поля "Температура"',
              }
    for key, value in fields.items():
        if data_json.get(key, False):
            if data_json[key] == '':
                info_dict['error'].append(value)
        else:
            info_dict['error'].append('Отсутствует поле ' + key)

    try:
        all_taxons = requests.get(API_URL + '/taxa/all').json()['value']
        found = False
        for el in all_taxons:
            if el['name'] == data_json['taxonSearchName']:
                data_json['taxonId'] = el['id']
                found = True
                break
        if not found:
            info_dict['error'] = ['Неверное имя таксона']

            return info_dict
    except Exception as e:
        info_dict['error'] = ['Проблема доступа к API. Обратитесь к администратору сервера']
        return info_dict

    fields_lists = {
        'environmentalFactors': 'Пустое значение в полях "Факторы среды"',
        'diseases': 'Пустое значение в полях "Заболевания"',
        'comments': 'Пустое значение в полях "Комментарии"',
        'filepaths': 'Пустое значение в полях "Пути файлов"',
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
                    info_dict['error'].append('Пустое значение ключа в доп. свойствах')
                if value == '':
                    info_dict['error'].append('Пустое значение ' + key + ' в доп. свойствах')

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
                    info_dict['error'].append('Отсутствует поле ' + field + ' в метаболите')
                    empty_field = True
            if not empty_field:
                for field in metabolit_fields:
                    if el[field] == '':
                        info_dict['error'].append('Пустое значение ' + field + ' в метаболите')

        for el in data_json['metabolites']:
            el['name'] = el['metaName']
            el.pop('metaName', None)

    if data_json.get('csrfmiddlewaretoken', False):
        data_json.pop('csrfmiddlewaretoken', None)

    if data_json.get('taxonSearchName', False):
        data_json.pop('taxonSearchName', None)

    #  TODO delete fix
    # if data_json.get('hoursPostMortem', False):
    #     data_json['secondsPostMortem'] = data_json['hoursPostMortem']
    #     data_json.pop('hoursPostMortem', None)
    #
    # if data_json.get('monthsAge', False):
    #     data_json['daysAge'] = data_json['monthsAge']
    #     data_json.pop('monthsAge', None)

    # File paths
    if data_json.get('withdrawDate', False):
        data_json['withdrawDate'] += " 00:00:00"
    if data_json.get('experimentName', False):
        data_json['name'] = data_json['experimentName']
        data_json.pop('experimentName', None)

    return info_dict


def translate_experiments(experiments_list):
    way_of_life = {'DIURNAL': 'Дневное', 'NOCTURNAL': 'Ночное', 'TWILIGHT': 'Сумеречное', 'OTHER': 'Другое'}
    habitat = {'WILD': 'Дикое', 'LABORATORY': 'Лабораторное', 'FARM': 'Фермерское', 'OTHER': 'Другое'}
    gender = {'MALE': 'Мужской', 'FEMALE': 'Женский', 'OTHER': 'Другое'}

    for el in experiments_list:
        el['wayOfLife'] = way_of_life[el['wayOfLife']]
        el['habitat'] = habitat[el['habitat']]
        el['gender'] = gender[el['gender']]

    return experiments_list


def taxons_id(request, taxon_id):
    args = dict()
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

    args['experiments'] = translate_experiments(experiments_dict)

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
            print('Taxon search error:' + str(e))
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
                    args['message'] = 'Пустое имя нового таксона'
                    return render(request, 'taxon/new.html', args)

                try:
                    all_taxons = requests.get(API_URL + '/taxa/all').json()['value']
                    all_taxons.append({'name': '', 'id': ''})
                    print(all_taxons)
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
                                    args['message'] = 'Таксон успешно добавлен'
                                else:
                                    args['success'] = False
                                    args['message'] = 'Таксон не был добавлен. Обратитесь к администратору сервера.'
                                return render(request, 'taxon/new.html', args)

                            except Exception as exp:
                                print('Error add taxon:' + str(exp))
                                args['success'] = False
                                args['message'] = 'Проблема с добавлением таксона. Обратитесь к администратору сервера.'
                                return render(request, 'taxon/new.html', args)
                    args['success'] = False
                    args['message'] = 'Такой таксон-родитель не найден'
                    return render(request, 'taxon/new.html', args)
                except Exception as e:
                    print('Error add taxon:' + str(e))
                    args['success'] = False
                    args['message'] = 'Проблема доступа API. Обратитесь к администратору сервера.'
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
            if request.POST:
                if request.POST['taxonName'] == '':
                    args['success'] = False
                    args['message'] = 'Пустое имя таксона'
                    return render(request, 'taxon/rename.html', args)

                try:
                    headers = {'Content-Type': 'application/json'}
                    if requests.post(API_URL + '/taxa/rename',
                                     data=json.dumps({'id': taxon_id, 'name': request.POST['taxonName']}),
                                     headers=headers,
                                     auth=('docker_admin', '123qweasdzxc')).status_code == 200:
                        args['success'] = True
                        args['message'] = 'Имя таксона успешно изменено'
                    else:
                        args['success'] = False
                        args['message'] = 'Имя таксона не было изменено. Обратитесь к администратору сервера.'
                    return render(request, 'taxon/rename.html', args)
                except Exception as e:
                    print('Error rename taxon:' + str(e))
                    args['success'] = False
                    args['message'] = 'Проблема доступа API. Обратитесь к администратору сервера.'
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
                print('Error move taxon, getting taxon_parent_id :' + str(e))
                args['success'] = False
                args['message'] = 'Проблема доступа API. Обратитесь к администратору сервера.'
                return render(request, 'taxon/move.html', args)

            if request.POST:
                try:
                    all_taxons = requests.get(API_URL + '/taxa/all').json()['value']
                    all_taxons.append({'name': '', 'id': ''})
                    print(all_taxons)
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
                                    args['message'] = 'Таксон успешно перемещен'
                                else:
                                    args['success'] = False
                                    args['message'] = 'Таксон не был перемещен. Обратитесь к администратору сервера.'
                                return render(request, 'taxon/move.html', args)

                            except Exception as exp:
                                print('Error move taxon:' + str(exp))
                                args['success'] = False
                                args['message'] = 'Проблема с перемещением таксона. Обратитесь к администратору ' \
                                                  'сервера. '
                                return render(request, 'taxon/move.html', args)
                    args['success'] = False
                    args['message'] = 'Такой таксон-родитель не найден'
                    return render(request, 'taxon/move.html', args)
                except Exception as e:
                    print('Error add taxon:' + str(e))
                    args['success'] = False
                    args['message'] = 'Проблема доступа API. Обратитесь к администратору сервера.'
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
                print('Error delete taxon, getting taxon_name :' + str(e))
                args['success'] = False
                args['message'] = 'Проблема доступа API. Обратитесь к администратору сервера.'
                return render(request, 'taxon/delete.html', args)

            if request.POST:
                if request.POST['delete']:
                    try:
                        if requests.post(API_URL + '/taxa/delete', data={'id': taxon_id},
                                         auth=('docker_admin', '123qweasdzxc')).status_code == 200:
                            args['success'] = True
                            args['message'] = 'Таксон успешно удалён'
                        else:
                            args['success'] = False
                            args['message'] = 'Таксон не был удалён. Обратитесь к администратору сервера.'
                        return render(request, 'taxon/delete.html', args)
                    except Exception as e:
                        print('Error delete taxon, getting taxon_name :' + str(e))
                        args['success'] = False
                        args['message'] = 'Проблема доступа API. Обратитесь к администратору сервера.'
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
                    return JsonResponse({'error': 'Некорректный путь'})

                if path.find('..') != -1:
                    return JsonResponse({'error': 'Путь содержит запрещённые символы'})

                try:
                    path = os.path.abspath(os.getcwd() + "/" + SHARED_FILES_DIR + '/' + path)
                    print(path)
                    print(os.listdir(path))
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
                    return JsonResponse({'error': 'Файл не найден'})

            else:
                return redirect('index')
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def experiment(request, experiment_id):
    try:
        args = requests.get(API_URL + '/experiments', params={'id': experiment_id}).json()['value']
        args = translate_experiments([args]).pop(0)
        args = check_auth_user(request, args)
        args['experiment_id'] = experiment_id
    except Exception as e:
        print('Experiment error:' + str(e))
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
                    print('JSON parse error: ' + str(e))
                    args['success'] = False
                    args['message'] = 'Некорректная форма запроса.'
                    return render(request, 'experiment/add.html', args)
                info_dict = check_experiments_data(data)
                if not info_dict['error']:
                    try:
                        headers = {'Content-Type': 'application/json'}
                        req = requests.post(API_URL + '/experiments/add', data=json.dumps(data),
                                            headers=headers,
                                            auth=('docker_admin', '123qweasdzxc'))
                        if req.status_code == 200:
                            info_dict['success'] = 'Эксперимент успешно добавлен'
                        else:
                            info_dict['error'].append('Некорректные данные формы')
                    except Exception as e:
                        info_dict['error'].append('Проблема доступа API. Обратитесь к администратору сервера.')
                # return JsonResponse(json.dumps(info_dict))
                return JsonResponse(info_dict)
            else:
                return render(request, 'experiment/add.html', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


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
                print('Uncorrect experiment id or troubles with api ' + str(e))
                args['success'] = False
                args['message'] = 'Некорректный id эксперимента или проблемы с доступом к API.'

            if request.method == 'POST':
                try:
                    data = json.loads(request.body)
                except ValueError as e:
                    print('JSON parse error: ' + str(e))
                    args['success'] = False
                    args['message'] = 'Некорректная форма запроса.'
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
                            info_dict['success'] = 'Эксперимент успешно изменён'
                        else:
                            info_dict['error'].append('Некорректные данные формы')
                    except Exception as e:
                        info_dict['error'].append('Проблема доступа API. Обратитесь к администратору сервера.')
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
                print('Error delete experiment, getting experiment_name :' + str(e))
                args['success'] = False
                args['message'] = 'Проблема доступа API. Обратитесь к администратору сервера.'
                return render(request, 'experiment/delete.html', args)
            if request.POST:
                try:
                    if requests.post(API_URL + '/experiments/delete', data={'id': experiment_id},
                                     auth=('docker_admin', '123qweasdzxc')).status_code == 200:
                        args['success'] = True
                        args['message'] = 'Эксперимент успешно удалён'
                    else:
                        args['success'] = False
                        args['message'] = 'Эксперимент не был удалён. Обратитесь к администратору сервера.'
                    return render(request, 'experiment/delete.html', args)
                except Exception as e:
                    print('error delete experiment:' + str(e))
                    args['success'] = False
                    args['message'] = 'Проблема доступа API. Обратитесь к администратору сервера.'
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
        torrent_file = req.json()['value']

        response = HttpResponse(torrent_file)

        response['status_code'] = 200
        response['Content-Type'] = 'application/x-bittorrent'
        response['Content-Length'] = str(len(torrent_file))
        response['Content-Disposition'] = "attachment; filename=" + os.path.basename(torrent_path)

        return response

    except Exception as e:
        print("getting torrent error")
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
                    args['error'] = 'Неверное имя таксона'
            except Exception as e:
                args['error'] = 'Проблема доступа к API. Обратитесь к администратору сервера'
                print('exception ' + str(e))

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
                args['experiments'] = translate_experiments(experiments_search(search_dict))
            else:
                args['experiments'] = {}
        except Exception as e:
            print('Search error:' + str(e))
            args = {}

    return render(request, 'experiments.html', args)
