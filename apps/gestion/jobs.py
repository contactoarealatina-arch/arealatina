"""Trabajos automáticos del sistema.

Cada función es independiente y se puede correr a mano. Ninguna lanza
excepciones hacia arriba: si una falla, el resto del día sigue funcionando
y el error queda en el log.

Horarios:
    00:01  marcar los planes vencidos
    08:00  recordatorio de clases a las profesoras
    09:00  alertas de vencimiento + avisos a alumnos + resumen al equipo
           + saludos de cumpleaños + revisión de ausencias
    09:05  alertas de negocio (meta, inscripciones, ausencias, atrasos)
    10:00  pedido de reseña a los alumnos con más de 3 semanas
    18:00  recordatorio de la clase de mañana a los alumnos
    23:45  revisión del tráfico del día
    lunes  resumen semanal de negocio (09:00)
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
# 09:05 — como va el negocio (despues de las alertas de las 09:00)
# ---------------------------------------------------------------------------
def job_alertas_negocio():
    """Meta del mes, inscripciones, ausencias y pagos muy atrasados."""
    from . import negocio
    return _seguro('alertas de negocio', negocio.revisar_todo)


# ---------------------------------------------------------------------------
# 23:45 — el trafico del dia que termina
# ---------------------------------------------------------------------------
def job_revisar_trafico():
    """Compara las visitas de hoy con el promedio de la semana.

    Va casi a medianoche y no en la manana a proposito: a las 09:00 el
    dia recien empieza y cualquier comparacion daria "caida del 90%"
    todos los dias.
    """
    from . import sistema
    return _seguro('revisar trafico', sistema.revisar_todo)


# ---------------------------------------------------------------------------
# Lunes 09:00 — como fue la semana
# ---------------------------------------------------------------------------
def job_resumen_semanal():
    return _seguro('resumen semanal', correos.enviar_resumen_semanal)


# ---------------------------------------------------------------------------
# Registro para el planificador
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 10:00 — pedir resena a quien ya lleva tiempo y viene seguido
# ---------------------------------------------------------------------------
def job_pedir_resenas():
    """Le pide su opinion a los alumnos que ya conocen la academia.

    Filtra por dos cosas a la vez, y las dos importan:
      · Antiguedad: al menos tres semanas desde que se inscribio
      · Asistencia real: al menos tres clases marcadas como presente

    Lo segundo es lo que evita pedirle una resena a alguien que se
    inscribio y nunca aparecio. Ese correo solo consigue molestar, y en el
    peor caso una estrella.
    """
    from datetime import timedelta

    from django.conf import settings

    from apps.asistencia.models import RegistroAsistencia

    from .models import Alumno, CorreoEnviado

    if not settings.ACADEMIA.get('google_resenas'):
        return 'sin enlace de Google configurado'

    hoy = timezone.localdate()
    limite = hoy - timedelta(weeks=correos.SEMANAS_ANTES_DE_PEDIR)

    ya_pedido = set(
        CorreoEnviado.objects
        .filter(tipo=CorreoEnviado.Tipo.RESENA, enviado=True)
        .values_list('alumno_id', flat=True)
    )

    candidatos = (
        Alumno.objects
        .filter(estado=Alumno.Estado.ACTIVO, fecha_ingreso__lte=limite)
        .exclude(email='')
        .exclude(pk__in=ya_pedido)
    )

    enviados = omitidos = 0
    for alumno in candidatos:
        asistencias = RegistroAsistencia.objects.filter(
            alumno=alumno, estado=RegistroAsistencia.Estado.PRESENTE
        ).count()

        if asistencias < correos.CLASES_MINIMAS:
            omitidos += 1
            continue

        semanas = max((hoy - alumno.fecha_ingreso).days // 7, 1)
        ok, _ = correos.enviar_pedido_resena(alumno, semanas, asistencias)
        enviados += int(ok)
        omitidos += int(not ok)

    return f'{enviados} pedidos enviados, {omitidos} omitidos'


TRABAJOS = [
    # (id, función, hora, minuto, día del mes, día de la semana)
    ('planes_vencidos', job_marcar_planes_vencidos, 0, 1, None, None),
    ('recordatorio_profesoras', job_recordatorio_profesoras, 8, 0, None, None),
    ('alertas_manana', job_manana, 9, 0, None, None),
    ('alertas_negocio', job_alertas_negocio, 9, 5, None, None),
    ('pedir_resenas', job_pedir_resenas, 10, 0, None, None),
    ('recordatorio_clases', job_recordatorio_clases, 18, 0, None, None),
    ('revisar_trafico', job_revisar_trafico, 23, 45, None, None),
    ('resumen_semanal', job_resumen_semanal, 9, 0, None, 'mon'),
    ('informe_mensual', job_informe_mensual, 8, 0, 1, None),
]
