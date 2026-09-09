# -*- coding: utf-8 -*-
"""Vigilancia del sistema: tráfico, errores y seguridad.

Es la contraparte técnica de negocio.py. Lo que hay acá no le dice nada
al dueño del estudio y se lo dice todo a quien mantiene el sistema, por
eso vive en su propio panel y solo lo ve el superadmin.
"""
import logging
from datetime import timedelta

from django.db.models import Avg
from django.utils import timezone

from .models import AlertaSistema, AuditLog, EstadisticaDiaria

logger = logging.getLogger(__name__)

# Cuánto tiene que moverse el tráfico para que valga la pena avisar.
CAIDA_MINIMA = 50      # bajo esto, es variación de un día cualquiera
PICO_MINIMO = 300      # sobre esto, o se viralizó algo o alguien raspa el sitio
DIAS_REFERENCIA = 7
# Con menos visitas que esto, los porcentajes son ruido: pasar de 2 a 8
# visitas es un 400% y no significa nada.
PISO_PARA_COMPARAR = 10


def revisar_trafico(referencia=None):
    """Compara las visitas de hoy contra el promedio de la semana."""
    hoy = referencia or timezone.localdate()

    fila = EstadisticaDiaria.objects.filter(fecha=hoy).first()
    visitas_hoy = fila.visitas_estimadas if fila else 0

    previos = EstadisticaDiaria.objects.filter(
        fecha__lt=hoy, fecha__gte=hoy - timedelta(days=DIAS_REFERENCIA))
    promedio = previos.aggregate(p=Avg('visitas_estimadas'))['p'] or 0

    # Sin días previos suficientes no hay contra qué comparar. El sistema
    # recién instalado no tiene por qué avisar de nada.
    if previos.count() < 3 or promedio < PISO_PARA_COMPARAR:
        return 0

    porcentaje = round(visitas_hoy / promedio * 100)

    if porcentaje >= PICO_MINIMO:
        tipo = AlertaSistema.Tipo.TRAFICO_PICO
        mensaje = f'Tráfico inusual detectado: {porcentaje}% sobre el promedio'
        severidad = AlertaSistema.Severidad.ATENCION
    elif porcentaje <= (100 - CAIDA_MINIMA):
        tipo = AlertaSistema.Tipo.TRAFICO_CAIDA
        mensaje = (f'Caída de tráfico: {100 - porcentaje}% bajo el promedio, '
                   f'verificar que el sitio esté funcionando bien')
        severidad = AlertaSistema.Severidad.ATENCION
    else:
        return 0

    # Una por día y por tipo: el cron corre a diario y repetir el mismo
    # aviso llenaría el panel.
    if AlertaSistema.objects.filter(tipo=tipo, creada_en__date=hoy).exists():
        return 0

    AlertaSistema.objects.create(
        tipo=tipo,
        severidad=severidad,
        mensaje=mensaje,
        detalle=f'Hoy: {visitas_hoy} visitas. Promedio de los últimos '
                f'{previos.count()} días: {promedio:.1f}.',
        datos_json={
            'visitas_hoy': visitas_hoy,
            'promedio': round(promedio, 1),
            'porcentaje': porcentaje,
            'dias_comparados': previos.count(),
        },
    )
    return 1


def registrar_error_servidor(mensaje, detalle=''):
    """Deja constancia de un 500 en el panel, además del correo de Django.

    Django ya manda un correo a ADMINS cuando una vista revienta. Esto
    lo complementa: el correo se lee una vez y se pierde en la bandeja,
    la fila queda para poder contar cuántos van y desde cuándo.
    """
    return AlertaSistema.objects.create(
        tipo=AlertaSistema.Tipo.ERROR_SERVIDOR,
        severidad=AlertaSistema.Severidad.URGENTE,
        mensaje=mensaje[:250],
        detalle=detalle,
    )


def revisar_todo():
    """Lo que corre el cron. Un fallo no detiene al resto."""
    resultados = {}
    for nombre, funcion in [('trafico', revisar_trafico)]:
        try:
            resultados[nombre] = funcion()
        except Exception:
            logger.exception('[sistema] %s falló', nombre)
            resultados[nombre] = None
    return resultados


# ---------------------------------------------------------------------------
# La vista unificada
# ---------------------------------------------------------------------------
def linea_de_tiempo(limite=60, tipo=''):
    """Todo lo técnico en una sola lista ordenada por fecha.

    Junta dos orígenes que viven en tablas distintas —las alertas de
    sistema y el registro de auditoría— porque para quien revisa "qué
    está pasando" son lo mismo: cosas que ocurrieron, en orden. Tenerlas
    en dos pantallas obligaría a cruzar horas a mano.
    """
    eventos = []

    if tipo != 'SEGURIDAD':
        consulta = AlertaSistema.objects.all()
        if tipo:
            consulta = consulta.filter(tipo=tipo)
        for alerta in consulta[:limite]:
            eventos.append({
                'cuando': alerta.creada_en,
                'origen': alerta.get_tipo_display(),
                'tipo': alerta.tipo,
                'icono': alerta.icono,
                'severidad': alerta.severidad,
                'mensaje': alerta.mensaje,
                'detalle': alerta.detalle,
                'quien': '',
                'ip': alerta.datos_json.get('ip', ''),
                'id_alerta': alerta.id,
                'leida': alerta.leida,
            })

    if not tipo or tipo == 'SEGURIDAD':
        sospechosos = (
            AuditLog.objects
            .filter(sospechoso=True)
            .select_related('usuario')[:limite]
        )
        fallidos = (
            AuditLog.objects
            .filter(accion=AuditLog.Accion.LOGIN_FALLIDO)
            .select_related('usuario')[:limite]
        )
        vistos = set()
        for registro in list(sospechosos) + list(fallidos):
            if registro.id in vistos:
                continue
            vistos.add(registro.id)
            eventos.append({
                'cuando': registro.timestamp,
                'origen': registro.get_accion_display(),
                'tipo': AlertaSistema.Tipo.SEGURIDAD,
                'icono': 'bi-shield-exclamation',
                'severidad': (AlertaSistema.Severidad.URGENTE
                              if registro.sospechoso
                              else AlertaSistema.Severidad.ATENCION),
                'mensaje': registro.descripcion or registro.get_accion_display(),
                'detalle': registro.user_agent,
                'quien': (registro.usuario.get_full_name()
                          or registro.usuario.username) if registro.usuario else '',
                'ip': registro.ip or '',
                'id_alerta': None,
                'leida': True,   # la auditoría no se marca, solo se lee
            })

    eventos.sort(key=lambda e: e['cuando'], reverse=True)
    return eventos[:limite]
