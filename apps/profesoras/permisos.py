"""Acceso al portal de profesoras.

Entran las profesoras y también el equipo administrativo, pero ven cosas
distintas: la profesora solo sus clases, el administrador todas. El filtro
va siempre en el servidor, nunca en la plantilla.
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from apps.gestion.models import Clase


def acceso_profesoras(vista):
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if request.user.es_profesor or request.user.puede_gestionar:
            return vista(request, *args, **kwargs)
        raise PermissionDenied('No tienes acceso al portal de profesoras.')
    return envoltura


def es_vista_admin(usuario):
    """True cuando quien mira es del equipo de gestión, no una profesora."""
    return usuario.puede_gestionar and not usuario.es_profesor


def clases_visibles(usuario, solo_activas=True):
    """Las clases que esta persona tiene derecho a ver.

    Una profesora ve únicamente las suyas. El administrador las ve todas,
    porque necesita poder cubrir una clase o revisar cualquier lista.
    """
    qs = Clase.objects.select_related('profesora')
    if solo_activas:
        qs = qs.filter(activa=True)
    if es_vista_admin(usuario):
        return qs
    return qs.filter(profesora=usuario)


def clase_visible_o_404(usuario, pk):
    from django.shortcuts import get_object_or_404

    return get_object_or_404(clases_visibles(usuario, solo_activas=False), pk=pk)
