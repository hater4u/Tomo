from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.template.context_processors import csrf
from django.core.files.base import ContentFile
from django.core.exceptions import ObjectDoesNotExist

import random
import string
import csv
import os
import chardet
from datetime import datetime

import logging
from tomo.settings import LOGGING

from experiments_base.models import Taxon, Experiment, Prob, ProbMetabolite, MetaboliteName, WithdrawPlace

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

            prob_fields = {3: 'name', 4: 'gender', 5: 'month_age', 6: 'hours_post_mortem', 7: 'weight', 8: 'length',
                           9: 'temperature', 10: 'comment'}
            for count, row in enumerate(reader):
                if count in [0, 2, 11, 12]:
                    continue
                if count == 1:
                    csv_dict['exp'] = {'name': row[0], 'taxon_name': row[1], 'way_of_life': row[2], 'habitat': row[3],
                                       'withdraw_place': row[4], 'withdraw_date': row[5], 'comments': row[6]}
                if count == 3:
                    if len(row) > 7:
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

                if 2 < count < 11:
                    for count_row, r in enumerate(row[1:]):
                        if count_row < probs_length:
                            csv_dict['probs'][count_row][prob_fields[count]] = r

                if count > 12:
                    csv_dict['metabolites'][row[0]] = row[1:probs_length+1]

    except IOError as e:
        custom_admin_logger.error('Parsing file IOError: ' + str(e))
        csv_dict['errors'] = 'Error of writing file. Try again.'
    except ValueError as e:
        custom_admin_logger.error('Parsing file ValueError: ' + str(e) + '\nNot enough columns in table?')
        csv_dict['errors'] = 'Error of parsing file. Quantity of columns < 7. Check your csv file.'

    os.remove(file_path)
    return csv_dict


def get_name(name):
    return name.replace('_', ' ')


def check_not_empty_field(value):
    return '' if value else 'Invalid {}. Field can not be empty.'


def check_checkbox_field(value, list_of_values):
    if value in list_of_values:
        return ''
    else:
        return 'Field {} has invalid value. Change it.'


def check_db_field(value, model, search_field):

    if model != WithdrawPlace:
        error = check_not_empty_field(value)
        if error:
            return error
    else:
        if value == '':
            return ''

    try:
        model.objects.get(**{search_field: value})
        return ''
    except ObjectDoesNotExist:
        if model == MetaboliteName:
            ref = ', <a href="/admin/experiments_base/metabolite/add">create metabolite</a> or ' \
                  '<a href="/admin/experiments_base/metabolitename/add">add metabolite synonym</a>'
        else:
            ref = ' or <a href="/admin/experiments_base/' + model.__qualname__.lower() + '/add">create</a>.'
        return 'Value of field {} not found in database. Change it in table' + ref


def check_datetime_field(value):
    if value == '':
        return ''

    try:
        datetime.strptime(value, "%d.%m.%y %H:%M")
        return ''
    except ValueError:
        return 'Invalid {}. Check template of datetime field.'


