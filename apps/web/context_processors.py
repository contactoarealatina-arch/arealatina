"""Expone los datos de contacto de la academia a todos los templates."""
from django.conf import settings


def academia(request):
    return {
        'academia': settings.ACADEMIA,
        'sitio_en_preparacion': settings.SITIO_PRIVADO,
    }


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


def analitica(request):
    """Decide si esta página puede llevar Google Analytics.

    Solo el sitio público se mide. El panel, el portal de alumnos y el de
    profesoras quedan fuera a propósito: ahí no hay marketing que analizar
    y sí datos de personas identificables, que es justo lo que no
    corresponde mandarle a un tercero.

    La medición además no arranca sola: el visitante tiene que aceptarla
    en el aviso de cookies. Eso lo resuelve el navegador, acá solo se
    entrega el código de medición cuando la página tiene derecho a usarlo.
    """
    from django.conf import settings

    coincidencia = getattr(request, 'resolver_match', None)
    # El namespace 'web' son las páginas públicas. Se compara con eso y no
    # con la ruta porque una URL nueva en apps/web queda incluida sola,
    # mientras que una lista de rutas escritas a mano se olvida.
    publica = bool(coincidencia) and coincidencia.namespace == 'web'

    medible = publica and (not settings.DEBUG or settings.GA_EN_DESARROLLO)

    return {
        'es_pagina_publica': publica,
        'ga_id': settings.GA_MEASUREMENT_ID if medible else '',
    }
