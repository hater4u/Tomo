from django.shortcuts import render, redirect
from django.contrib import auth
from django.template.context_processors import csrf
from django.http import HttpResponse, JsonResponse

import requests
import json


def index(request):
    return HttpResponse()


def login(request):

    args = {}
    args.update(csrf(request))

    if request.POST:
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')

        user = auth.authenticate(username=email, password=password)

        if user is not None:
            auth.login(request, user)
            return redirect('taxa')

        else:
            args['login_error'] = 'Пользователь не найден'
            return render(request, 'reg/login.html', args)
    else:
        return render(request, 'reg/login.html', args)


def get_taxon_path(taxon_id):
    hierarchy = list()
    try:
        values = requests.get("http://localhost:8080/api/taxa", params={"id": taxon_id}).json()
        hierarchy.append({"id": taxon_id, "name": values["value"]["name"]})
        parent_id = values["value"]["parentId"]
        while parent_id:
            values = requests.get("http://localhost:8080/api/taxa", params={"id": parent_id}).json()
            parent_name = values["value"]["name"]
            hierarchy.append({"id": parent_id, "name": parent_name})
            parent_id = values["value"]["parentId"]
        return hierarchy
    except Exception:
        print("hierarchy found error")
        return []


def get_taxon_children(taxon_id):
    try:
        return requests.get("http://localhost:8080/api/taxa/byParent", params={"parentId": taxon_id}).json()["value"]
    except Exception:
        print("children found error")
        return []


def experiments_search(search_dict):
    try:
        headers = {'Content-type': 'application/json', 'Content-Encoding': 'utf-8'}
        return requests.post("http://localhost:8080/api/experiments/search",
                             data=json.dumps(search_dict), headers=headers).json()["value"]
    except Exception as e:
        print("experiments found error: " + str(e))
        return []


def translate_experiments(experiments_list):
    way_of_life = {"DIURNAL": "Дневное", "NOCTURNAL": "Ночное", "TWILIGHT": "Сумеречное", "OTHER": "Другое"}
    habitat = {"WILD": "Дикое", "LABORATORY": "Лабораторное", "FARM": "Фермерское", "OTHER": "Другое"}
    gender = {"MALE": "Мужской", "FEMALE": "Женский", "OTHER": "Другое"}

    for el in experiments_list:
        el["wayOfLife"] = way_of_life[el["wayOfLife"]]
        el["habitat"] = habitat[el["habitat"]]
        el["gender"] = gender[el["gender"]]

    return experiments_list


def taxa_id(request, taxon_id):
    args = dict()

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

    return render(request, "taxa.html", args)


def taxa(request):
    return taxa_id(request, "")


def taxa_parent_search(request):
    if request.POST:
        if request.user.is_authenticated:
            if request.user.is_staff:
                parent_name = request.POST['parentName']
                try:
                    all_taxons = requests.get('http://localhost:8080/api/taxa/all').json()['value']
                    print(all_taxons)
                    taxons = []
                    for el in all_taxons:
                        if el['name'].startswith(parent_name):
                            taxons.append(el)
                    print(taxons)
                    return JsonResponse({'value': taxons})
                except Exception as e:
                    print('Taxon search error:' + str(e))
                    return JsonResponse({'value': []})
    else:
        return redirect('taxa')


def taxa_add(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            args = dict()
            args.update(csrf(request))
            return render(request, 'taxa/new.html', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def taxa_rename(request, taxon_id):
    if request.user.is_authenticated:
        if request.user.is_staff:
            args = dict()
            args.update(csrf(request))
            return render(request, 'taxa/rename.html', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def taxa_move(request, taxon_id):
    if request.user.is_authenticated:
        if request.user.is_staff:
            args = dict()
            args.update(csrf(request))
            return render(request, 'taxa/move.html', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def taxa_delete(request, taxon_id):
    if request.user.is_authenticated:
        if request.user.is_staff:
            args = dict()
            args.update(csrf(request))
            return render(request, 'taxa/delete.html', args)
        else:
            return render(request, 'reg/403.html')
    else:
        return redirect('login')


def experiment(request, experiment_id):
    try:
        args = requests.get('http://localhost:8080/api/experiments', params={'id': experiment_id}).json()['value']
        args = translate_experiments([args]).pop(0)
    except Exception as e:
        print('Experiment error:' + str(e))
        args = {}
    return render(request, 'experiment.html', args)


def experiments(request):
    if request.POST:
        args = dict()
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
    else:
        return render(request, "experiments.html", {})
