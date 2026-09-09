"""Módulo 10b — Estado técnico del sistema. Solo superadmin.

Una sola pantalla cronológica con lo que pasa por debajo: seguridad,
errores del servidor y movimientos raros de tráfico. Están juntos porque
para quien revisa un incidente son lo mismo —cosas que ocurrieron, en
orden— y separarlos obligaría a cruzar horas entre dos pantallas.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .. import sistema as vigilancia
from ..models import AlertaSistema, EstadisticaDiaria
from ..permisos import superadmin_requerido


@superadmin_requerido
def alertas_sistema(request):
    tipo = request.GET.get('tipo', '')
    eventos = vigilancia.linea_de_tiempo(limite=80, tipo=tipo)

    sin_leer = AlertaSistema.objects.filter(leida=False)

    return render(request, 'gestion/sistema/alertas.html', {
        'activo': 'alertas_sistema',
        'eventos': eventos,
        'tipos': AlertaSistema.Tipo.choices,
        'tipo': tipo,
        'conteo': {
            'sin_leer': sin_leer.count(),
            'urgentes': sin_leer.filter(
                severidad=AlertaSistema.Severidad.URGENTE).count(),
        },
        # El tráfico de la última quincena, para que el número de una
        # alerta se pueda mirar contra su propia serie y no en el aire.
        'trafico': _barras(EstadisticaDiaria.objects.all()[:14][::-1]),
    })


def _barras(dias, alto=90):
    """Le calcula a cada día la altura de su barra, en píxeles.

    Va en Python y no en la plantilla porque el lenguaje de plantillas de
    Django no divide. Y va en píxeles y no en porcentaje porque el
    contenedor no tiene altura fija: un porcentaje sobre una altura
    automática da cero y no se vería ninguna barra.
    """
    dias = list(dias)
    tope = max((d.visitas_estimadas for d in dias), default=0)
    for dia in dias:
        # Mínimo 3 px: un día con cero visitas tiene que dejar su hueco
        # visible, si no la serie parece tener menos días de los que tiene.
        dia.altura_px = max(3, round(dia.visitas_estimadas / tope * alto)) if tope else 3
    return dias


@superadmin_requerido
def alerta_sistema_leer(request, pk):
    if request.method != 'POST':
        return redirect('gestion:alertas_sistema')

    alerta = get_object_or_404(AlertaSistema, pk=pk)
    alerta.leida = True
    alerta.save(update_fields=['leida'])
    return redirect(request.POST.get('siguiente') or 'gestion:alertas_sistema')


@superadmin_requerido
def alertas_sistema_revisar(request):
    if request.method != 'POST':
        return redirect('gestion:alertas_sistema')

    resultado = vigilancia.revisar_todo()
    creadas = sum(v for v in resultado.values() if v)
    if creadas:
        messages.warning(request, f'Revisión lista: {creadas} alerta(s) nuevas.')
    else:
        messages.info(request, 'Revisión lista: el tráfico está dentro de lo normal.')
    return redirect('gestion:alertas_sistema')
