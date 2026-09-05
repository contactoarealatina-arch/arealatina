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
    return [
        {'etiqueta': f['nombre'], 'total': f['total']}
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


# ---------------------------------------------------------------------------
# Sesiones: una clase se repite en ciertos días; cada ocurrencia es una sesión
# ---------------------------------------------------------------------------
CODIGOS_DIA = ['LU', 'MA', 'MI', 'JU', 'VI', 'SA', 'DO']


def codigo_dia(fecha):
    """Lunes -> 'LU'. El orden de CODIGOS_DIA calza con date.weekday()."""
    return CODIGOS_DIA[fecha.weekday()]


def clase_ocurre_en(clase, fecha):
    return codigo_dia(fecha) in clase.dias_lista


def clases_del_dia(clases, fecha=None):
    """De un conjunto de clases, las que tocan ese día."""
    fecha = fecha or timezone.localdate()
    return [c for c in clases if clase_ocurre_en(c, fecha)]


def sesiones_proximas(clases, dias=7, desde=None):
    """Cada ocurrencia de cada clase en el rango, ordenada por fecha y hora.

    Devuelve dicts {clase, fecha, es_hoy} en vez de objetos: no hay modelo de
    sesión, se calculan a partir de los días de la clase.
    """
    desde = desde or timezone.localdate()
    hoy = timezone.localdate()
    sesiones = []
    for salto in range(dias):
        fecha = desde + timedelta(days=salto)
        for clase in clases_del_dia(clases, fecha):
            sesiones.append({'clase': clase, 'fecha': fecha, 'es_hoy': fecha == hoy})
    sesiones.sort(key=lambda s: (s['fecha'], s['clase'].hora_inicio))
    return sesiones


def proxima_sesion(clases, desde=None):
    """La siguiente ocurrencia, mirando hasta 14 días adelante."""
    ahora = timezone.localtime()
    for sesion in sesiones_proximas(clases, dias=14, desde=desde):
        if sesion['fecha'] > ahora.date():
            return sesion
        if sesion['fecha'] == ahora.date() and sesion['clase'].hora_fin > ahora.time():
            return sesion
    return None


def inicio_sesion(sesion):
    """datetime con zona horaria del comienzo de una sesión."""
    from datetime import datetime

    ingenuo = datetime.combine(sesion['fecha'], sesion['clase'].hora_inicio)
    return timezone.make_aware(ingenuo, timezone.get_current_timezone())


def puede_confirmar(sesion):
    """Se confirma hasta una hora antes de que empiece."""
    return timezone.now() < inicio_sesion(sesion) - timedelta(hours=1)


# ---------------------------------------------------------------------------
# Retención: quién dejó de venir sin avisar
# ---------------------------------------------------------------------------
DIAS_AUSENCIA = 14


def alumnos_ausentes(dias=DIAS_AUSENCIA):
    """Alumnos activos con plan vigente que llevan tiempo sin aparecer.

    Es la señal más temprana de que alguien se está yendo: primero dejan de
    venir, y recién semanas después no renuevan. Para entonces ya se fueron.
    """
    from apps.asistencia.models import RegistroAsistencia

    from .models import Alumno

    hoy = timezone.localdate()
    corte = hoy - timedelta(days=dias)

    encontrados = []
    candidatos = Alumno.objects.filter(estado=Alumno.Estado.ACTIVO).prefetch_related(
        'inscripciones__clase')

    for alumno in candidatos:
        # Sin plan vigente ya lo cubre la alerta de vencimiento.
        if not alumno.suscripcion_vigente:
            continue
        # Sin clases inscritas no hay a qué faltar.
        if not alumno.inscripciones.exists():
            continue

        ultima = (
            RegistroAsistencia.objects
            .filter(alumno=alumno, estado=RegistroAsistencia.Estado.PRESENTE)
            .order_by('-fecha')
            .values_list('fecha', flat=True)
            .first()
        )

        # Recién inscrito y sin historial: se le da margen.
        referencia = ultima or alumno.fecha_ingreso
        if referencia > corte:
            continue

        faltas = list(
            RegistroAsistencia.objects
            .filter(alumno=alumno, fecha__gt=referencia)
            .exclude(estado=RegistroAsistencia.Estado.PRESENTE)
            .select_related('clase')
            .order_by('-fecha')[:8]
        )

        encontrados.append({
            'alumno': alumno,
            'ultima': ultima,
            'dias': (hoy - referencia).days,
            'faltas': faltas,
        })

    encontrados.sort(key=lambda x: -x['dias'])
    return encontrados


def generar_alertas_ausencia(dias=DIAS_AUSENCIA):
    """Crea la alerta de ausencia prolongada. Una sola por episodio."""
    from .models import Alerta

    detectados = alumnos_ausentes(dias)
    creadas = 0

    for item in detectados:
        alumno = item['alumno']
        mensaje = (
            f'Lleva {item["dias"]} días sin venir a clases '
            f'(última asistencia: '
            f'{item["ultima"]:%d/%m/%Y}).' if item['ultima']
            else f'Lleva {item["dias"]} días inscrito y nunca ha asistido.'
        )
        if _crear_alerta(Alerta.Tipo.AUSENCIA_PROLONGADA, alumno, mensaje):
            creadas += 1

    return creadas, detectados


# ---------------------------------------------------------------------------
# Cumpleaños
# ---------------------------------------------------------------------------
def cumpleaneros(fecha=None):
    from .models import Alumno

    fecha = fecha or timezone.localdate()
    return Alumno.objects.filter(
        estado=Alumno.Estado.ACTIVO,
        fecha_nacimiento__month=fecha.month,
        fecha_nacimiento__day=fecha.day,
    ).exclude(email='')


# ---------------------------------------------------------------------------
# Cierre mensual
# ---------------------------------------------------------------------------
def cierre_mensual(referencia=None):
    """Los números del mes que acaba de terminar. Todo sale de la base."""
    from apps.asistencia.models import RegistroAsistencia

    from .models import Alumno, Pago, Plan, Suscripcion

    hoy = referencia or timezone.localdate()
    inicio, fin = mes_anterior(hoy)
    inicio_previo, fin_previo = mes_anterior(inicio)

    activos_cierre = Alumno.objects.filter(
        estado=Alumno.Estado.ACTIVO, fecha_ingreso__lte=fin).count()
    activos_previo = Alumno.objects.filter(
        estado=Alumno.Estado.ACTIVO, fecha_ingreso__lte=fin_previo).count()

    nuevos = Alumno.objects.filter(fecha_ingreso__gte=inicio, fecha_ingreso__lte=fin)

    # No renovaron: se les venció dentro del mes y siguen sin plan vigente.
    sin_renovar = []
    for sus in Suscripcion.objects.filter(
        fecha_vencimiento__gte=inicio, fecha_vencimiento__lte=fin,
        alumno__eliminado=False,
    ).select_related('alumno', 'plan'):
        if not sus.alumno.suscripcion_vigente:
            sin_renovar.append(sus)

    # Asistencia por clase
    registros = RegistroAsistencia.objects.filter(fecha__gte=inicio, fecha__lte=fin)
    por_clase = {}
    for registro in registros.select_related('clase'):
        datos = por_clase.setdefault(registro.clase, {'total': 0, 'presentes': 0})
        datos['total'] += 1
        datos['presentes'] += int(registro.estado == RegistroAsistencia.Estado.PRESENTE)

    ranking = sorted(
        ({'clase': c, 'presentes': d['presentes'], 'total': d['total'],
          'porcentaje': round(d['presentes'] / d['total'] * 100) if d['total'] else 0}
         for c, d in por_clase.items()),
        key=lambda x: -x['presentes'],
    )

    total_marcas = registros.count()
    total_presentes = registros.filter(
        estado=RegistroAsistencia.Estado.PRESENTE).count()

    # Planes más contratados en el mes
    conteo = {}
    for sus in Suscripcion.objects.filter(
        fecha_inicio__gte=inicio, fecha_inicio__lte=fin
    ).select_related('plan'):
        conteo[sus.plan] = conteo.get(sus.plan, 0) + 1
    top_planes = sorted(
        ({'plan': p, 'total': n} for p, n in conteo.items()),
        key=lambda x: -x['total'],
    )[:3]

    return {
        'inicio': inicio,
        'fin': fin,
        'nombre_mes': nombre_mes(inicio),
        'ingresos': ingresos_entre(inicio, fin),
        'ingresos_previo': ingresos_entre(inicio_previo, fin_previo),
        'activos': activos_cierre,
        'activos_previo': activos_previo,
        'diferencia_alumnos': activos_cierre - activos_previo,
        'nuevos': nuevos,
        'sin_renovar': sin_renovar,
        'mejor_clase': ranking[0] if ranking else None,
        'peor_clase': ranking[-1] if len(ranking) > 1 else None,
        'asistencia_global': (round(total_presentes / total_marcas * 100)
                              if total_marcas else None),
        'top_planes': top_planes,
        'pagos_count': Pago.objects.filter(
            estado=Pago.Estado.PAGADO, fecha_pago__gte=inicio, fecha_pago__lte=fin).count(),
    }
