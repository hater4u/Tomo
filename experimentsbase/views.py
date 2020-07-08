from django.shortcuts import render
from django.template.loader import render_to_string
from django.http import HttpResponse

import requests


# Create your views here.
def index(request):
    return HttpResponse()


def get_taxon_path(taxon_id):
    hierarchy = list()
    try:
        values = requests.get("http://localhost:8080/api/taxa", params={"id": taxon_id}).json()
        parent_id = values["value"]["parentId"]
        while parent_id:
            values = requests.get("http://localhost:8080/api/taxa", params={"id": parent_id}).json()
            parent_name = values["value"]["name"]
            hierarchy.append({"id": parent_id, "name": parent_name})
            parent_id = values["value"]["parentId"]
        return hierarchy
    except Exception:
        print("unknown error")
        return []


def taxa_id(request, taxon_id):
    args = dict()
    hierarchy = get_taxon_path(taxon_id)
    hierarchy.reverse()
    args["hierarchy"] = hierarchy

    return render(request, "taxa.html", args)


def taxa(request):
    return taxa_id(request, "")


def experiments(request):
    return HttpResponse()


def experiments_search(request):
    return HttpResponse()
