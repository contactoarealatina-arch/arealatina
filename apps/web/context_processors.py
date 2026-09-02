"""Expone los datos de contacto de la academia a todos los templates."""
from django.conf import settings


def academia(request):
    return {'academia': settings.ACADEMIA}


def areas(request):
    """Las áreas del estudio, para el pie que se repite en todas las páginas.

    Va como procesador de contexto y no en cada vista porque el pie está en
    base.html: si faltara en una sola vista, esa página quedaría con el
    bloque de áreas vacío y nadie lo notaría hasta verla.
    """
    from apps.gestion.models import Categoria

    try:
        return {'areas_footer': Categoria.objects.filter(activa=True)}
    except Exception:
        # Antes de la primera migración la tabla no existe todavía.
        return {'areas_footer': []}
