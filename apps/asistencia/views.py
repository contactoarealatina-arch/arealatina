"""Vistas del modulo de asistencia (para profesoras)."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.gestion.models import Clase


@login_required
def mis_clases(request):
    """Listado de clases de la profesora conectada."""
    clases = Clase.objects.filter(activa=True).select_related('profesora')
    if request.user.es_profesor:
        clases = clases.filter(profesora=request.user)
    return render(request, 'gestion/mis_clases.html', {'clases': clases})
