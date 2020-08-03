from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Taxon(models.Model):
    class Meta:
        db_table = 'taxons'
        verbose_name = 'taxon'
        verbose_name_plural = 'taxons'

    taxon_name = models.CharField(max_length=128, verbose_name='Имя таксона')
    parent_id = models.ForeignKey('self', null=True, blank=True, verbose_name='Родительский таксон',
                                  on_delete=models.DO_NOTHING)
    view_in_popular = models.BooleanField(default=False, verbose_name='Отображать в популярных таксонах')
    is_tissue = models.BooleanField(default=False, verbose_name='Ткань')

    def __str__(self):
        if self.parent_id is None:
            parent_name = 'ROOT'
        elif not self.parent_id.taxon_name:
            parent_name = 'ROOT'
        else:
            parent_name = self.parent_id.taxon_name

        name = 'ROOT' if self.taxon_name is None else self.taxon_name
        return '{0} ({1})'.format(name, parent_name)

    # TODO realise creation directory in initialization taxon object and renaming directory
    #  in file system while renaming taxon


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

    factor_name = models.CharField(max_length=256, verbose_name='Имя фактора среды')

    def __str__(self):
        return self.factor_name


class Disease(models.Model):
    class Meta:
        db_table = 'diseases'
        verbose_name = 'disease'
        verbose_name_plural = 'diseases'

    disease_name = models.CharField(max_length=256, verbose_name='Имя заболевания')

    def __str__(self):
        return self.disease_name


class WithdrawCondition(models.Model):
    class Meta:
        db_table = 'withdraw_conditions'
        verbose_name = 'withdraw condition'
        verbose_name_plural = 'withdraw conditions'

    withdraw_condition = models.CharField(max_length=256, verbose_name='Условие забора')

    def __str__(self):
        return self.withdraw_condition


class WithdrawPlace(models.Model):
    class Meta:
        db_table = 'withdraw_places'
        verbose_name = 'withdraw place'
        verbose_name_plural = 'withdraw places'

    withdraw_place = models.CharField(max_length=256, verbose_name='Место забора')

    def __str__(self):
        return self.withdraw_place


class AdditionalProperty(models.Model):
    class Meta:
        db_table = 'additional_properties'
        verbose_name = 'additional property'
        verbose_name_plural = 'additional properties'

    key = models.CharField(max_length=128, verbose_name='Ключ')
    value = models.CharField(max_length=128, verbose_name='Значение')

    def __str__(self):
        return '{}: {}'.format(self.key, self.value)


class Metabolite(models.Model):
    class Meta:
        db_table = 'metabolites'
        verbose_name = 'metabolite'
        verbose_name_plural = 'metabolites'

    metabolite_name = models.CharField(max_length=128, verbose_name='Основное имя метаболита')
    pubchemcid = models.IntegerField(default=0, blank=True, verbose_name='PubChemCid')

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


# for search one metabolite by different names
class MetaboliteName(models.Model):
    class Meta:
        db_table = 'metabolite_names'
        verbose_name = 'metabolite name'
        verbose_name_plural = 'metabolite names'

    metabolite_synonym = models.CharField(max_length=128, verbose_name='Синоним основному имени метаболита')
    metabolite_id = models.ForeignKey('experimentsbase.Metabolite',
                                      verbose_name='Метаболит, для которого добавляем синонимичное имя',
                                      on_delete=models.DO_NOTHING)

    def __str__(self):
        return '{}({})'.format(self.metabolite_synonym, self.metabolite_id.metabolite_name)


class ProbMetabolite(models.Model):
    class Meta:
        db_table = 'prob_metabolites'
        verbose_name = 'prob metabolite'
        verbose_name_plural = 'prob metabolites'

    prob_id = models.ForeignKey('experimentsbase.Prob', verbose_name='Проба', on_delete=models.DO_NOTHING)
    metabolite_id = models.ForeignKey('experimentsbase.Metabolite', verbose_name='Метаболит',
                                      on_delete=models.DO_NOTHING)
    concentration = models.FloatField(default=0, validators=[MinValueValidator(0)],
                                      verbose_name='Концентрация(нмоль/г)')

    def __str__(self):
        return '{}({} нмоль/г)'.format(self.metabolite_id.metabolite_name, self.concentration)


