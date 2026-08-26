"""Filtros de formato propios del sitio."""
from django import template

register = template.Library()


@register.filter
def clp(valor):
    """Formatea un entero como monto chileno: 25000 -> 25.000

    El filtro intcomma de Django depende del locale instalado y en es-CL
    termina usando espacio en vez de punto, asi que lo hacemos explicito.
    """
    try:
        entero = int(valor)
    except (TypeError, ValueError):
        return valor
    return f'{entero:,}'.replace(',', '.')
