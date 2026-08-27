"""Lógica compartida del módulo de gestión: fechas, alertas y exportación."""
import calendar
from datetime import date, timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from .models import Alerta, Alumno, Pago, Suscripcion

MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
         'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

MESES_LARGO = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
               'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


# ---------------------------------------------------------------------------
# Fechas
# ---------------------------------------------------------------------------
def rango_mes(referencia=None):
    """(primer_dia, ultimo_dia) del mes de la fecha dada."""
    referencia = referencia or timezone.localdate()
    primero = referencia.replace(day=1)
    ultimo = referencia.replace(day=calendar.monthrange(referencia.year, referencia.month)[1])
    return primero, ultimo


def mes_anterior(referencia=None):
    referencia = referencia or timezone.localdate()
    ultimo_dia_anterior = referencia.replace(day=1) - timedelta(days=1)
    return rango_mes(ultimo_dia_anterior)


def ultimos_meses(cantidad=6, referencia=None):
    """Lista de (primer_dia, ultimo_dia, etiqueta) del mes más viejo al actual."""
    referencia = referencia or timezone.localdate()
    meses = []
    cursor = referencia.replace(day=1)
    for _ in range(cantidad):
        inicio, fin = rango_mes(cursor)
        meses.append((inicio, fin, f'{MESES[inicio.month - 1]} {inicio.year % 100:02d}'))
        cursor = inicio - timedelta(days=1)
    return list(reversed(meses))


def nombre_mes(fecha):
    return f'{MESES_LARGO[fecha.month - 1]} de {fecha.year}'


def dias_para_cerrar_mes(referencia=None):
    referencia = referencia or timezone.localdate()
    _, ultimo = rango_mes(referencia)
    return (ultimo - referencia).days


# ---------------------------------------------------------------------------
# Consultas de dinero
# ---------------------------------------------------------------------------
def ingresos_entre(inicio, fin):
    return Pago.objects.filter(
        estado=Pago.Estado.PAGADO,
        fecha_pago__gte=inicio,
        fecha_pago__lte=fin,
    ).aggregate(total=Sum('monto_clp'))['total'] or 0


def ingresos_por_mes(cantidad=6):
    """[{'etiqueta': 'ago 26', 'total': 350000}, ...]"""
    return [
        {'etiqueta': etiqueta, 'total': ingresos_entre(inicio, fin)}
        for inicio, fin, etiqueta in ultimos_meses(cantidad)
    ]


def variacion(actual, anterior):
    """Porcentaje de variación. None si no hay base con la que comparar."""
    if not anterior:
        return None
    return round((actual - anterior) / anterior * 100)


# ---------------------------------------------------------------------------
# Distribución de alumnos por estilo
# ---------------------------------------------------------------------------
def alumnos_por_clase():
    from .models import Clase

    filas = (
        Clase.objects.filter(activa=True)
        .values('nombre')
        .annotate(total=Count('inscripciones__alumno', distinct=True))
        .order_by('nombre')
    )
    etiquetas = dict(Clase.Estilo.choices)
    return [
        {'etiqueta': etiquetas.get(f['nombre'], f['nombre']), 'total': f['total']}
        for f in filas if f['total']
    ]


# ---------------------------------------------------------------------------
# Asistencia
# ---------------------------------------------------------------------------
def promedio_asistencia(inicio=None, fin=None):
    """Porcentaje de presentes sobre el total de marcas del período."""
    from apps.asistencia.models import RegistroAsistencia

    if inicio is None or fin is None:
        inicio, fin = rango_mes()

    registros = RegistroAsistencia.objects.filter(fecha__gte=inicio, fecha__lte=fin)
    total = registros.count()
    if not total:
        return None
    presentes = registros.filter(estado=RegistroAsistencia.Estado.PRESENTE).count()
    return round(presentes / total * 100)


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------
def vencer_suscripciones_pasadas():
    """Marca como VENCIDA toda suscripción activa cuya fecha ya pasó."""
    return Suscripcion.objects.filter(
        estado=Suscripcion.Estado.ACTIVA,
        fecha_vencimiento__lt=timezone.localdate(),
    ).update(estado=Suscripcion.Estado.VENCIDA)


