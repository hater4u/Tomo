from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.template.context_processors import csrf
from django.core.files.base import ContentFile
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

import random
import string
import csv
import os
import chardet
from datetime import datetime

import logging
from tomo.settings import LOGGING

from experiments_base.models import Taxon, Tissue, Experiment, Prob, ProbMetabolite, MetaboliteName, WithdrawPlace
from experiments_base.models import AnimalBehavior, HabitatNew, GenderNew
from experiments_base.admin import ExperimentAdminForm
from django.forms import inlineformset_factory
from experiments_base.views import get_animal_behavior_list, get_habitat_list, get_genders_list

logging.config.dictConfig(LOGGING)
custom_admin_logger = logging.getLogger('django')


def create_random_str(size):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(size))


def upload_csv(request):
    try:
        folder = "/tmp/"
        if request.FILES['csvFile'].name:
            filename = create_random_str(8) + request.FILES['csvFile'].name
        else:
            return ''

        full_filename = folder + filename
        f_out = open(full_filename, 'wb+')

        file_content = ContentFile(request.FILES['csvFile'].read())

        for chunk in file_content.chunks():
            f_out.write(chunk)
        f_out.close()

        return full_filename
    except Exception as e:
        custom_admin_logger.warning('Upload csv error: ' + str(e))
        return ''


def parse_csv(file_path):
    csv_dict = dict()

    try:
        raw_data = open(file_path, 'rb').read()
        result = chardet.detect(raw_data)
        char_enc = result['encoding']

        with open(file_path, "r", encoding=char_enc) as f_obj:
            reader = csv.reader(f_obj, delimiter=';')

            prob_fields = {3: 'prob_name', 4: 'gender_new', 5: 'month_age', 6: 'hours_post_mortem', 7: 'weight',
                           8: 'sample_weight', 9: 'length', 10: 'temperature', 11: 'comment'}
            for count, row in enumerate(reader):
                if count in [0, 2, 12, 13]:
                    continue
                if count == 1:
                    csv_dict['exp'] = {'experiment_name': row[0], 'tissue': row[1], 'taxon_id': row[2],
                                       'animal_behavior': row[3], 'habitat_new': row[4], 'withdraw_place': row[5],
                                       'withdraw_date': row[6], 'comments': row[7]}
                if count == 3:
                    if len(row) > 8:
                        probs_length = len(row)
                    else:
                        probs_length = 0
                        for el in row:
                            if el == '':
                                break
                            probs_length += 1

                    probs_length -= 1

                    csv_dict['probs_length'] = probs_length
                    csv_dict['probs'] = [{} for p in range(probs_length)]
                    csv_dict['metabolites'] = {}

                if 2 < count < 12:
                    for count_row, r in enumerate(row[1:]):
                        if count_row < probs_length:
                            csv_dict['probs'][count_row][prob_fields[count]] = r

                if count > 13:
                    csv_dict['metabolites'][row[0].strip()] = row[1:probs_length+1]

    except IOError as e:
        custom_admin_logger.error('Parsing file IOError: ' + str(e))
        csv_dict['errors'] = 'Error of writing file. Try again.'
    except ValueError as e:
        custom_admin_logger.error('Parsing file ValueError: ' + str(e) + '\nNot enough columns in table?')
        csv_dict['errors'] = 'Error of parsing file. Quantity of columns < 8. Check your csv file.'

    os.remove(file_path)
    return csv_dict


def get_value_from_field(value, field_type, some_args):

    if field_type == 'str':
        return value

    if field_type == 'bd':
        if value == '':
            return value

        model, search_field = some_args
        search_field = {search_field: value}
        try:
            return model.objects.get(**search_field).pk
        except ObjectDoesNotExist:
            return 0

    if field_type == 'date_time':
        return value.replace('.', '-')

    if field_type == 'number':
        return value.replace(',', '.')


