from django.shortcuts import render, redirect
from django.contrib import auth
from django.template.context_processors import csrf
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User

from tomo.settings import API_URL

import requests
import json


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
        values = requests.get(API_URL + "/taxa", params={"id": taxon_id}).json()
        hierarchy.append({"id": taxon_id, "name": values["value"]["name"]})
        parent_id = values["value"]["parentId"]
        while parent_id:
            values = requests.get(API_URL + "/taxa", params={"id": parent_id}).json()
            parent_name = values["value"]["name"]
            hierarchy.append({"id": parent_id, "name": parent_name})
            parent_id = values["value"]["parentId"]
        return hierarchy
    except Exception:
        print("hierarchy found error")
        return []


def get_taxon_children(taxon_id):
    try:
        return requests.get(API_URL + "/taxa/byParent", params={"parentId": taxon_id}).json()["value"]
    except Exception:
        print("children found error")
        return []


def experiments_search(search_dict):
    try:
        headers = {'Content-type': 'application/json'}
        return requests.post(API_URL + "/experiments/search",
                             data=json.dumps(search_dict), headers=headers).json()["value"]
    except Exception as e:
        print("experiments found error: " + str(e))
        return []


def parse_experiments_data(request):
    experiments_dict = dict()
    experiments_dict['name'] = request.POST['experimentName']

    experiments_dict['taxonId'] = ''
    try:
        all_taxons = requests.get(API_URL + '/taxa/all').json()['value']
        for el in all_taxons:
            if el['name'] == request.POST['taxonName']:
                experiments_dict['taxonId'] = el['id']
    except Exception as e:
        experiments_dict['API_error'] = 'Parse error:' + str(e)
        return experiments_dict

    # Ways of life
    experiments_dict['wayOfLife'] = request.POST.get('wayOfLife', False)

    # Habitat
    experiments_dict['habitat'] = request.POST.get('habitat', False)

    # Gender
    experiments_dict['gender'] = request.POST.get('gender', False)

    # Age TODO:fix
    experiments_dict['monthsAge'] = request.POST.get('monthsAge', -1)

    # Weight
    experiments_dict['weight'] = request.POST.get('weight', -1)

    # Length
    experiments_dict['length'] = request.POST.get('length', -1)

    # Environmental factors
    if not request.POST["environmentalFactors"] == "":
        experiments_dict["environmentalFactors"] = [request.POST["environmentalFactors"]]

    # Diseases
    if not request.POST["diseases"] == "":
        experiments_dict["diseases"] = [request.POST["diseases"]]

    # Withdraw place
    if not request.POST["withdrawPlace"] == "":
        experiments_dict["withdrawPlace"] = request.POST["withdrawPlace"]

    # Withdraw date
    if request.POST["withdrawDateFrom"] != "":
        #     search_dict["withdrawDateFrom"] = "null"
        # else:
        experiments_dict["withdrawDateFrom"] = request.POST["withdrawDateFrom"] + " 00:00:00"

    if request.POST["withdrawDateTo"] != "":
        #     search_dict["withdrawDateTo"] = "null"
        # else:
        experiments_dict["withdrawDateTo"] = request.POST["withdrawDateTo"] + " 00:00:00"

    # Seconds post mortem
    if request.POST["secondsPostMortemFrom"] == "":
        experiments_dict["secondsPostMortemFrom"] = "null"
    else:
        experiments_dict["secondsPostMortemFrom"] = request.POST["secondsPostMortemFrom"]

    if request.POST["secondsPostMortemTo"] == "":
        experiments_dict["secondsPostMortemTo"] = "null"
    else:
        experiments_dict["secondsPostMortemTo"] = request.POST["secondsPostMortemTo"]

    # Temperature
    if request.POST["temperatureFrom"] == "":
        experiments_dict["temperatureFrom"] = "null"
    else:
        experiments_dict["temperatureFrom"] = request.POST["temperatureFrom"]

    if request.POST["temperatureTo"] == "":
        experiments_dict["temperatureTo"] = "null"
    else:
        experiments_dict["temperatureTo"] = request.POST["temperatureTo"]

    # Comments
    if not request.POST["comments"] == "":
        experiments_dict["comments"] = [request.POST["comments"]]

    # Metabolite names
    if not request.POST["metaboliteNames"] == "":
        experiments_dict["metaboliteNames"] = [request.POST["metaboliteNames"]]
    return experiments_dict