def _crear_alerta(tipo, alumno, mensaje, suscripcion=None):
    """Crea la alerta solo si no hay una viva del mismo tipo para ese alumno."""
    existente = Alerta.objects.filter(tipo=tipo, alumno=alumno, gestionada=False).first()
    if existente:
        if existente.mensaje != mensaje:
            existente.mensaje = mensaje
            existente.save(update_fields=['mensaje', 'updated_at'])
        return False
    Alerta.objects.create(tipo=tipo, alumno=alumno, mensaje=mensaje, suscripcion=suscripcion)
    return True


def generar_alertas(dias_anticipacion=None):
    """Recorre la base y crea las alertas del día.

    Devuelve un resumen con las listas de alumnos afectados, que es lo que
    después se manda por correo.
    """
    from .models import ConfiguracionAlertas

    if dias_anticipacion is None:
        dias_anticipacion = ConfiguracionAlertas.obtener().dias_anticipacion

    hoy = timezone.localdate()
    vencer_suscripciones_pasadas()

    creadas = 0
    por_vencer, vencidos, sin_pago = [], [], []

    # 1. Planes que vencen dentro del plazo de anticipación
    proximas = Suscripcion.objects.filter(
        estado=Suscripcion.Estado.ACTIVA,
        fecha_vencimiento__gte=hoy,
        fecha_vencimiento__lte=hoy + timedelta(days=dias_anticipacion),
        alumno__eliminado=False,
    ).select_related('alumno', 'plan')

    for sus in proximas:
        dias = (sus.fecha_vencimiento - hoy).days
        cuando = 'hoy' if dias == 0 else f'en {dias} día{"s" if dias != 1 else ""}'
        mensaje = f'El plan {sus.plan.nombre} vence {cuando} ({sus.fecha_vencimiento:%d/%m/%Y}).'
        if _crear_alerta(Alerta.Tipo.VENCIMIENTO_PROXIMO, sus.alumno, mensaje, sus):
            creadas += 1
        por_vencer.append({'alumno': sus.alumno, 'plan': sus.plan.nombre,
                           'vence': sus.fecha_vencimiento, 'dias': dias})

    # 2. Planes ya vencidos
    caducadas = Suscripcion.objects.filter(
        estado=Suscripcion.Estado.VENCIDA,
        fecha_vencimiento__gte=hoy - timedelta(days=60),
        alumno__eliminado=False,
    ).select_related('alumno', 'plan')

    for sus in caducadas:
        # Si ya renovó, no se le molesta.
        if sus.alumno.suscripcion_vigente:
            continue
        dias = (hoy - sus.fecha_vencimiento).days
        mensaje = f'El plan {sus.plan.nombre} venció hace {dias} día{"s" if dias != 1 else ""}.'
        if _crear_alerta(Alerta.Tipo.PLAN_VENCIDO, sus.alumno, mensaje, sus):
            creadas += 1
        vencidos.append({'alumno': sus.alumno, 'plan': sus.plan.nombre,
                         'vencio': sus.fecha_vencimiento, 'dias': dias})

    # 3. Alumnos activos sin ningún pago del mes en curso
    inicio_mes, fin_mes = rango_mes(hoy)
    activos = Alumno.objects.filter(estado=Alumno.Estado.ACTIVO)
    for alumno in activos:
        tiene_pago = alumno.pagos.filter(
            estado=Pago.Estado.PAGADO,
            fecha_pago__gte=inicio_mes,
            fecha_pago__lte=fin_mes,
        ).exists()
        if tiene_pago:
            continue
        mensaje = f'Sin pagos registrados en {nombre_mes(hoy)}.'
        if _crear_alerta(Alerta.Tipo.PAGO_PENDIENTE, alumno, mensaje):
            creadas += 1
        sin_pago.append({'alumno': alumno})

    return {
        'creadas': creadas,
        'por_vencer': por_vencer,
        'vencidos': vencidos,
        'sin_pago': sin_pago,
        'fecha': hoy,
    }
