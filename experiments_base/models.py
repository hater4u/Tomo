from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from tomo.settings import SHARED_FILES_DIR, TORRENT_DIR, API_URL, API_AUTH, LOGGING

import os
import requests
import json
import logging

logging.config.dictConfig(LOGGING)
experiments_base_logger = logging.getLogger('django')


def get_full_path(taxon):
    if taxon.parent_id is None:
        return taxon.taxon_folder
    else:
        return get_full_path(taxon.parent_id) + '/' + taxon.taxon_folder


def r_replace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)


class Taxon(models.Model):
    class Meta:
        db_table = 'taxons'
        verbose_name = 'taxon'
        verbose_name_plural = 'taxons'

    taxon_name = models.CharField(max_length=128, verbose_name='Taxon name')
    parent_id = models.ForeignKey('self', null=True, blank=True, verbose_name='Taxon parent',
                                  on_delete=models.DO_NOTHING)
    view_in_popular = models.BooleanField(default=False, verbose_name='Display in popular taxons')
    is_tissue = models.BooleanField(default=False, verbose_name='Tissue')

    taxon_folder = models.CharField(default='old_taxon', max_length=128, verbose_name='Taxon folder')

    def __str__(self):
        if self.parent_id is None:
            parent_name = 'ROOT'
        elif not self.parent_id.taxon_name:
            parent_name = 'ROOT'
        else:
            parent_name = self.parent_id.taxon_name

        name = 'ROOT' if self.taxon_name is None else self.taxon_name
        return '{0} ({1})'.format(name, parent_name)

    def save(self, *args, **kwargs):
        if not self.pk:
            super(Taxon, self).save(*args, **kwargs)
            self.taxon_folder = self.taxon_name + '_' + str(self.pk)
            super(Taxon, self).save(*args, **kwargs)
            full_path = str(SHARED_FILES_DIR) + '/' + get_full_path(self)
            os.mkdir(full_path)

        else:
            old_self = Taxon.objects.get(pk=self.pk)
            old_taxon_folder = old_self.taxon_folder
            full_path_old = str(SHARED_FILES_DIR) + '/' + get_full_path(self)
            self.taxon_folder = self.taxon_name + '_' + str(self.pk)
            # replace with right side 1 occurrence in string - need for security(can be same names of taxons)
            full_path_new = r_replace(full_path_old, old_taxon_folder, self.taxon_folder, 1)

            os.rename(full_path_old, full_path_new)
            super(Taxon, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        experiments = Experiment.objects.filter(taxon_id=self.pk)
        for e in experiments:
            e.delete()

        taxons = Taxon.objects.filter(parent_id=self.pk)
        for t in taxons:
            t.delete()
        super(Taxon, self).delete(*args, **kwargs)


class WayOfLife(models.IntegerChoices):
    DIURNAL = 0, 'diurnal'
    NOCTURNAL = 1, 'nocturnal'
    TWILIGHT = 2, 'twilight'
    OTHER = 3, 'other'


class Habitat(models.IntegerChoices):
    WILD = 0, 'wild'
    LABORATORY = 1, 'laboratory'
    FARM = 2, 'farm'
    OTHER = 3, 'other'


class Gender(models.IntegerChoices):
    MALE = 0, 'male'
    FEMALE = 1, 'female'
    OTHER = 2, 'other'


class EnvironmentalFactor(models.Model):
    class Meta:
        db_table = 'environmental_factors'
        verbose_name = 'environmental factor'
        verbose_name_plural = 'environmental factors'

    factor_name = models.CharField(max_length=256, verbose_name='Environmental factor name')

    def __str__(self):
        return self.factor_name


class Disease(models.Model):
    class Meta:
        db_table = 'diseases'
        verbose_name = 'disease'
        verbose_name_plural = 'diseases'

    disease_name = models.CharField(max_length=256, verbose_name='Disease name')

    def __str__(self):
        return self.disease_name


class WithdrawCondition(models.Model):
    class Meta:
        db_table = 'withdraw_conditions'
        verbose_name = 'withdraw condition'
        verbose_name_plural = 'withdraw conditions'

    withdraw_condition = models.CharField(max_length=256, verbose_name='Withdraw condition')

    def __str__(self):
        return self.withdraw_condition


class WithdrawPlace(models.Model):
    class Meta:
        db_table = 'withdraw_places'
        verbose_name = 'withdraw place'
        verbose_name_plural = 'withdraw places'

    withdraw_place = models.CharField(max_length=256, verbose_name='Withdraw place')

    def __str__(self):
        return self.withdraw_place


class AdditionalProperty(models.Model):
    class Meta:
        db_table = 'additional_properties'
        verbose_name = 'additional property'
        verbose_name_plural = 'additional properties'

    key = models.CharField(max_length=128, verbose_name='Key')
    value = models.CharField(max_length=128, verbose_name='Value')

    def __str__(self):
        return '{}: {}'.format(self.key, self.value)


class Metabolite(models.Model):
    class Meta:
        db_table = 'metabolites'
        verbose_name = 'metabolite'
        verbose_name_plural = 'metabolites'

    metabolite_name = models.CharField(max_length=128, verbose_name='Metabolite name(main)', unique=True)
    pub_chem_cid = models.IntegerField(default=0, blank=True, verbose_name='PubChemCid')
    comment = models.CharField(max_length=1024, verbose_name='Comment', blank=True)

    def __str__(self):
        return self.metabolite_name

    # It need for adding synonym for this metabolite with the same name
    def save(self, *args, **kwargs):
        if not self.pk:
            super(Metabolite, self).save(*args, **kwargs)
            MetaboliteName.objects.create(metabolite_synonym=self.metabolite_name, metabolite_id=self)
        else:
            old_self = Metabolite.objects.get(pk=self.pk)
            metabolite_name = MetaboliteName.objects.get(metabolite_synonym=old_self.metabolite_name)
            metabolite_name.metabolite_synonym = self.metabolite_name
            metabolite_name.save()
            super(Metabolite, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        metabolite_names = MetaboliteName.objects.filter(metabolite_id=self.pk)
        for mn in metabolite_names:
            mn.delete()

        super(Metabolite, self).delete(*args, **kwargs)


# for search one metabolite by different names
class MetaboliteName(models.Model):
    class Meta:
        db_table = 'metabolite_names'
        verbose_name = 'metabolite name'
        verbose_name_plural = 'metabolite names'

    metabolite_synonym = models.CharField(max_length=128, verbose_name='Synonym for main metabolite name')
    metabolite_id = models.ForeignKey('experiments_base.Metabolite',
                                      verbose_name='The metabolite for which we add a synonymous name',
                                      on_delete=models.DO_NOTHING)

    def __str__(self):
        return '{}({})'.format(self.metabolite_synonym, self.metabolite_id.metabolite_name)


class ProbMetabolite(models.Model):
    class Meta:
        db_table = 'prob_metabolites'
        verbose_name = 'prob metabolite'
        verbose_name_plural = 'prob metabolites'

    prob_id = models.ForeignKey('experiments_base.Prob', verbose_name='Prob', on_delete=models.DO_NOTHING)
    metabolite_id = models.ForeignKey('experiments_base.Metabolite', verbose_name='Metabolite',
                                      on_delete=models.DO_NOTHING)
    concentration = models.FloatField(default=0, validators=[MinValueValidator(0)],
                                      verbose_name='Concentration(nmol/g)', null=True, blank=True)

    def __str__(self):
        return '{}({} nmol/g)'.format(self.metabolite_id.metabolite_name, self.concentration)


def stop_torrent(torrent_paths):
    try:
        req = requests.post(API_URL + '/torrent/stop',
                            json=json.dumps({'torrentPaths': torrent_paths}),
                            auth=API_AUTH)
        # maybe need checking answer

    except Exception as e:
        experiments_base_logger.error('Stopping torrent error: ' + str(e))


def start_torrent(torrent_path):
    try:
        file_path = torrent_path.replace(str(SHARED_FILES_DIR) + '/', '')

        headers = {'Content-Type': 'application/json'}
        req = requests.post(API_URL + '/torrents/seed',
                            data=json.dumps({'files': [file_path]}),
                            auth=API_AUTH,
                            headers=headers)

        if req.status_code == 200:
            data = req.json()
            if not data['errors']:
                return data['value'][0].replace('/var/metabolites/torrents/', '')
            else:
                experiments_base_logger.error('Creating torrent error: ' + data['errors'])
                return 'file_error'
        else:
            experiments_base_logger.error('Creating torrent error: ' + req.text)
            return 'file_error'

    except Exception as e:
        experiments_base_logger.error('Creating torrent error: ' + str(e))
        return 'file_error'


class Prob(models.Model):
    class Meta:
        db_table = 'probs'
        verbose_name = 'prob'
        verbose_name_plural = 'probs'

    prob_name = models.CharField(max_length=128, verbose_name='Prob name')
    experiment_id = models.ForeignKey('experiments_base.Experiment', verbose_name='Experiment',
                                      on_delete=models.DO_NOTHING)

    gender = models.IntegerField(default=Gender.OTHER, choices=Gender.choices, verbose_name='Gender', blank=True)

    month_age = models.IntegerField(default=0, validators=[MinValueValidator(0)],
                                    verbose_name='Age(months)', blank=True)
    hours_post_mortem = models.IntegerField(default=0, validators=[MinValueValidator(0)],
                                            verbose_name='Time post mortem(hours)', blank=True)

    weight = models.FloatField(default=0, validators=[MinValueValidator(0)], verbose_name='Weight(kg)', blank=True)
    length = models.FloatField(default=0, validators=[MinValueValidator(0)], verbose_name='Height/length(cm)', blank=True)
    temperature = models.FloatField(default=0, validators=[MinValueValidator(0)],
                                    verbose_name='Temperature(degrees Celsius)', blank=True)

    comment = models.CharField(max_length=1024, verbose_name='Comment', blank=True)

    def get_upload_path(self, file_name):
        return str(SHARED_FILES_DIR) + '/' + \
               get_full_path(self.experiment_id.taxon_id) + '/' + \
               self.experiment_id.experiment_folder + '/' + file_name

    prob_file_nmr = models.FileField(upload_to=get_upload_path, default='', max_length=1024, blank=True)
    prob_torrent_file_nmr = models.FileField(default='', max_length=1024, blank=True)

    prob_file_ms = models.FileField(upload_to=get_upload_path, default='', max_length=1024, blank=True)
    prob_torrent_file_ms = models.FileField(default='', max_length=1024, blank=True)

    def save(self, *args, **kwargs):

        nmr_is_update = True
        ms_is_update = True

        if self.pk:

            old_self = Prob.objects.get(pk=self.pk)
            nmr_is_update = old_self.prob_file_nmr != self.prob_file_nmr
            ms_is_update = old_self.prob_file_ms != self.prob_file_ms

            torrent_paths = []
            if nmr_is_update:
                torrent_paths.append(old_self.prob_file_nmr)

            if ms_is_update:
                torrent_paths.append(old_self.prob_file_ms)

            if not torrent_paths:
                super(Prob, self).save(*args, **kwargs)
                return
            else:
                stop_torrent(torrent_paths)
                # maybe need deleting file

        super(Prob, self).save(*args, **kwargs)
        # creating torrent

        if nmr_is_update and self.prob_file_nmr:
            self.prob_torrent_file_nmr = start_torrent(str(self.prob_file_nmr))

        if ms_is_update and self.prob_file_ms:
            self.prob_torrent_file_ms = start_torrent(str(self.prob_file_ms))

        super(Prob, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        prob_metabolites = ProbMetabolite.objects.filter(prob_id=self.pk)
        for pm in prob_metabolites:
            pm.delete()

        try:
            torrent_paths = str(self.prob_torrent_file_nmr)
            req = requests.post(API_URL + '/torrent/stop',
                                json=json.dumps({'torrentPaths': [torrent_paths]}),
                                auth=API_AUTH)

            os.remove(TORRENT_DIR + '/' + str(self.prob_torrent_file_nmr))
            os.remove(TORRENT_DIR + '/' + os.path.splitext(str(self.prob_torrent_file_nmr))[0] + '.path')
        except Exception as e:
            experiments_base_logger.error('Prob torrent files stopping and deleting error: ' + str(e))

        try:
            os.remove(str(self.prob_file_nmr))
        except Exception as e:
            experiments_base_logger.error('Prob files deleting error: ' + str(e))

        super(Prob, self).delete(*args, **kwargs)


class Experiment(models.Model):
    class Meta:
        db_table = 'experiments'
        verbose_name = 'experiment'
        verbose_name_plural = 'experiments'

    experiment_name = models.CharField(max_length=128, verbose_name='Experiment name')
    taxon_id = models.ForeignKey('experiments_base.Taxon', verbose_name='Taxon', on_delete=models.DO_NOTHING)

    way_of_life = models.IntegerField(default=WayOfLife.OTHER, choices=WayOfLife.choices,
                                      verbose_name='Way of life', blank=True)
    habitat = models.IntegerField(default=Habitat.OTHER, choices=Habitat.choices,
                                  verbose_name='Habitat', blank=True)

    environmental_factors = models.ManyToManyField(EnvironmentalFactor, verbose_name='Environmental factors',
                                                   blank=True)
    diseases = models.ManyToManyField(Disease, verbose_name='Diseases', blank=True)
    withdraw_conditions = models.ManyToManyField(WithdrawCondition, verbose_name='Withdraw conditions', blank=True)

    withdraw_place = models.ForeignKey('experiments_base.WithdrawPlace', verbose_name='Withdraw place',
                                       on_delete=models.DO_NOTHING, blank=True, null=True)
    withdraw_date = models.DateTimeField(default=timezone.now, verbose_name='Withdraw date', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')

    comments = models.CharField(max_length=1024, verbose_name='Comments', blank=True)
    additional_properties = models.ManyToManyField(AdditionalProperty, verbose_name='Additional properties',
                                                   blank=True)

    experiment_folder = models.CharField(default='old_experiment', max_length=128, verbose_name='Experiment folder')

    def __str__(self):
        parent_name = 'ROOT' if self.taxon_id.taxon_name == '' else self.taxon_id.taxon_name
        return '{0} ({1})'.format(self.experiment_name, parent_name)

    def save(self, *args, **kwargs):
        if not self.pk:
            super(Experiment, self).save(*args, **kwargs)
            self.experiment_folder = self.experiment_name + '_' + str(self.pk)
            super(Experiment, self).save(*args, **kwargs)
            full_path = str(SHARED_FILES_DIR) + '/' + get_full_path(self.taxon_id) + '/' + self.experiment_folder
            os.mkdir(full_path)
        else:
            old_self = Experiment.objects.get(pk=self.pk)
            old_experiment_folder = old_self.experiment_folder
            full_path_old = str(SHARED_FILES_DIR) + '/' + get_full_path(self.taxon_id) + '/' + self.experiment_folder
            self.experiment_folder = self.experiment_name + '_' + str(self.pk)
            # replace with right side 1 occurrence in string - need for security(can be same names of taxons)
            full_path_new = r_replace(full_path_old, old_experiment_folder, self.experiment_folder, 1)

            os.rename(full_path_old, full_path_new)
            super(Experiment, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        probs = Prob.objects.filter(experiment_id=self.pk)
        for p in probs:
            p.delete()

        super(Experiment, self).delete(*args, **kwargs)


class InterfaceName(models.Model):
    class Meta:
        db_table = 'interface_names'
        verbose_name = 'interface name'
        verbose_name_plural = 'interface names'

    name = models.CharField(max_length=128, verbose_name='Name')
    value = models.CharField(max_length=128, verbose_name='Value')
    search_name = models.CharField(max_length=64, verbose_name='Search name', unique=True)
    search_name = models.CharField(max_length=64, verbose_name='Search name', unique=True)
