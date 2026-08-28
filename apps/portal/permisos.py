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
        return vista(request, *args, **kwargs)
    return envoltura