def translate_experiments(experiments_list):
    way_of_life = {"DIURNAL": "Дневное", "NOCTURNAL": "Ночное", "TWILIGHT": "Сумеречное", "OTHER": "Другое"}
    habitat = {"WILD": "Дикое", "LABORATORY": "Лабораторное", "FARM": "Фермерское", "OTHER": "Другое"}
    gender = {"MALE": "Мужской", "FEMALE": "Женский", "OTHER": "Другое"}

    for el in experiments_list:
        el["wayOfLife"] = way_of_life[el["wayOfLife"]]
        el["habitat"] = habitat[el["habitat"]]
        el["gender"] = gender[el["gender"]]

    return experiments_list


def taxons_id(request, taxon_id):
    args = dict()
    args["taxon_id"] = taxon_id
    hierarchy = get_taxon_path(taxon_id)
    hierarchy.reverse()
    args["hierarchy"] = hierarchy
    args["children"] = get_taxon_children(taxon_id)

    if taxon_id == "":
        experiments_dict = []
    else:
        search_dict = {"taxonIds": [taxon_id]}
        experiments_dict = experiments_search(search_dict)

    args["experiments"] = translate_experiments(experiments_dict)

    args = check_auth_user(request, args)

    return render(request, "taxons.html", args)


def taxons(request):
    return taxons_id(request, "")


