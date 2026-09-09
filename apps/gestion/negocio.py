# -*- coding: utf-8 -*-
"""Reglas que vigilan la salud del negocio.

Cada función revisa una cosa y devuelve cuántas alertas creó. Ninguna
crea alertas repetidas: se ejecutan todos los días desde el cron y si
avisaran de nuevo lo mismo, el panel se llenaría de ruido y en una
semana nadie lo miraría.
"""
import logging
from datetime import datetime, time, timedelta

from django.db.models import Count
from django.utils import timezone

from . import servicios
from .models import (AlertaNegocio, Alumno, ConfiguracionAlertas, Suscripcion)

logger = logging.getLogger(__name__)

# Días de atraso a partir de los cuales un pago deja de ser "se le pasó"
# y pasa a ser "hay que llamarlo".
DIAS_ATRASO_CRITICO = 15
DIAS_AUSENCIA = 14
# Cuánto tiene que caer la semana para que valga la pena avisar. Bajo 40%
# se dispararía casi todas las semanas por variación normal.
CAIDA_MINIMA = 40


def _pesos(monto):
    """1520000 -> '1.520.000'. El formato chileno, sin decimales."""
    return f'{int(monto):,}'.replace(',', '.')


def _ya_existe(tipo, desde, **filtros):
    """¿Se avisó de esto mismo hace poco?"""
    return AlertaNegocio.objects.filter(
        tipo=tipo, creada_en__gte=desde, **filtros
    ).exists()


# ---------------------------------------------------------------------------
# a) Meta mensual de ingresos alcanzada
# ---------------------------------------------------------------------------
def revisar_meta_mensual():
    """Avisa la primera vez que los ingresos del mes pasan la meta."""
    config = ConfiguracionAlertas.obtener()
    meta = config.meta_mensual_clp
    if not meta:
        return 0   # Sin meta configurada no hay nada que comparar.

    hoy = timezone.localdate()
    inicio, fin = servicios.rango_mes(hoy)
    ingresos = servicios.ingresos_entre(inicio, fin)

    if ingresos < meta:
        return 0

    # Una sola vez por mes: se busca desde el día 1 y no en los últimos
    # 30 días, para que el mes nuevo pueda volver a avisar aunque el
    # aviso anterior sea reciente.
    desde_el_uno = timezone.make_aware(datetime.combine(inicio, time.min))
    if _ya_existe(AlertaNegocio.Tipo.META_MENSUAL_ALCANZADA, desde_el_uno):
        return 0

    AlertaNegocio.objects.create(
        tipo=AlertaNegocio.Tipo.META_MENSUAL_ALCANZADA,
        severidad=AlertaNegocio.Severidad.INFO,
        mensaje=f'Meta mensual alcanzada: ${_pesos(ingresos)} '
                f'de ${_pesos(meta)}',
        datos_json={
            'ingresos': int(ingresos),
            'meta': int(meta),
            'mes': inicio.strftime('%Y-%m'),
            'dia_del_mes': hoy.day,
        },
    )
    return 1


# ---------------------------------------------------------------------------
# b) Caída de inscripciones
# ---------------------------------------------------------------------------
def revisar_caida_inscripciones():
    """Compara los alumnos nuevos de la semana contra las 4 anteriores."""
    hoy = timezone.localdate()
    inicio_semana = hoy - timedelta(days=7)

    def nuevos_entre(desde, hasta):
        return Alumno.objects.filter(
            fecha_ingreso__gte=desde, fecha_ingreso__lt=hasta).count()

    esta_semana = nuevos_entre(inicio_semana, hoy + timedelta(days=1))

    previas = [
        nuevos_entre(inicio_semana - timedelta(days=7 * (n + 1)),
                     inicio_semana - timedelta(days=7 * n))
        for n in range(4)
    ]
    promedio = sum(previas) / 4

    # Con menos de un alumno por semana de referencia, cualquier número
    # da porcentajes enormes que no significan nada. Mejor no avisar.
    if promedio < 1:
        return 0

    caida = round((promedio - esta_semana) / promedio * 100)
    if caida < CAIDA_MINIMA:
        return 0

    # Una por semana: si no, avisaría todos los días de la misma caída.
    if _ya_existe(AlertaNegocio.Tipo.CAIDA_INSCRIPCIONES,
                  timezone.now() - timedelta(days=7)):
        return 0

    AlertaNegocio.objects.create(
        tipo=AlertaNegocio.Tipo.CAIDA_INSCRIPCIONES,
        severidad=AlertaNegocio.Severidad.ATENCION,
        mensaje=f'Las inscripciones bajaron un {caida}% esta semana '
                f'comparado con el promedio reciente',
        datos_json={
            'esta_semana': esta_semana,
            'promedio_previo': round(promedio, 1),
            'caida_porcentaje': caida,
            'semanas_comparadas': previas,
        },
    )
    return 1


