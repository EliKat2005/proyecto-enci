"""
Filtros personalizados para cálculos financieros en templates.
"""
from decimal import Decimal
from django import template

register = template.Library()


@register.filter
def multiply(value, arg):
    """Multiplica un valor por un argumento."""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError, ArithmeticError):
        return Decimal('0.00')


@register.filter
def subtract(value, arg):
    """Resta un argumento de un valor."""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except (ValueError, TypeError, ArithmeticError):
        return Decimal('0.00')


@register.filter
def add_decimal(value, arg):
    """Suma dos valores decimales."""
    try:
        return Decimal(str(value)) + Decimal(str(arg))
    except (ValueError, TypeError, ArithmeticError):
        return Decimal('0.00')
