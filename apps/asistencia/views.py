"""Puente al portal de profesoras.

La asistencia vive ahora en /profesoras/. Esta vista se mantiene para que
los enlaces antiguos no queden rotos.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def mis_clases(request):
    return redirect('profesoras:panel')
