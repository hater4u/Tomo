from django.contrib import admin
import nested_admin
from .models import Taxon, Experiment, Prob, ProbMetabolite, Metabolite, MetaboliteName
from .models import EnvironmentalFactor, Disease, WithdrawCondition, WithdrawPlace, AdditionalProperty
from .models import InterfaceName


class TaxonAdmin(admin.ModelAdmin):
    list_display = ('taxon_name', 'taxon_parent_name', 'is_tissue', 'view_in_popular', 'taxon_folder')
    ordering = ('taxon_name',)
    exclude = ('taxon_folder',)

    def taxon_parent_name(self, obj):
        if obj.parent_id is None:
            parent_name = 'ROOT'
        elif not obj.parent_id.taxon_name:
            parent_name = 'ROOT'
        else:
            parent_name = obj.parent_id.taxon_name

        return '{}'.format(parent_name)


class ProbMetaboliteAdmin(nested_admin.NestedModelAdmin):
    list_display = ('metabolite_name', 'concentration')
    ordering = ('metabolite_id',)

    def metabolite_name(self, obj):
        return '{}'.format(obj.metabolite_id.metabolite_name)


class ProbMetaboliteAdminInline(nested_admin.NestedTabularInline):
    model = ProbMetabolite
    extra = 0


class ProbAdmin(nested_admin.NestedModelAdmin):
    list_display = ('prob_name', 'gender',
                    'month_age', 'hours_post_mortem',
                    'weight', 'length', 'temperature',
                    'prob_file',)
    ordering = ('prob_name',)
    exclude = ('prob_torrent_file',)
    inlines = (ProbMetaboliteAdminInline, )

    def experiment_name(self, obj):
        return '{}'.format('ROOT' if obj.experiment_id.experiment_name == '' else obj.experiment_id.experiment_name)


class ProbAdminInline(nested_admin.NestedTabularInline):
    model = Prob
    extra = 0
    inlines = (ProbMetaboliteAdminInline, )
    exclude = ('prob_torrent_file',)


class ExperimentAdmin(nested_admin.NestedModelAdmin):
    list_display = ('experiment_name', 'taxon_id', 'way_of_life', 'habitat',
                    'withdraw_place', 'withdraw_date', 'experiment_folder')

    ordering = ('experiment_name',)
    exclude = ('experiment_folder',)
    inlines = (ProbAdminInline, )

    def taxon_id(self, obj):
        return '{}'.format('ROOT' if obj.taxon_id.taxon_name == '' else obj.taxon_id.taxon_name)

    fieldsets = (
        (None, {'fields': ('experiment_name', 'taxon_id')}),
        (None, {'fields': ('way_of_life', 'habitat',)}),
        (None, {'fields': ('withdraw_place', 'withdraw_date', 'comments')}),
        (None, {'fields': (('environmental_factors', 'diseases', 'withdraw_conditions'), 'additional_properties',)}),
                 )


class MetaboliteAdmin(admin.ModelAdmin):
    list_display = ('metabolite_name', 'pub_chem_cid', 'pk',)
    ordering = ('metabolite_name',)


class MetaboliteNameAdmin(admin.ModelAdmin):
    list_display = ('metabolite_synonym', 'metabolite_id',)
    ordering = ('metabolite_id',)


class EnvironmentalFactorAdmin(admin.ModelAdmin):
    list_display = ('factor_name',)
    ordering = ('factor_name',)


class DiseaseAdmin(admin.ModelAdmin):
    list_display = ('disease_name',)
    ordering = ('disease_name',)


class WithdrawConditionAdmin(admin.ModelAdmin):
    list_display = ('withdraw_condition',)
    ordering = ('withdraw_condition',)


class WithdrawPlaceAdmin(admin.ModelAdmin):
    list_display = ('withdraw_place',)
    ordering = ('withdraw_place',)


class AdditionalPropertyAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    ordering = ('key',)


class InterfaceNameAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'search_name')
    ordering = ('name',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['search_name']
        else:
            return []


# TODO maybe use decorator for this ?
admin.site.register(Taxon, TaxonAdmin)
admin.site.register(Experiment, ExperimentAdmin)
admin.site.register(Prob, ProbAdmin)
admin.site.register(ProbMetabolite, ProbMetaboliteAdmin)
admin.site.register(Metabolite, MetaboliteAdmin)
admin.site.register(MetaboliteName, MetaboliteNameAdmin)
admin.site.register(EnvironmentalFactor, EnvironmentalFactorAdmin)
admin.site.register(Disease, DiseaseAdmin)
admin.site.register(WithdrawCondition, WithdrawConditionAdmin)
admin.site.register(WithdrawPlace, WithdrawPlaceAdmin)
admin.site.register(AdditionalProperty, AdditionalPropertyAdmin)
admin.site.register(InterfaceName, InterfaceNameAdmin)
