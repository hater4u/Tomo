from django.contrib import admin
import nested_admin
from .models import Taxon, Experiment, Prob, ProbMetabolite, Metabolite, MetaboliteName
from .models import EnvironmentalFactor, Disease, WithdrawCondition, WithdrawPlace, AdditionalProperty
from .models import InterfaceName

import logging
from tomo.settings import LOGGING

logging.config.dictConfig(LOGGING)
experiments_base_logger = logging.getLogger('django')


def set_extra_context_args(self, request, extra_context, model_class, model_args, field_name):

    d_objects = model_class.objects.filter(**model_args)
    deleted_objects, model_count, perms_needed, protected = self.get_deleted_objects(d_objects, request)

    extra_context['deleted_' + field_name] = deleted_objects
    if extra_context.get('model_count_new', False) is False:
        extra_context['model_count_new'] = dict(model_count).items()
    else:
        extra_context['model_count_new'] = {**dict(extra_context['model_count_new']), **model_count}.items()
    extra_context[field_name + '_perms_needed'] = perms_needed
    extra_context[field_name + '_protected'] = protected


@admin.register(Taxon)
class TaxonAdmin(admin.ModelAdmin):
    list_display = ('taxon_name', 'taxon_parent_name', 'is_tissue', 'view_in_popular', 'taxon_folder')
    ordering = ('taxon_name',)
    exclude = ('taxon_folder',)
    actions = ['delete_model']

    def get_actions(self, request):
        actions = super(TaxonAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def delete_model(self, request, obj):
        if isinstance(obj, Taxon):
            obj.delete()
        else:
            for o in obj.all():
                o.delete()

    delete_model.short_description = 'Delete selected taxons'

    @staticmethod
    def taxon_parent_name(obj):
        if obj.parent_id is None:
            parent_name = 'ROOT'
        elif not obj.parent_id.taxon_name:
            parent_name = 'ROOT'
        else:
            parent_name = obj.parent_id.taxon_name

        return '{}'.format(parent_name)

    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}

        set_extra_context_args(self, request, extra_context, Taxon, {'parent_id': object_id}, 'sub_taxons')
        set_extra_context_args(self, request, extra_context, Experiment, {'taxon_id': object_id}, 'experiments')
        set_extra_context_args(self, request, extra_context, Prob, {'experiment_id__taxon_id': object_id}, 'probs')
        set_extra_context_args(self, request, extra_context, ProbMetabolite,
                               {'prob_id__experiment_id__taxon_id': object_id}, 'prob_metabolites')

        return super(TaxonAdmin, self).delete_view(request, object_id, extra_context=extra_context)


@admin.register(ProbMetabolite)
class ProbMetaboliteAdmin(nested_admin.NestedModelAdmin):
    list_display = ('metabolite_name', 'concentration')
    ordering = ('metabolite_id',)

    @staticmethod
    def metabolite_name(obj):
        return '{}'.format(obj.metabolite_id.metabolite_name)


class ProbMetaboliteAdminInline(nested_admin.NestedTabularInline):
    model = ProbMetabolite
    extra = 0


@admin.register(Prob)
class ProbAdmin(nested_admin.NestedModelAdmin):

    change_form_template = 'progressbar_upload/change_form.html'
    add_form_template = 'progressbar_upload/change_form.html'

    list_display = ('prob_name', 'gender',
                    'month_age', 'hours_post_mortem',
                    'weight', 'length', 'temperature',
                    'prob_file_nmr', 'prob_file_ms', )
    ordering = ('prob_name',)
    exclude = ('prob_torrent_file_nmr', 'prob_torrent_file_ms', )
    inlines = (ProbMetaboliteAdminInline, )
    actions = ['delete_model']

    def get_actions(self, request):
        actions = super(ProbAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def delete_model(self, request, obj):
        if isinstance(obj, Prob):
            obj.delete()
        else:
            for o in obj.all():
                o.delete()

    delete_model.short_description = 'Delete selected probs'

    @staticmethod
    def experiment_name(obj):
        return '{}'.format('ROOT' if obj.experiment_id.experiment_name == '' else obj.experiment_id.experiment_name)

    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}

        set_extra_context_args(self, request, extra_context, ProbMetabolite, {'prob_id': object_id}, 'prob_metabolites')

        # prob = Prob.objects.get(pk=object_id)
        # extra_context['deleted_files'] = [str(prob.prob_file)] if prob.prob_file != '' else []
        # extra_context['model_count_new'] = dict(model_count).items()

        return super(ProbAdmin, self).delete_view(request, object_id, extra_context=extra_context)


