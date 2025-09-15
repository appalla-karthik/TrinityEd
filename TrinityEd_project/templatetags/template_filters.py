from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
@stringfilter
def replace(value, arg):
      """
      Replace all occurrences of a substring in the value.
      Usage: {{ value|replace:"old,new" }}
      Example: {{ "Very High"|replace:" ,-" }} -> "Very-High"
      """
      try:
          old, new = arg.split(',', 1)
          return value.replace(old, new)
      except ValueError:
          return value