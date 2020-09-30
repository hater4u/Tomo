from django import template

register = template.Library()


@register.filter()
def way_of_life(value):
    wl = {0: 'diurnal', 1: 'nocturnal', 2: 'twilight', 3: 'not specified', '': ' ', None: ' '}
    return wl[value]


@register.filter()
def habitat(value):
    h = {0: 'wild', 1: 'laboratory', 2: 'farm', 3: 'not specified', '': ' ', None: ' '}
    return h[value]


@register.filter()
def gender(value):
    g = {0: 'male', 1: 'female', 2: 'not specified', '': ' ', None: ' '}
    return g[value]


@register.filter()
def get_item(dictionary, key):
    return dictionary.get(key)
