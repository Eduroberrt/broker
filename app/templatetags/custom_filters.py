from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key"""
    if dictionary and key:
        return dictionary.get(key, 0)
    return 0

@register.filter
def divide(value, arg):
    """Divide value by arg"""
    try:
        value = Decimal(str(value))
        arg = Decimal(str(arg))
        if arg == 0:
            return 0
        return value / arg
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
