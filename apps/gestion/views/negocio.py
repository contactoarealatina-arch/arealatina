"""Módulo 6b — Alertas de negocio.

Separado del panel de alertas de siempre a propósito: aquel es una lista
de tareas (renovar, cobrar, llamar) que alguien cierra una por una; este
es una lectura de cómo va el estudio, que se mira y se decide.
"""
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .. import negocio as reglas
from ..models import AlertaNegocio
from ..permisos import gestion_requerida

POR_PAGINA = 15


@gestion_requerida
def alertas_negocio(request):
    tipo = request.GET.get('tipo', '')
    severidad = request.GET.get('severidad', '')
    ver = request.GET.get('ver', 'todas')

    qs = AlertaNegocio.objects.all()
    if tipo:
        qs = qs.filter(tipo=tipo)
    if severidad:
        qs = qs.filter(severidad=severidad)
    if ver == 'pendientes':
        qs = qs.filter(leida=False)

    paginador = Paginator(qs, POR_PAGINA)
    pagina = paginador.get_page(request.GET.get('page'))

    parametros = request.GET.copy()
    parametros.pop('page', None)

    # Los conteos se calculan sobre todas las alertas y no sobre la
    # página: un contador que dijera "3 urgentes" cuando hay 12 sería
    # peor que no tenerlo.
    sin_leer = AlertaNegocio.objects.filter(leida=False)

    return render(request, 'gestion/alertas/negocio.html', {
        'activo': 'alertas_negocio',
        'pagina': pagina,
        'total': paginador.count,
        'tipos': AlertaNegocio.Tipo.choices,
        'severidades': AlertaNegocio.Severidad.choices,
        'filtros': {'tipo': tipo, 'severidad': severidad, 'ver': ver},
        'querystring': parametros.urlencode(),
        'conteo': {
            'sin_leer': sin_leer.count(),
            'urgentes': sin_leer.filter(
                severidad=AlertaNegocio.Severidad.URGENTE).count(),
            'atencion': sin_leer.filter(
                severidad=AlertaNegocio.Severidad.ATENCION).count(),
        },
    })


@gestion_requerida
def alerta_negocio_leer(request, pk):
    if request.method != 'POST':
        return redirect('gestion:alertas_negocio')

    alerta = get_object_or_404(AlertaNegocio, pk=pk)
    alerta.leida = True
    alerta.save(update_fields=['leida'])
    return redirect(request.POST.get('siguiente') or 'gestion:alertas_negocio')


@gestion_requerida
def alertas_negocio_leer_todas(request):
    if request.method != 'POST':
        return redirect('gestion:alertas_negocio')

    cuantas = AlertaNegocio.objects.filter(leida=False).update(leida=True)
    messages.success(request, f'{cuantas} alerta(s) marcadas como leídas.')
    return redirect('gestion:alertas_negocio')


@gestion_requerida
def alertas_negocio_revisar(request):
    """Corre las revisiones del cron a pedido, sin esperar a mañana."""
    if request.method != 'POST':
        return redirect('gestion:alertas_negocio')

    resultado = reglas.revisar_todo()
    creadas = sum(v for v in resultado.values() if v)
    if creadas:
        messages.success(request, f'Revisión lista: {creadas} alerta(s) nuevas.')
    else:
        messages.info(request, 'Revisión lista: no hay nada nuevo que avisar.')
    return redirect('gestion:alertas_negocio')
