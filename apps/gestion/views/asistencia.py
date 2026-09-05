"""Asistencia vista desde la administración.

La asistencia se *pasa* desde el portal de profesoras, que está pensado
para tablet. Acá se *lee*: cuántos fueron a cada clase y qué días.

Esta vista existe porque se eliminó la confirmación previa del alumno.
Antes el estudio sabía quién iba a venir porque el alumno confirmaba; hoy
lo sabe después, con lo que marcó la profesora.
"""
from datetime import timedelta

from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.asistencia.models import RegistroAsistencia

from ..models import Clase
from ..permisos import gestion_requerida, profesor_o_gestion


@profesor_o_gestion
def asistencia(request):
    """Puente: cualquier enlace viejo lleva al portal de profesoras."""
    return redirect('profesoras:panel')


# Rangos del filtro. El valor es cuántos días hacia atrás mirar; None es
# todo el histórico.
RANGOS = {
    'semana': ('Últimos 7 días', 7),
    'mes': ('Últimos 30 días', 30),
    'trimestre': ('Últimos 90 días', 90),
    'todo': ('Todo el histórico', None),
}


@gestion_requerida
def asistencia_resumen(request):
    """Cuántos asistieron a cada clase, sesión por sesión."""
    hoy = timezone.localdate()

    clase_id = request.GET.get('clase', '')
    rango = request.GET.get('rango', 'mes')
    if rango not in RANGOS:
        rango = 'mes'

    registros = RegistroAsistencia.objects.select_related('clase')

    _, dias = RANGOS[rango]
    if dias is not None:
        registros = registros.filter(fecha__gte=hoy - timedelta(days=dias))

    if clase_id.isdigit():
        registros = registros.filter(clase_id=int(clase_id))

    # Una fila por clase y fecha, con los tres estados contados de una
    # sola pasada. Agrupar en Python obligaría a traerse todas las marcas.
    sesiones = (
        registros
        .values('clase_id', 'clase__nombre', 'clase__hora_inicio', 'fecha')
        .annotate(
            presentes=Count('id', filter=Q(estado=RegistroAsistencia.Estado.PRESENTE)),
            ausentes=Count('id', filter=Q(estado=RegistroAsistencia.Estado.AUSENTE)),
            justificados=Count('id', filter=Q(estado=RegistroAsistencia.Estado.JUSTIFICADO)),
            marcados=Count('id'),
        )
        .order_by('-fecha', 'clase__hora_inicio')
    )

    etiquetas = dict(Clase.Estilo.choices)

    # Cuántos hay inscritos hoy en cada clase. Es el dato de hoy, no el de
    # la fecha de la sesión: nadie guarda cuántos había inscritos hace un
    # mes, y fingir que sí sería peor que no mostrarlo.
    inscritos = {
        c.pk: c.inscritos
        for c in Clase.objects.prefetch_related('inscripciones__alumno')
    }

    filas = []
    for s in sesiones[:300]:
        total = inscritos.get(s['clase_id'], 0)
        filas.append({
            'clase_id': s['clase_id'],
            'clase': etiquetas.get(s['clase__nombre'], s['clase__nombre']),
            'hora': s['clase__hora_inicio'],
            'fecha': s['fecha'],
            'presentes': s['presentes'],
            'ausentes': s['ausentes'],
            'justificados': s['justificados'],
            'marcados': s['marcados'],
            'inscritos': total,
            'porcentaje': round(s['presentes'] / s['marcados'] * 100) if s['marcados'] else 0,
        })

    totales = {
        'sesiones': len(filas),
        'presentes': sum(f['presentes'] for f in filas),
        'ausentes': sum(f['ausentes'] for f in filas),
        'justificados': sum(f['justificados'] for f in filas),
    }
    marcados = totales['presentes'] + totales['ausentes'] + totales['justificados']
    totales['porcentaje'] = (
        round(totales['presentes'] / marcados * 100) if marcados else 0
    )

    return render(request, 'gestion/asistencia/resumen.html', {
        'activo': 'asistencia',
        'filas': filas,
        'totales': totales,
        'clases': Clase.objects.filter(activa=True),
        'rangos': [(k, v[0]) for k, v in RANGOS.items()],
        'clase_activa': clase_id,
        'rango_activo': rango,
        'hay_filtro': bool(clase_id) or rango != 'mes',
    })