class Prob(models.Model):
    class Meta:
        db_table = 'probs'
        verbose_name = 'prob'
        verbose_name_plural = 'probs'

    prob_name = models.CharField(max_length=128, verbose_name='Имя пробы')
    experiment_id = models.ForeignKey('experimentsbase.Experiment', verbose_name='Эксперимент',
                                      on_delete=models.DO_NOTHING)

    way_of_life = models.IntegerField(default=WayOfLife.OTHER, choices=WayOfLife.choices, verbose_name='Образ жизни')
    habitat = models.IntegerField(default=Habitat.OTHER, choices=Habitat.choices, verbose_name='Ареал обитания')
    gender = models.IntegerField(default=Gender.OTHER, choices=Gender.choices, verbose_name='Пол')

    month_age = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name='Возраст(месяцы)')
    hours_post_mortem = models.IntegerField(default=0, validators=[MinValueValidator(0)],
                                            verbose_name='Время после смерти(часы)')

    weight = models.FloatField(default=0, validators=[MinValueValidator(0)], verbose_name='Вес(кг)')
    length = models.FloatField(default=0, validators=[MinValueValidator(0)], verbose_name='Рост/длина(см)')
    temperature = models.FloatField(default=0, validators=[MinValueValidator(0)],
                                    verbose_name='Температура(градусы Цельсия)')

    # TODO realise downloading file
    # TODO loading data from previous prob when you adding new prob(copy all fields and ProbMetabolites)


class Experiment(models.Model):
    class Meta:
        db_table = 'experiments'
        verbose_name = 'experiment'
        verbose_name_plural = 'experiments'

    experiment_name = models.CharField(max_length=128, verbose_name='Имя эксперимента')
    taxon_id = models.ForeignKey('experimentsbase.Taxon', verbose_name='Таксон', on_delete=models.DO_NOTHING)

    way_of_life = models.IntegerField(default=WayOfLife.OTHER, choices=WayOfLife.choices, verbose_name='Образ жизни')
    habitat = models.IntegerField(default=Habitat.OTHER, choices=Habitat.choices, verbose_name='Ареал обитания')
    gender = models.IntegerField(default=Gender.OTHER, choices=Gender.choices, verbose_name='Пол')

    month_age = models.IntegerField(default=0, validators=[MinValueValidator(0)], verbose_name='Возраст(месяцы)')
    hours_post_mortem = models.IntegerField(default=0, validators=[MinValueValidator(0)],
                                            verbose_name='Время после смерти(часы)')

    weight = models.FloatField(default=0, validators=[MinValueValidator(0)], verbose_name='Вес(кг)')
    length = models.FloatField(default=0, validators=[MinValueValidator(0)], verbose_name='Рост/длина(см)')
    temperature = models.FloatField(default=0, validators=[MinValueValidator(0)],
                                    verbose_name='Температура(градусы Цельсия)')

    environmental_factors = models.ManyToManyField(EnvironmentalFactor, verbose_name='Факторы среды', blank=True)
    diseases = models.ManyToManyField(Disease, verbose_name='Заболевания', blank=True)
    withdraw_conditions = models.ManyToManyField(WithdrawCondition, verbose_name='Условия забора', blank=True)

    withdraw_place = models.ForeignKey('experimentsbase.WithdrawPlace', verbose_name='Место забора',
                                       on_delete=models.DO_NOTHING, blank=True, null=True)
    withdraw_date = models.DateTimeField(default=timezone.now, verbose_name='Дата забора')

    # string ?
    comments = models.CharField(max_length=1024, verbose_name='Комментарии', blank=True)
    additional_properties = models.ManyToManyField(AdditionalProperty, verbose_name='Дополнительные свойства',
                                                   blank=True)

    def __str__(self):
        parent_name = 'ROOT' if self.taxon_id.taxon_name == '' else self.taxon_id.taxon_name
        return '{0} ({1})'.format(self.experiment_name, parent_name)

    # TODO realise creation directory in initialization experiment object(exp_name + random str) and renaming directory
    #  in file system while renaming experiment


class InterfaceName(models.Model):
    class Meta:
        db_table = 'interface_names'
        verbose_name = 'interface name'
        verbose_name_plural = 'interface names'

    name = models.CharField(max_length=128, verbose_name='Имя')
    value = models.CharField(max_length=64, verbose_name='Значение')
    search_name = models.CharField(max_length=64, verbose_name='Имя для поиска', unique=True)