def taxon_parent_search(request):
    if request.POST:
        if request.user.is_authenticated:
            if request.user.is_staff:
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
                if request.POST["taxonName"] == "":
                    args['success'] = False
                    args['message'] = 'Пустое имя таксона'
                    return render(request, 'taxon/rename.html', args)

                try:
                    headers = {'Content-Type': 'application/json'}
                    if requests.post(API_URL + "/taxa/rename",
                                     data=json.dumps({"id": taxon_id, "name": request.POST['taxonName']}),
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
            args["taxon_id"] = taxon_id
            try:
                values = requests.get(API_URL + '/taxa',
                                      params={'id': taxon_id}).json()['value']
                args['taxon_name'] = values['name']
                if values['parentId']:
                    args["taxon_parent_name"] = requests.get(API_URL + '/taxa',
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
            args["taxon_id"] = taxon_id

            try:
                args["taxon_name"] = requests.get(API_URL + '/taxa', params={'id': taxon_id}).json()['value'][
                    'name']
            except Exception as e:
                print('Error delete taxon, getting taxon_name :' + str(e))
                args['success'] = False
                args['message'] = 'Проблема доступа API. Обратитесь к администратору сервера.'
                return render(request, 'taxon/delete.html', args)

            if request.POST:
                if request.POST['delete']:
                    try:
                        if requests.post(API_URL + "/taxa/delete", params={"id": taxon_id},
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


def experiment(request, experiment_id):
    try:
        args = requests.get(API_URL + '/experiments', params={'id': experiment_id}).json()['value']
        args = translate_experiments([args]).pop(0)
        args = check_auth_user(request, args)
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
            if request.POST:
                # args['experiment_data'] = \
                # TODO: fix
                args['data'] = parse_experiments_data(request)
                return render(request, 'experiment/add.html', args)
            else:
                # args['success'] = False
                # args['message'] = 'Проблема доступа API. Обратитесь к администратору сервера.'
                return render(request, 'experiment/add.html', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def experiment_change(request, experiment_id):
    return HttpResponse


def experiment_delete(request, experiment_id):
    args = dict()
    args = check_auth_user(request, args)
    args.update(csrf(request))
    if request.user.is_authenticated:
        if request.user.is_staff:
            if request.POST:
                try:
                    if requests.post(API_URL + "/experiments/delete", params={"id": experiment_id},
                                     auth=('docker_admin', '123qweasdzxc')).status_code == 200:
                        args['success'] = True
                        args['message'] = 'Эксперимент успешно удалён'
                    else:
                        args['success'] = False
                        args['message'] = 'Эксперимент не был удалён. Обратитесь к администратору сервера.'
                    return render(request, 'taxon/delete.html', args)
                except Exception as e:
                    print('error delete experiment:' + str(e))
                    return render(request, 'experiment/', args)
            else:
                return render(request, 'experiment/', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def get_torrent(request):
    args = dict()
    args = check_auth_user(request, args)
    args.update(csrf(request))
    if request.user.is_authenticated:
        if request.user.is_staff:
            if request.POST:
                "123"
            else:
                return render(request, 'experiment/', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def experiments(request):
    args = dict()
    args = check_auth_user(request, args)
    if request.POST:
        args.update(csrf(request))
        search_dict = dict()
        if not request.POST["experimentName"] == "":
            search_dict["name"] = request.POST["experimentName"]

        if not request.POST["taxonId"] == "":
            search_dict["taxonIds"] = [request.POST["taxonId"]]

        # Ways of life
        search_dict["waysOfLife"] = []
        if request.POST.get("diurnalWayCheckbox", False):
            search_dict["waysOfLife"].append("DIURNAL")

        if request.POST.get("nocturnalWayCheckbox", False):
            search_dict["waysOfLife"].append("NOCTURNAL")

        if request.POST.get("twilightWayCheckbox", False):
            search_dict["waysOfLife"].append("TWILIGHT")

        if request.POST.get("otherWayCheckbox", False):
            search_dict["waysOfLife"].append("OTHER")

        # Habitat
        search_dict["habitats"] = []
        if request.POST.get("wildHabitatCheckbox", False):
            search_dict["habitats"].append("WILD")

        if request.POST.get("laboratoryHabitatCheckbox", False):
            search_dict["habitats"].append("LABORATORY")

        if request.POST.get("farmHabitatCheckbox", False):
            search_dict["habitats"].append("FARM")

        if request.POST.get("otherHabitatCheckbox", False):
            search_dict["habitats"].append("OTHER")

        # Gender
        # search_dict["gender"] = []
        # if request.POST["maleGenderCheckbox"]:
        #     search_dict["gender"].append("MALE")
        #
        # if request.POST["femaleGenderCheckbox"]:
        #     search_dict["gender"].append("FEMALE")
        #
        # if request.POST["otherGenderCheckbox"]:
        #     search_dict["gender"].append("OTHER")

        # Age
        if request.POST["ageFrom"] == "":
            search_dict["ageFrom"] = "null"
        else:
            search_dict["ageFrom"] = request.POST["ageFrom"]

        if request.POST["ageTo"] == "":
            search_dict["ageTo"] = "null"
        else:
            search_dict["ageTo"] = request.POST["ageTo"]

        # Weight
        if request.POST["weightFrom"] == "":
            search_dict["weightFrom"] = "null"
        else:
            search_dict["weightFrom"] = request.POST["weightFrom"]

        if request.POST["weightTo"] == "":
            search_dict["weightTo"] = "null"
        else:
            search_dict["weightTo"] = request.POST["weightTo"]

        # Length
        if request.POST["lengthFrom"] == "":
            search_dict["lengthFrom"] = "null"
        else:
            search_dict["lengthFrom"] = request.POST["lengthFrom"]

        if request.POST["lengthTo"] == "":
            search_dict["lengthTo"] = "null"
        else:
            search_dict["lengthTo"] = request.POST["lengthTo"]

        # Environmental factors
        if not request.POST["environmentalFactors"] == "":
            search_dict["environmentalFactors"] = [request.POST["environmentalFactors"]]

        # Diseases
        if not request.POST["diseases"] == "":
            search_dict["diseases"] = [request.POST["diseases"]]

        # Withdraw place
        if not request.POST["withdrawPlace"] == "":
            search_dict["withdrawPlace"] = request.POST["withdrawPlace"]

        # Withdraw date
        if request.POST["withdrawDateFrom"] != "":
            #     search_dict["withdrawDateFrom"] = "null"
            # else:
            search_dict["withdrawDateFrom"] = request.POST["withdrawDateFrom"] + " 00:00:00"

        if request.POST["withdrawDateTo"] != "":
            #     search_dict["withdrawDateTo"] = "null"
            # else:
            search_dict["withdrawDateTo"] = request.POST["withdrawDateTo"] + " 00:00:00"

        # Seconds post mortem
        if request.POST["secondsPostMortemFrom"] == "":
            search_dict["secondsPostMortemFrom"] = "null"
        else:
            search_dict["secondsPostMortemFrom"] = request.POST["secondsPostMortemFrom"]

        if request.POST["secondsPostMortemTo"] == "":
            search_dict["secondsPostMortemTo"] = "null"
        else:
            search_dict["secondsPostMortemTo"] = request.POST["secondsPostMortemTo"]

        # Temperature
        if request.POST["temperatureFrom"] == "":
            search_dict["temperatureFrom"] = "null"
        else:
            search_dict["temperatureFrom"] = request.POST["temperatureFrom"]

        if request.POST["temperatureTo"] == "":
            search_dict["temperatureTo"] = "null"
        else:
            search_dict["temperatureTo"] = request.POST["temperatureTo"]

        # Comments
        if not request.POST["comments"] == "":
            search_dict["comments"] = [request.POST["comments"]]

        # Metabolite names
        if not request.POST["metaboliteNames"] == "":
            search_dict["metaboliteNames"] = [request.POST["metaboliteNames"]]

        try:
            args["experiments"] = translate_experiments(experiments_search(search_dict))
        except Exception as e:
            print("Search error:" + str(e))
            args = {}

    return render(request, "experiments.html", args)
