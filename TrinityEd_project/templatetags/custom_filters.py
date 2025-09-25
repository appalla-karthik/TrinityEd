from django import template

register = template.Library()

@register.filter
def replace_space(value, arg):
    """
    Replace all occurrences of the first argument with the second argument in the value.
    Usage: {{ value|replace_space:' ':'-' }}
    """
    if not value:
        return ''
    return value.replace(arg, '-')