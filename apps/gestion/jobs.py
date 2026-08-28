"""Trabajos automáticos del sistema.

Cada función es independiente y se puede correr a mano. Ninguna lanza
excepciones hacia arriba: si una falla, el resto del día sigue funcionando
y el error queda en el log.

Horarios:
    00:01  marcar los planes vencidos
    08:00  recordatorio de clases a las profesoras
    09:00  alertas de vencimiento + avisos a alumnos + resumen al equipo
           + saludos de cumpleaños + revisión de ausencias
    18:00  recordatorio de la clase de mañana a los alumnos
    día 1  informe mensual al dueño
"""
import logging

from django.utils import timezone

from . import correos, servicios

logger = logging.getLogger(__name__)


def _seguro(nombre, funcion, *args, **kwargs):
    """Corre un trabajo y registra el resultado sin dejar que reviente."""
    try:
        resultado = funcion(*args, **kwargs)
        logger.info('[cron] %s: %s', nombre, resultado)
        return resultado
    except Exception:
        logger.exception('[cron] %s falló', nombre)
        return None


# ---------------------------------------------------------------------------
# 00:01 — poner al día el estado de los planes
# ---------------------------------------------------------------------------
def job_marcar_planes_vencidos():
    return _seguro('planes vencidos', servicios.vencer_suscripciones_pasadas)


# ---------------------------------------------------------------------------
# 08:00 — a las profesoras, sus clases de hoy
# ---------------------------------------------------------------------------
def job_recordatorio_profesoras():
    return _seguro('recordatorio profesoras', correos.enviar_recordatorios_profesoras)


# ---------------------------------------------------------------------------
# 09:00 — vencimientos, cumpleaños, ausencias y resumen
# ---------------------------------------------------------------------------
def job_alertas_vencimiento():
    resumen = _seguro('generar alertas', servicios.generar_alertas)
    if resumen is None:
        return None
    _seguro('avisos a alumnos', correos.enviar_recordatorios_del_dia, resumen)
    return resumen


def job_resumen_admin(resumen=None):
    if resumen is None:
        resumen = _seguro('generar alertas', servicios.generar_alertas)
    if resumen is None:
        return None
    return _seguro('resumen al equipo', correos.enviar_resumen, resumen)


def job_cumpleanos():
    return _seguro('cumpleaños', correos.enviar_saludos_cumpleanos)


def job_ausencias():
    salida = _seguro('detectar ausencias', servicios.generar_alertas_ausencia)
    if not salida:
        return None
    creadas, detectados = salida
    if detectados:
        _seguro('avisar ausencias', correos.avisar_ausencias, detectados)
    return creadas


def job_manana():
    """Todo lo de las 09:00, en el orden correcto."""
    resumen = job_alertas_vencimiento()
    job_resumen_admin(resumen)
    job_cumpleanos()
    job_ausencias()
    return resumen


# ---------------------------------------------------------------------------
# 18:00 — a los alumnos, su clase de mañana
# ---------------------------------------------------------------------------
def job_recordatorio_clases():
    return _seguro('recordatorio de clases', correos.enviar_recordatorios_clases)


# ---------------------------------------------------------------------------
# Día 1 — informe del mes que cerró
# ---------------------------------------------------------------------------
def job_informe_mensual():
    return _seguro('informe mensual', correos.enviar_informe_mensual)


# ---------------------------------------------------------------------------
# Registro para el planificador
# ---------------------------------------------------------------------------
TRABAJOS = [
    # (id, función, hora, minuto, día del mes)
    ('planes_vencidos', job_marcar_planes_vencidos, 0, 1, None),
    ('recordatorio_profesoras', job_recordatorio_profesoras, 8, 0, None),
    ('alertas_manana', job_manana, 9, 0, None),
    ('recordatorio_clases', job_recordatorio_clases, 18, 0, None),
    ('informe_mensual', job_informe_mensual, 8, 0, 1),
]