def create_request_dict(csv_dict, token):
    request_data = dict()
    request_data['csrfmiddlewaretoken'] = str(token)

    if csv_dict.get('exp', False):

        exp_fields = {'experiment_name': 'str', 'tissue': 'bd', 'taxon_id': 'bd', 'animal_behavior': 'bd',
                      'habitat_new': 'bd', 'withdraw_place': 'bd', 'withdraw_date': 'date_time', 'comments': 'str'}
        exp_some_data = {'tissue': [Tissue, 'name__iexact'], 'taxon_id': [Taxon, 'taxon_name'],
                         'animal_behavior': [AnimalBehavior, 'animal_behavior__iexact'],
                         'habitat_new': [HabitatNew, 'habitat__iexact'],
                         'withdraw_place': [WithdrawPlace, 'withdraw_place__iexact']}

        data = csv_dict['exp']
        for k, v in exp_fields.items():
            request_data[k] = get_value_from_field(data[k], v, exp_some_data.get(k, []))

        prob_prefix = 'prob_set-'
        prob_length = csv_dict.get('probs_length', 0)
        request_data[prob_prefix + 'TOTAL_FORMS'] = prob_length
        request_data[prob_prefix + 'INITIAL_FORMS'] = 0
        request_data[prob_prefix + 'MIN_NUM_FORMS'] = 0
        request_data[prob_prefix + 'MAX_NUM_FORMS'] = 1000

        prob_fields = {'prob_name': 'str', 'gender_new': 'bd', 'month_age': 'number', 'hours_post_mortem': 'number',
                       'weight': 'number', 'sample_weight': 'number', 'length': 'number', 'temperature': 'number',
                       'comment': 'str'}

        if csv_dict.get('probs', False):

            prob_some_data = {'gender_new': [GenderNew, 'gender__iexact']}

            for counter, p in enumerate(csv_dict['probs']):
                for k, v in prob_fields.items():
                    request_data[prob_prefix + str(counter) + '-' + k] = get_value_from_field(p[k], v,
                                                                                              prob_some_data.get(k, []))

                request_data[prob_prefix + str(counter) + '-probmetabolite_set-__prefix__-id'] = ''
                request_data[prob_prefix + str(counter) + '-probmetabolite_set-__prefix__-prob_id'] = ''
                request_data[prob_prefix + str(counter) + '-probmetabolite_set-__prefix__-metabolite_id'] = ''
                request_data[prob_prefix + str(counter) + '-probmetabolite_set-__prefix__-concentration'] = 0

            if csv_dict.get('metabolites', False):
                meta_length = len(csv_dict['metabolites'])
                i = 0
                while i < prob_length:
                    request_data[prob_prefix + str(i) + '-probmetabolite_set-TOTAL_FORMS'] = meta_length
                    request_data[prob_prefix + str(i) + '-probmetabolite_set-INITIAL_FORMS'] = 0
                    request_data[prob_prefix + str(i) + '-probmetabolite_set-MIN_NUM_FORMS'] = 0
                    request_data[prob_prefix + str(i) + '-probmetabolite_set-MAX_NUM_FORMS'] = 1000
                    i += 1

                meta_some_data = {'metabolite_id': [MetaboliteName, 'metabolite_synonym__iexact']}

                i = 0
                for metabolite_id, concentrations in csv_dict['metabolites'].items():
                    meta_id = get_value_from_field(metabolite_id, 'bd', meta_some_data['metabolite_id'])
                    if meta_id != 0:
                        meta_id = MetaboliteName.objects.get(pk=meta_id).metabolite_id.pk
                    j = 0
                    while j < prob_length:
                        meta_prefix = prob_prefix + str(j) + '-probmetabolite_set-' + str(i)
                        request_data[meta_prefix + '-metabolite_id'] = meta_id
                        request_data[meta_prefix + '-concentration'] = get_value_from_field(concentrations[j],
                                                                                            'number', [])

                        j += 1
                    i += 1

        for k, v in prob_fields.items():
            request_data[prob_prefix + '__prefix__' + '-' + k] = ''

        request_data[prob_prefix + 'empty-probmetabolite_set-TOTAL_FORMS'] = 0
        request_data[prob_prefix + 'empty-probmetabolite_set-INITIAL_FORMS'] = 0
        request_data[prob_prefix + 'empty-probmetabolite_set-MIN_NUM_FORMS'] = 0
        request_data[prob_prefix + 'empty-probmetabolite_set-MAX_NUM_FORMS'] = 1000
        request_data[prob_prefix + 'empty-probmetabolite_set-__prefix__-id'] = ''
        request_data[prob_prefix + 'empty-probmetabolite_set-__prefix__-prob_id'] = ''
        request_data[prob_prefix + 'empty-probmetabolite_set-__prefix__-metabolite_id'] = ''
        request_data[prob_prefix + 'empty-probmetabolite_set-__prefix__-concentration'] = 0

    return request_data


@user_passes_test(lambda u: u.is_superuser, login_url='/admin/login/')
def add_experiment_from_csv(request):
    args = dict()
    args.update(csrf(request))

    if request.POST:
        error = ''
        if request.FILES.get('csvFile', False):
            file_path = upload_csv(request)
            if file_path:
                if os.path.splitext(file_path)[1].lower() == '.csv':
                    csv_dict = parse_csv(file_path)
                    if csv_dict.get('errors', False):
                        error = csv_dict['errors']
                    else:
                        return JsonResponse(create_request_dict(csv_dict, args['csrf_token']))
                else:
                    error = 'Invalid file extension'
            else:
                error = 'File saving error'
        else:
            error = 'File error: void file field ?'
        return JsonResponse({'error': error})
    else:
        return render(request, 'add_experiment_from_csv.html', args)