class ProbAdminInline(nested_admin.NestedTabularInline):

    change_form_template = 'progressbar_upload/change_form.html'
    add_form_template = 'progressbar_upload/change_form.html'

    model = Prob
    extra = 0
    inlines = (ProbMetaboliteAdminInline, )
    exclude = ('prob_torrent_file_nmr', 'prob_torrent_file_ms',)


@admin.register(Experiment)
class ExperimentAdmin(nested_admin.NestedModelAdmin):

    change_form_template = 'progressbar_upload/change_form.html'
    add_form_template = 'progressbar_upload/change_form.html'

    list_display = ('experiment_name', 'taxon_id', 'way_of_life', 'habitat', 'genders',
                    'withdraw_place', 'created_at', 'withdraw_date', 'experiment_folder')

    ordering = ('experiment_name',)
    exclude = ('experiment_folder',)
    inlines = (ProbAdminInline, )
    actions = ['delete_model']

    def get_actions(self, request):
        actions = super(ExperimentAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def delete_model(self, request, obj):
        if isinstance(obj, Experiment):
            obj.delete()
        else:
            for o in obj.all():
                o.delete()

    delete_model.short_description = 'Delete selected experiments'

    @staticmethod
    def taxon_id(obj):
        return '{}'.format('ROOT' if obj.taxon_id.taxon_name == '' else obj.taxon_id.taxon_name)

    @staticmethod
    def genders(obj):
        gender_table = {0: 'male', 1: 'female', 2: 'other', '': ' ', None: ' '}
        return ', '.join([gender_table[p.gender] for p in Prob.objects.filter(experiment_id=obj.pk)])

    fieldsets = (
        (None, {'fields': ('experiment_name', 'taxon_id')}),
        (None, {'fields': ('way_of_life', 'habitat',)}),
        (None, {'fields': ('withdraw_place', 'withdraw_date', 'comments')}),
        (None, {'fields': (('environmental_factors', 'diseases', 'withdraw_conditions'), 'additional_properties',)}),
                 )

    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}

        set_extra_context_args(self, request, extra_context, Prob, {'experiment_id': object_id},
                               'probs')
        set_extra_context_args(self, request, extra_context, ProbMetabolite, {'prob_id__experiment_id': object_id},
                               'prob_metabolites')

        return super(ExperimentAdmin, self).delete_view(request, object_id, extra_context=extra_context)


@admin.register(Metabolite)
class MetaboliteAdmin(admin.ModelAdmin):
    delete_confirmation_template = 'admin/experiments_base/metabolite/delete_confirmation.html'

    list_display = ('metabolite_name', 'pub_chem_cid', 'comment', 'pk',)
    ordering = ('metabolite_name',)
    actions = ['delete_model']

    def get_actions(self, request):
        actions = super(MetaboliteAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def delete_model(self, request, obj):
        if isinstance(obj, Metabolite):
            obj.delete()
        else:
            for o in obj.all():
                o.delete()

    delete_model.short_description = 'Delete selected metabolites'

    def delete_view(self, request, object_id, extra_context=None):
        extra_context = extra_context or {}

        set_extra_context_args(self, request, extra_context, MetaboliteName, {'metabolite_id': object_id},
                               'metabolite_names')

        return super(MetaboliteAdmin, self).delete_view(request, object_id, extra_context=extra_context)


@admin.register(MetaboliteName)
class MetaboliteNameAdmin(admin.ModelAdmin):
    list_display = ('metabolite_synonym', 'metabolite_id',)
    ordering = ('metabolite_id',)


@admin.register(EnvironmentalFactor)
class EnvironmentalFactorAdmin(admin.ModelAdmin):
    list_display = ('factor_name',)
    ordering = ('factor_name',)


@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ('disease_name',)
    ordering = ('disease_name',)


@admin.register(WithdrawCondition)
class WithdrawConditionAdmin(admin.ModelAdmin):
    list_display = ('withdraw_condition',)
    ordering = ('withdraw_condition',)


@admin.register(WithdrawPlace)
class WithdrawPlaceAdmin(admin.ModelAdmin):
    list_display = ('withdraw_place',)
    ordering = ('withdraw_place',)


@admin.register(AdditionalProperty)
class AdditionalPropertyAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    ordering = ('key',)


@admin.register(InterfaceName)
class InterfaceNameAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'search_name')
    ordering = ('name',)
    actions = None

    def has_delete_permission(self, request, obj=None):
        # Disable delete
        return False

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['search_name']
        else:
            return []