# ---------------------------------------------------------------------------
# c) Alumno ausente hace mucho
# ---------------------------------------------------------------------------
def revisar_ausencias_prolongadas(dias=DIAS_AUSENCIA):
    """Alumnos con plan al día que llevan dos semanas sin aparecer.

    Existe también una Alerta (la de tarea, que alguien gestiona y
    cierra). Esta es la lectura de negocio del mismo hecho: sirve para
    ver el patrón —cuántos se están yendo— y no para llamar a uno.
    """
    creadas = 0
    # Un mes de gracia entre avisos del mismo alumno: si sigue sin venir,
    # repetirlo cada día no aporta nada nuevo.
    desde = timezone.now() - timedelta(days=30)

    for caso in servicios.alumnos_ausentes(dias):
        alumno = caso['alumno']
        if AlertaNegocio.objects.filter(
                tipo=AlertaNegocio.Tipo.ALUMNO_AUSENTE_PROLONGADO,
                creada_en__gte=desde,
                datos_json__alumno_id=alumno.id).exists():
            continue

        AlertaNegocio.objects.create(
            tipo=AlertaNegocio.Tipo.ALUMNO_AUSENTE_PROLONGADO,
            severidad=AlertaNegocio.Severidad.ATENCION,
            mensaje=f'{alumno.nombre_completo} lleva {caso["dias"]} días '
                    f'sin venir y tiene el plan al día',
            datos_json={
                'alumno_id': alumno.id,
                'alumno': alumno.nombre_completo,
                'dias_sin_venir': caso['dias'],
                'ultima_asistencia': (caso['ultima'].isoformat()
                                      if caso['ultima'] else None),
            },
        )
        creadas += 1
    return creadas


# ---------------------------------------------------------------------------
# d) Pago atrasado crítico
# ---------------------------------------------------------------------------
def revisar_pagos_atrasados(dias=DIAS_ATRASO_CRITICO):
    """Planes vencidos hace más de dos semanas y sin renovar.

    Se diferencia de la alerta de vencimiento en el momento: aquella
    avisa antes de que venza, para que renueve. Esta avisa cuando ya
    pasó tiempo y no renovó, que es otra conversación.
    """
    hoy = timezone.localdate()
    corte = hoy - timedelta(days=dias)
    creadas = 0
    desde = timezone.now() - timedelta(days=30)

    vencidas = (
        Suscripcion.objects
        .filter(estado=Suscripcion.Estado.VENCIDA,
                fecha_vencimiento__lte=corte,
                alumno__eliminado=False,
                alumno__estado=Alumno.Estado.ACTIVO)
        .select_related('alumno', 'plan')
        .order_by('alumno_id', '-fecha_vencimiento')
    )

    vistos = set()
    for suscripcion in vencidas:
        alumno = suscripcion.alumno
        # Un alumno puede arrastrar varias suscripciones vencidas; se
        # avisa por la más reciente y no una vez por cada una.
        if alumno.id in vistos:
            continue
        vistos.add(alumno.id)

        # Si ya renovó, su plan vigente lo deja fuera aunque el anterior
        # siga marcado como vencido.
        if alumno.suscripcion_vigente:
            continue
        if AlertaNegocio.objects.filter(
                tipo=AlertaNegocio.Tipo.PAGO_ATRASADO_CRITICO,
                creada_en__gte=desde,
                datos_json__alumno_id=alumno.id).exists():
            continue

        atraso = (hoy - suscripcion.fecha_vencimiento).days
        AlertaNegocio.objects.create(
            tipo=AlertaNegocio.Tipo.PAGO_ATRASADO_CRITICO,
            severidad=AlertaNegocio.Severidad.URGENTE,
            mensaje=f'{alumno.nombre_completo} lleva {atraso} días con el '
                    f'plan vencido y sin renovar',
            datos_json={
                'alumno_id': alumno.id,
                'alumno': alumno.nombre_completo,
                'dias_atraso': atraso,
                'plan': suscripcion.plan.nombre,
                'vencio_el': suscripcion.fecha_vencimiento.isoformat(),
            },
        )
        creadas += 1
    return creadas


