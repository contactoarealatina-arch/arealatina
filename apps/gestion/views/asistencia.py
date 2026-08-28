"""La asistencia se pasa desde el portal de profesoras.

Esta vista quedó como puente: cualquier enlace viejo a /gestion/asistencia/
lleva al portal, que es donde vive ahora la funcionalidad y está pensado
para tablet.
"""
from django.shortcuts import redirect

from ..permisos import profesor_o_gestion


@profesor_o_gestion
def asistencia(request):
    return redirect('profesoras:panel')