def is_number(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def check_number_field(value, is_int):

    if value == '' or value == 'na':
        return ''
    else:
        value = value.replace(',', '.')
        if is_number(value):
            try:
                value = int(value) if is_int else float(value)
            except ValueError:
                return 'Float number in integer field'
            if value >= 0:
                return ''
            else:
                return 'Negative number'
        else:
            return 'Bad number'


def check_prob_number_field(prob, info_dict, is_int, field_name):

    correct_name = 'correct_' + field_name
    name_error = field_name + '_error'

    try:
        value = prob[field_name]
    except KeyError:
        info_dict[correct_name] = False
        info_dict[name_error] = 'Not found ' + field_name.replace('_', ' ') + '. Check structure of table.'
        return

    check = check_number_field(is_int, value)
    if check:
        info_dict[correct_name] = False
        info_dict[name_error] = check
    else:
        info_dict[correct_name] = True


def write_checking_in_dict(error, info_dict, correct_name, name_error):

    if not error:
        info_dict[correct_name] = True
    else:
        info_dict[correct_name] = False
        info_dict[name_error] = error
    return


def get_function(field_type):
    method_name = 'check_' + field_type + '_field'
    return globals()[method_name]


def check_field(data, field_name, field_type, info_dict, obj_data):
    correct_name = 'correct_' + field_name
    name_error = field_name + '_error'

    if data.get(field_name, False) is False:
        info_dict[correct_name] = False
        info_dict[name_error] = 'Not found ' + field_name.replace('_', ' ') + '. Check structure of table.'
        return

    value = data[field_name]
    args = {'value': value, **obj_data}
    error = get_function(field_type)(**args).format(get_name(field_name))

    write_checking_in_dict(error, info_dict, correct_name, name_error)


def check_metabolite_number_field(concentrations, info_dict):
    info_dict['concentrations'] = []
    for c in concentrations:
        error = check_number_field(c, False)
        if error:
            info_dict['concentrations'].append({'value': c, 'error': error})
        else:
            info_dict['concentrations'].append({'value': c, 'error': False})


def has_errors(csv_info):

    for field in ['name', 'taxon_name', 'way_of_life', 'habitat', 'withdraw_place', 'withdraw_date']:
        if not csv_info['exp']['correct_' + field]:
            return True

    if csv_info['probs_length_exist'] and csv_info['probs_exist']:

        for prob in csv_info['probs']:
            for field in ['gender', 'month_age', 'hours_post_mortem', 'weight', 'length', 'temperature']:
                if not prob['correct_' + field]:
                    return True

        if csv_info['metabolites_exist']:

            for m in csv_info['metabolites']:

                if not m['correct_name']:
                    return True

                for c in m['concentrations']:
                    if c['error'] is not False:
                        return True

    return False


def check_csv_data(csv_dict):
    csv_info = dict()

    for el in ['exp', 'probs_length', 'probs', 'metabolites']:
        csv_info[el + '_exist'] = csv_dict.get(el, False)

    if not (csv_info['exp_exist'] or csv_info['probs_length_exist'] or
            csv_info['probs_exist'] or csv_info['metabolites_exist']):
        return csv_info

    exp = dict()
    fields = {'name': 'not_empty', 'taxon_name': 'db', 'way_of_life': 'checkbox', 'habitat': 'checkbox',
              'withdraw_place': 'db', 'withdraw_date': 'datetime'}
    field_args = {'name': {},
                  'taxon_name': {'model': Taxon, 'search_field': 'taxon_name'},
                  'way_of_life': {'list_of_values': ['', 'diurnal', 'nocturnal', 'twilight', 'other']},
                  'habitat': {'list_of_values': ['', 'wild', 'laboratory', 'farm', 'other']},
                  'withdraw_place': {'model': WithdrawPlace, 'search_field': 'withdraw_place'},
                  'withdraw_date': {}}

    for field_name, field_type in fields.items():
        check_field(csv_dict['exp'], field_name, field_type, exp, field_args[field_name])

    csv_info['exp'] = exp

    if not csv_info['probs_length_exist'] or not csv_info['probs_exist']:
        return csv_info
    probs = []
    fields = {'gender': 'checkbox', 'month_age': 'number', 'hours_post_mortem': 'number', 'weight': 'number',
              'length': 'number', 'temperature': 'number'}
    field_args = {'gender': {'list_of_values': ['', 'male', 'female', 'other']},
                  'month_age': {'is_int': True},
                  'hours_post_mortem': {'is_int': True},
                  'weight': {'is_int': False},
                  'length': {'is_int': False},
                  'temperature': {'is_int': False}}

    for prob in csv_dict['probs']:
        prob_dict = dict()

        for field_name, field_type in fields.items():
            check_field(prob, field_name, field_type, prob_dict, field_args[field_name])
        probs.append(prob_dict)

    csv_info['probs'] = probs

    if not csv_info['metabolites_exist']:
        return csv_info

    metabolites = []
    for meta_name, concentrations in csv_dict['metabolites'].items():
        meta_dict = dict()
        meta_dict['name'] = meta_name

        check_field(meta_dict, 'name', 'db', meta_dict, {'model': MetaboliteName,
                                                         'search_field': 'metabolite_synonym'})
        if meta_dict.get(meta_name + '_error', False):
            meta_dict[meta_name + '_error'] = meta_dict[meta_name + '_error'].replace('metabolitename', 'metabolite')

        check_metabolite_number_field(concentrations, meta_dict)
        metabolites.append(meta_dict)

    csv_info['metabolites'] = metabolites

    csv_info['has_error'] = has_errors(csv_info)
    return csv_info


def write_field_in_template_dict(field_name, t_dict, info_dict, values_dict):

    correct_name = 'correct_' + field_name

    t_dict[field_name] = values_dict[field_name]
    t_dict[correct_name] = info_dict[correct_name]
    if not t_dict[correct_name]:
        t_dict[field_name + '_error'] = info_dict[field_name + '_error']


def update_args_from_csv_info(args, csv_info, csv_dict):

    args['has_error'] = csv_info['has_error']

    if csv_info['exp_exist']:
        e = csv_info['exp']
        de = csv_dict['exp']

        exp = dict()
        for field_name in ['name', 'taxon_name', 'way_of_life', 'habitat', 'withdraw_place', 'withdraw_date']:
            write_field_in_template_dict(field_name, exp, e, de)

        exp['comments'] = de['comments']
        args['exp'] = exp

        if csv_info['probs_length_exist'] and csv_info['probs_exist']:
            dp = csv_dict['probs']
            probs = []

            for c, prob in enumerate(csv_info['probs']):
                p_dict = dict()
                p_dict['prob_name'] = dp[c]['name']
                for field_name in ['gender', 'month_age', 'hours_post_mortem', 'weight', 'length', 'temperature']:
                    write_field_in_template_dict(field_name, p_dict, prob, dp[c])
                p_dict['comment'] = dp[c]['comment']
                probs.append(p_dict)

            args['probs'] = probs

            if csv_info['metabolites_exist']:
                metabolites = []

                for m in csv_info['metabolites']:
                    m_dict = dict()

                    meta_name = m['name']

                    m_dict['name'] = meta_name
                    m_dict['correct'] = m['correct_name']
                    if not m_dict['correct']:
                        m_dict['error'] = m['name_error']

                    m_dict['concentrations'] = m['concentrations']
                    metabolites.append(m_dict)

                args['metabolites'] = metabolites
            else:
                args['warning'] = 'Metabolites not found'
        else:
            args['warning'] = 'Probs not found'

    else:
        args['error'] = 'Invalid structure of table. Second string is data of experiment.'


def create_experiment_dict(exp):
    way_of_life = {'diurnal': 0, 'nocturnal': 1, 'twilight': 2, 'other': 3}
    habitat = {'wild': 0, 'laboratory': 1, 'farm': 2, 'other': 3}

    try:
        exp['experiment_name'] = exp['name']
        exp.pop('name')
        exp['taxon_id'] = Taxon.objects.get(taxon_name=exp['taxon_name'])
        exp.pop('taxon_name')
        if exp['way_of_life']:
            exp['way_of_life'] = way_of_life[exp['way_of_life']]
        else:
            exp.pop('way_of_life')

        if exp['habitat']:
            exp['habitat'] = habitat[exp['habitat']]
        else:
            exp.pop('habitat')

        exp['withdraw_place'] = WithdrawPlace.objects.get(withdraw_place=exp['withdraw_place'])

        if exp['withdraw_date']:
            exp['withdraw_date'] = datetime.strptime(exp['withdraw_date'], "%d.%m.%y %H:%M")
        else:
            exp.pop('withdraw_date')

        if exp['comments']:
            exp['comments'] = exp['comments']
        else:
            exp.pop('comments')

        return ''

    except (ObjectDoesNotExist, KeyError):
        return 'Unidentified error. Please contact with administration.'


def create_prob_dict(prob, exp):
    gender = {'male': 0, 'female': 1, 'other': 2}

    try:
        prob['prob_name'] = prob['name']
        prob.pop('name')
        prob['experiment_id'] = exp

        if prob['gender']:
            prob['gender'] = gender[prob['gender']]
        else:
            prob.pop('gender')

        is_int = {'month_age': True, 'hours_post_mortem': True,
                  'weight': False, 'length': False, 'temperature': False}
        for field, is_int in is_int.items():
            if prob[field] == '':
                prob.pop(field)
            else:
                if prob[field] == 'na':
                    prob[field] = None
                else:
                    with_point = prob[field].replace(',', '.')
                    prob[field] = int(with_point) if is_int else float(with_point)

        if prob['comment']:
            prob['comment'] = prob['comment']
        else:
            prob.pop('comment')

        return ''
    except KeyError:
        return 'Unidentified error in prob' + prob.get('prob_name', '') + '. Please contact with administration.'


def create_prob_metabolites(csv_dict, prob_objs, args):

    metabolites = csv_dict['metabolites']

    for meta_name, concentrations in metabolites.items():
        try:
            m = MetaboliteName.objects.get(metabolite_synonym=meta_name).metabolite_id

            for counter, c in enumerate(concentrations):
                if c == '':
                    continue
                else:
                    if c == 'na':
                        c = None
                    else:
                        c = float(c.replace(',', '.'))
                    prop_metabolite = ProbMetabolite(prob_id=prob_objs[counter], metabolite_id=m, concentration=c)
                    prop_metabolite.save()

        except (ObjectDoesNotExist, KeyError):
            return 'Unidentified error in metabolite' + meta_name + '.Please contact with administration.'

    args['success'] = 'Experiment was successfully created.'
    return ''


def create_probs_and_prob_metabolites(csv_info, csv_dict, exp, args):

    probs = csv_dict['probs']
    prob_objs = []

    for prob in probs:
        error = create_prob_dict(prob, exp)
        if error:
            return error

        p = Prob(**prob)
        p.save()
        prob_objs.append(p)

    if csv_info['probs_length_exist']:
        return create_prob_metabolites(csv_dict, prob_objs, args)
    else:
        args['success'] = 'Experiment without metabolites was successfully created'
        return ''


def create_experiment(csv_info, csv_dict, args):
    e = csv_dict['exp']
    error = create_experiment_dict(e)
    if error:
        return error

    exp = Experiment(**e)
    exp.save()

    if csv_info['probs_length_exist'] and csv_info['probs_exist']:
        return create_probs_and_prob_metabolites(csv_info, csv_dict, exp, args)
    else:
        args['success'] = 'Experiment without probs and metabolites was successfully created'
        return ''


@user_passes_test(lambda u: u.is_superuser, login_url='/admin/login/')
def add_experiment_from_csv(request):
    args = dict()
    args.update(csrf(request))

    if request.POST:
        if request.FILES.get('csvFile', False):
            file_path = upload_csv(request)
            if file_path:
                if os.path.splitext(file_path)[1].lower() == '.csv':
                    csv_dict = parse_csv(file_path)
                    if csv_dict.get('errors', False):
                        args['error'] = csv_dict['errors']
                    else:
                        csv_info = check_csv_data(csv_dict)
                        if request.POST.get('upload', False):
                            if not csv_info['has_error']:
                                error = create_experiment(csv_info, csv_dict, args)
                                if error:
                                    args['error'] = error
                                return render(request, 'add_experiment_from_csv.html', args)
                        update_args_from_csv_info(args, csv_info, csv_dict)
                else:
                    args['error'] = 'Invalid file extension'
            else:
                args['error'] = 'File saving error'
        else:
            args['error'] = 'File error: void file field ?'
    return render(request, 'add_experiment_from_csv.html', args)