# ---------------------------------------------------------------------------
# e) Alumno nuevo
# ---------------------------------------------------------------------------
def registrar_alumno_nuevo(alumno):
    """Se llama al inscribir. No va en el cron: es un hecho, no una revisión."""
    return AlertaNegocio.objects.create(
        tipo=AlertaNegocio.Tipo.NUEVO_ALUMNO,
        severidad=AlertaNegocio.Severidad.INFO,
        mensaje=f'{alumno.nombre_completo} se inscribió en el estudio',
        datos_json={'alumno_id': alumno.id, 'alumno': alumno.nombre_completo},
    )


# ---------------------------------------------------------------------------
# Todas juntas, para el cron
# ---------------------------------------------------------------------------
def revisar_todo():
    """Corre las cuatro revisiones. Una que falle no detiene al resto."""
    resultados = {}
    for nombre, funcion in [
        ('meta_mensual', revisar_meta_mensual),
        ('caida_inscripciones', revisar_caida_inscripciones),
        ('ausencias', revisar_ausencias_prolongadas),
        ('pagos_atrasados', revisar_pagos_atrasados),
    ]:
        try:
            resultados[nombre] = funcion()
        except Exception:
            logger.exception('[negocio] %s falló', nombre)
            resultados[nombre] = None
    return resultados


# ---------------------------------------------------------------------------
# Datos del resumen semanal
# ---------------------------------------------------------------------------
def resumen_semanal(referencia=None):
    """Los números de los últimos 7 días, contra los 7 anteriores."""
    from apps.asistencia.models import RegistroAsistencia

    hoy = referencia or timezone.localdate()
    inicio = hoy - timedelta(days=6)          # la semana incluye hoy
    inicio_previa = inicio - timedelta(days=7)

    ingresos = servicios.ingresos_entre(inicio, hoy)
    ingresos_previos = servicios.ingresos_entre(inicio_previa,
                                                inicio - timedelta(days=1))

    nuevos = Alumno.objects.filter(
        fecha_ingreso__gte=inicio, fecha_ingreso__lte=hoy)

    # La clase con más y con menos asistencia de la semana. Se cuentan
    # solo los presentes; las clases sin ningún registro no aparecen,
    # porque "cero asistentes" y "nadie pasó lista" son cosas distintas
    # y confundirlas haría ver como fracaso un olvido administrativo.
    conteo = list(
        RegistroAsistencia.objects
        .filter(fecha__gte=inicio, fecha__lte=hoy,
                estado=RegistroAsistencia.Estado.PRESENTE)
        .values('clase__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    return {
        'desde': inicio,
        'hasta': hoy,
        'ingresos': ingresos,
        'ingresos_previos': ingresos_previos,
        'variacion_ingresos': servicios.variacion(ingresos, ingresos_previos),
        'alumnos_nuevos': nuevos.count(),
        'nombres_nuevos': list(
            nuevos.values_list('nombre_completo', flat=True)[:8]),
        'alertas_negocio': AlertaNegocio.objects.filter(
            creada_en__date__gte=inicio).count(),
        'clase_top': conteo[0] if conteo else None,
        'clase_baja': conteo[-1] if len(conteo) > 1 else None,
    }
