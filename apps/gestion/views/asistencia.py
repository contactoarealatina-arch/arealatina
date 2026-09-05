"""Asistencia vista desde la administración.

La asistencia se *pasa* desde el portal de profesoras, que está pensado
para tablet. Acá se *lee*: cuántos fueron a cada clase, quiénes, y cuánto
genera esa clase al mes.

Esta vista existe porque se eliminó la confirmación previa del alumno.
Antes el estudio sabía quién iba a venir porque el alumno confirmaba; hoy
lo sabe después, con lo que marcó la profesora.
"""
from datetime import datetime, timedelta

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.asistencia.models import RegistroAsistencia

from ..models import Alumno, Clase, Suscripcion
from ..permisos import gestion_requerida, profesor_o_gestion

POR_PAGINA = 10


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


def ingreso_mensual_de(clase):
    """Cuánto genera esta clase al mes, estimado.

    Un alumno no paga por clase: paga un plan que le da acceso a varias.
    Así que se reparte su mensualidad entre las clases en las que está
    inscrito, y la parte que le toca a esta se suma.

    Es un estimado y la pantalla lo dice. La alternativa —contar la
    mensualidad completa en cada clase— haría que la suma de todas las
    clases diera mucho más de lo que el estudio factura de verdad.
    """
    hoy = timezone.localdate()
    total = 0

    inscritos = (
        Alumno.objects.filter(inscripciones__clase=clase)
        .prefetch_related('inscripciones', 'suscripciones__plan')
        .distinct()
    )
    for alumno in inscritos:
        vigente = next(
            (s for s in alumno.suscripciones.all()
             if s.estado == Suscripcion.Estado.ACTIVA
             and s.fecha_vencimiento >= hoy),
            None,
        )
        if not vigente or not vigente.plan:
            continue

        cuantas = alumno.inscripciones.count() or 1
        total += vigente.plan.precio_clp / cuantas

    return round(total)


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

    clase_elegida = None
    if clase_id.isdigit():
        clase_elegida = Clase.objects.filter(pk=int(clase_id)).first()
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

    # Cuántos hay inscritos hoy en cada clase. Es el dato de hoy, no el de
    # la fecha de la sesión: nadie guarda cuántos había inscritos hace un
    # mes, y fingir que sí sería peor que no mostrarlo.
    inscritos = {
        c.pk: c.inscritos
        for c in Clase.objects.prefetch_related('inscripciones__alumno')
    }

    # Los totales van sobre TODO el resultado, no sobre la página: un
    # resumen que solo suma diez filas no resume nada.
    todas = list(sesiones)
    totales = {
        'sesiones': len(todas),
        'presentes': sum(s['presentes'] for s in todas),
        'ausentes': sum(s['ausentes'] for s in todas),
        'justificados': sum(s['justificados'] for s in todas),
    }
    marcados = totales['presentes'] + totales['ausentes'] + totales['justificados']
    totales['porcentaje'] = (
        round(totales['presentes'] / marcados * 100) if marcados else 0
    )

    paginador = Paginator(todas, POR_PAGINA)
    pagina = paginador.get_page(request.GET.get('page'))

    filas = []
    for s in pagina:
        filas.append({
            'clase_id': s['clase_id'],
            'clase': s['clase__nombre'],
            'hora': s['clase__hora_inicio'],
            'fecha': s['fecha'],
            'presentes': s['presentes'],
            'ausentes': s['ausentes'],
            'justificados': s['justificados'],
            'marcados': s['marcados'],
            'inscritos': inscritos.get(s['clase_id'], 0),
            'porcentaje': round(s['presentes'] / s['marcados'] * 100) if s['marcados'] else 0,
        })

    parametros = request.GET.copy()
    parametros.pop('page', None)

    return render(request, 'gestion/asistencia/resumen.html', {
        'activo': 'asistencia',
        'filas': filas,
        'pagina': pagina,
        'querystring': parametros.urlencode(),
        'totales': totales,
        'clases': Clase.objects.filter(activa=True),
        'rangos': [(k, v[0]) for k, v in RANGOS.items()],
        'clase_activa': clase_id,
        'clase_elegida': clase_elegida,
        # Solo cuando hay una clase filtrada: la ganancia de "todas las
        # clases" mezcladas no significaría nada.
        'ingreso_clase': ingreso_mensual_de(clase_elegida) if clase_elegida else None,
        'rango_activo': rango,
        'hay_filtro': bool(clase_id) or rango != 'mes',
    })


@gestion_requerida
def asistencia_sesion(request, clase_id, fecha):
    """Quién fue y quién no a una clase, un día concreto.

    Es lo que el estudio quiere mirar cuando ve que una sesión tuvo poca
    gente: no el número, sino los nombres.
    """
    clase = get_object_or_404(Clase, pk=clase_id)

    try:
        dia = datetime.fromisoformat(fecha).date()
    except (TypeError, ValueError):
        return redirect('gestion:asistencia_resumen')

    marcas = {
        r.alumno_id: r
        for r in RegistroAsistencia.objects
        .filter(clase=clase, fecha=dia)
        .select_related('alumno')
    }

    filas = []
    for inscripcion in clase.inscripciones.select_related('alumno'):
        alumno = inscripcion.alumno
        if alumno.eliminado:
            continue
        marca = marcas.get(alumno.pk)
        filas.append({
            'alumno': alumno,
            # Sin marca = la profesora no lo registró ese día. No es lo
            # mismo que ausente y no se puede mostrar como tal.
            'estado': marca.estado if marca else None,
            'observacion': marca.observacion if marca else '',
            'ya_no_inscrito': False,
        })

    # Los que estaban marcados pero ya no están inscritos: se salieron de
    # la clase después. Igual asistieron y tienen que aparecer.
    en_lista = {f['alumno'].pk for f in filas}
    for alumno_id, marca in marcas.items():
        if alumno_id not in en_lista:
            filas.append({
                'alumno': marca.alumno,
                'estado': marca.estado,
                'observacion': marca.observacion,
                'ya_no_inscrito': True,
            })

    orden = {'PRESENTE': 0, 'JUSTIFICADO': 1, 'AUSENTE': 2}
    filas.sort(key=lambda f: (orden.get(f['estado'], 3), f['alumno'].nombre_completo))

    conteo = {
        'presentes': sum(1 for f in filas if f['estado'] == 'PRESENTE'),
        'ausentes': sum(1 for f in filas if f['estado'] == 'AUSENTE'),
        'justificados': sum(1 for f in filas if f['estado'] == 'JUSTIFICADO'),
        'sin_marcar': sum(1 for f in filas if f['estado'] is None),
    }

    return render(request, 'gestion/asistencia/sesion.html', {
        'activo': 'asistencia',
        'clase': clase,
        'fecha': dia,
        'filas': filas,
        'conteo': conteo,
        'ingreso_clase': ingreso_mensual_de(clase),
        'inscritos': clase.inscritos,
    })
