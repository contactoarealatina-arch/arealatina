"""Módulo 7 — Reportes y exportaciones."""
from datetime import timedelta

from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.asistencia.models import RegistroAsistencia

from .. import excel, servicios
from ..models import Alumno, Clase, Pago, Suscripcion
from ..permisos import gestion_requerida

TIPO_EXCEL = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

REPORTES = [
    {
        'slug': 'alumnos-activos',
        'titulo': 'Alumnos activos',
        'texto': 'Ficha completa de todos los alumnos en estado activo, con su plan y estado de pago.',
        'icono': 'bi-people',
    },
    {
        'slug': 'pagos-periodo',
        'titulo': 'Pagos por período',
        'texto': 'Todos los pagos entre dos fechas, con el total cobrado al pie.',
        'icono': 'bi-cash-coin',
        'pide_fechas': True,
    },
    {
        'slug': 'asistencia',
        'titulo': 'Asistencia por clase y mes',
        'texto': 'Detalle de cada marca de asistencia del período elegido.',
        'icono': 'bi-clipboard-check',
        'pide_fechas': True,
        'pide_clase': True,
    },
    {
        'slug': 'por-vencer',
        'titulo': 'Planes por vencer (30 días)',
        'texto': 'Alumnos cuyo plan vence dentro de los próximos 30 días, con teléfono para llamarlos.',
        'icono': 'bi-hourglass-split',
    },
    {
        'slug': 'ingresos',
        'titulo': 'Ingresos mensuales',
        'texto': 'Ingresos de los últimos 12 meses, con el gráfico de barras incluido en la planilla.',
        'icono': 'bi-graph-up-arrow',
    },
]


@gestion_requerida
def reportes(request):
    hoy = timezone.localdate()
    inicio_mes, _ = servicios.rango_mes(hoy)
    return render(request, 'gestion/reportes/listado.html', {
        'activo': 'reportes',
        'reportes': REPORTES,
        'clases': Clase.objects.all(),
        'desde_defecto': inicio_mes.isoformat(),
        'hasta_defecto': hoy.isoformat(),
    })


def _rango_pedido(request):
    """Lee desde/hasta de la URL, con el mes actual como valor por defecto."""
    hoy = timezone.localdate()
    inicio_mes, fin_mes = servicios.rango_mes(hoy)

    def leer(nombre, defecto):
        valor = request.GET.get(nombre)
        if not valor:
            return defecto
        try:
            return timezone.datetime.fromisoformat(valor).date()
        except (ValueError, TypeError):
            return defecto

    return leer('desde', inicio_mes), leer('hasta', fin_mes)


@gestion_requerida
def reporte_descargar(request, slug):
    hoy = timezone.localdate()

    if slug == 'alumnos-activos':
        datos = excel.exportar_alumnos(
            Alumno.objects.filter(estado=Alumno.Estado.ACTIVO)
            .prefetch_related('inscripciones__clase', 'suscripciones__plan')
        )
        nombre = f'alumnos_activos_{hoy:%Y-%m-%d}.xlsx'

    elif slug == 'pagos-periodo':
        desde, hasta = _rango_pedido(request)
        datos = excel.exportar_pagos(
            Pago.objects.filter(fecha_pago__gte=desde, fecha_pago__lte=hasta)
            .select_related('alumno', 'registrado_por'),
            titulo='Pagos',
        )
        nombre = f'pagos_{desde:%Y-%m-%d}_a_{hasta:%Y-%m-%d}.xlsx'

    elif slug == 'asistencia':
        desde, hasta = _rango_pedido(request)
        qs = RegistroAsistencia.objects.filter(
            fecha__gte=desde, fecha__lte=hasta
        ).select_related('clase', 'alumno')
        clase = request.GET.get('clase')
        if clase:
            qs = qs.filter(clase_id=clase)
        datos = excel.exportar_asistencia(qs)
        nombre = f'asistencia_{desde:%Y-%m-%d}_a_{hasta:%Y-%m-%d}.xlsx'

    elif slug == 'por-vencer':
        datos = excel.exportar_vencimientos(
            Suscripcion.objects.filter(
                estado=Suscripcion.Estado.ACTIVA,
                fecha_vencimiento__gte=hoy,
                fecha_vencimiento__lte=hoy + timedelta(days=30),
                alumno__eliminado=False,
            ).select_related('alumno', 'plan').order_by('fecha_vencimiento')
        )
        nombre = f'por_vencer_{hoy:%Y-%m-%d}.xlsx'

    elif slug == 'ingresos':
        datos = excel.exportar_ingresos(servicios.ingresos_por_mes(12))
        nombre = f'ingresos_{hoy:%Y-%m-%d}.xlsx'

    else:
        raise Http404('Ese reporte no existe.')

    respuesta = HttpResponse(datos, content_type=TIPO_EXCEL)
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return respuesta
