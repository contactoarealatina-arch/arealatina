"""Módulo 1 — Dashboard principal."""
from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone

from ..models import Alumno, Clase, ConfiguracionAlertas, Pago, Suscripcion
from ..permisos import gestion_requerida
from .. import servicios


@gestion_requerida
def dashboard(request):
    hoy = timezone.localdate()
    inicio_mes, fin_mes = servicios.rango_mes(hoy)
    inicio_anterior, fin_anterior = servicios.mes_anterior(hoy)
    dias_aviso = ConfiguracionAlertas.obtener().dias_anticipacion

    # Las suscripciones vencidas se marcan al entrar: así los números del
    # panel siempre cuadran aunque el cron no haya corrido hoy.
    servicios.vencer_suscripciones_pasadas()

    # ------------------------------------------------------------------
    # Métricas
    # ------------------------------------------------------------------
    activos = Alumno.objects.filter(estado=Alumno.Estado.ACTIVO)
    total_activos = activos.count()

    # Comparación honesta: cuántos de los activos de hoy ya estaban en la
    # academia al cierre del mes pasado.
    activos_mes_anterior = activos.filter(fecha_ingreso__lte=fin_anterior).count()
    nuevos_del_mes = activos.filter(fecha_ingreso__gte=inicio_mes).count()

    ingresos_mes = servicios.ingresos_entre(inicio_mes, fin_mes)
    ingresos_anterior = servicios.ingresos_entre(inicio_anterior, fin_anterior)

    vencidos = Alumno.objects.filter(
        estado=Alumno.Estado.ACTIVO,
        suscripciones__estado=Suscripcion.Estado.VENCIDA,
    ).exclude(
        suscripciones__estado=Suscripcion.Estado.ACTIVA,
        suscripciones__fecha_vencimiento__gte=hoy,
    ).distinct()

    por_vencer_qs = Suscripcion.objects.filter(
        estado=Suscripcion.Estado.ACTIVA,
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=hoy + timedelta(days=dias_aviso),
        alumno__eliminado=False,
    ).select_related('alumno', 'plan').order_by('fecha_vencimiento')

    # ------------------------------------------------------------------
    # Gráficos
    # ------------------------------------------------------------------
    serie_ingresos = servicios.ingresos_por_mes(6)
    distribucion = servicios.alumnos_por_clase()

    contexto = {
        'activo': 'dashboard',
        'hoy': hoy,

        'total_activos': total_activos,
        'variacion_alumnos': servicios.variacion(total_activos, activos_mes_anterior),
        'nuevos_del_mes': nuevos_del_mes,

        'ingresos_mes': ingresos_mes,
        'variacion_ingresos': servicios.variacion(ingresos_mes, ingresos_anterior),
        'ingresos_anterior': ingresos_anterior,

        'total_vencidos': vencidos.count(),
        'total_por_vencer': por_vencer_qs.count(),
        'dias_aviso': dias_aviso,
        'clases_activas': Clase.objects.filter(activa=True).count(),
        'promedio_asistencia': servicios.promedio_asistencia(inicio_mes, fin_mes),

        'dias_cierre': servicios.dias_para_cerrar_mes(hoy),
        'nombre_mes': servicios.nombre_mes(hoy),

        'top_por_vencer': por_vencer_qs[:5],
        'ultimos_pagos': Pago.objects.select_related('alumno')[:5],
        'ultimos_alumnos': Alumno.objects.order_by('-fecha_ingreso', '-id')[:5],

        # Los datos van como dict: json_script se encarga de serializarlos
        # de forma segura en la plantilla.
        'grafico_ingresos': {
            'etiquetas': [m['etiqueta'] for m in serie_ingresos],
            'datos': [m['total'] for m in serie_ingresos],
        },
        'grafico_distribucion': {
            'etiquetas': [d['etiqueta'] for d in distribucion],
            'datos': [d['total'] for d in distribucion],
        },
        'hay_distribucion': bool(distribucion),
    }
    return render(request, 'gestion/dashboard.html', contexto)
