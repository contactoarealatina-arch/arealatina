"""Acceso al portal de alumnos.

Regla única y sin excepciones: un alumno ve sus datos y nada más. La ficha
sale siempre de request.user, nunca de un id que venga en la URL.
"""
from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def alumno_requerido(vista):
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('portal:login')

        # El equipo tiene su propio panel; no se les manda al del alumno.
        if request.user.puede_gestionar:
            return redirect('gestion:dashboard')
        if request.user.es_profesor:
            return redirect('profesoras:panel')

        ficha = getattr(request.user, 'ficha_alumno', None)
        if ficha is None:
            messages.error(
                request,
                'Tu cuenta todavía no está enlazada a una ficha de alumno. '
                'Escríbenos y lo arreglamos.'
            )
            return redirect('web:index')
        if ficha.eliminado:
            raise PermissionDenied('Esta ficha ya no está activa.')

        request.alumno = ficha

        # Antes de dejarlo entrar: si hay términos vigentes sin aceptar,
        # va primero a esa pantalla. Se comprueba acá y no en cada vista
        # para que no se pueda saltar escribiendo la URL a mano.
        if _debe_aceptar(request.user) and request.resolver_match:
            if request.resolver_match.url_name != 'terminos':
                return redirect('portal:terminos')

        return vista(request, *args, **kwargs)
    return envoltura


def _debe_aceptar(usuario):
    """¿Le falta aceptar la versión vigente de los términos?

    Si el estudio todavía no cargó ningún documento, no se le pide nada:
    una pantalla obligatoria sin texto que leer sería un muro sin puerta.
    """
    from apps.gestion.models import AceptacionTerminos, TerminoCondicion

    vigente = TerminoCondicion.vigente()
    if vigente is None:
        return False

    return not AceptacionTerminos.objects.filter(
        usuario=usuario, termino=vigente,
    ).exists()
