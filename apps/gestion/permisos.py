"""Control de acceso por rol para el módulo de gestión."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def _sin_sesion(request):
    return redirect_to_login(request.get_full_path())


def gestion_requerida(vista):
    """Solo ADMIN y SUPERADMIN entran al módulo de gestión.

    A un PROFESOR se le manda a su propio módulo en vez de darle un 403
    seco: no es que no tenga permiso de estar en el sistema, es que su
    lugar es otro.
    """
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _sin_sesion(request)
        if request.user.puede_gestionar:
            return vista(request, *args, **kwargs)
        if request.user.es_profesor:
            messages.info(request, 'Tu cuenta accede al módulo de asistencia.')
            return redirect('profesoras:panel')
        raise PermissionDenied('No tienes acceso al módulo de gestión.')
    return envoltura


def superadmin_requerido(vista):
    """Reservado para la auditoría."""
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _sin_sesion(request)
        if not request.user.es_superadmin:
            raise PermissionDenied('Solo el super administrador puede ver esta sección.')
        return vista(request, *args, **kwargs)
    return envoltura


def profesor_o_gestion(vista):
    """Asistencia: la usan tanto las profesoras como el equipo administrativo."""
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _sin_sesion(request)
        if request.user.puede_gestionar or request.user.es_profesor:
            return vista(request, *args, **kwargs)
        raise PermissionDenied('No tienes acceso a esta sección.')
    return envoltura
