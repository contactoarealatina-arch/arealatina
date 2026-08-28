"""Portal de profesoras: panel del día, clases, historial y pasar lista."""
from datetime import datetime, timedelta

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.asistencia.models import RegistroAsistencia
from apps.gestion import servicios
from apps.gestion.auditoria import registrar
from apps.gestion.models import AuditLog, ConfirmacionAsistencia, DiaSemana

from .permisos import acceso_profesoras, clase_visible_o_404, clases_visibles, es_vista_admin


def _contexto_base(request):
    return {
        'vista_admin': es_vista_admin(request.user),
    }


def _confirmados(clase, fecha):
    return ConfirmacionAsistencia.objects.filter(clase=clase, fecha=fecha).count()


def _inscritos(clase):
    return clase.inscripciones.filter(alumno__eliminado=False).count()


# ---------------------------------------------------------------------------
# 1.1 Panel del día
# ---------------------------------------------------------------------------
@acceso_profesoras
def panel(request):
    hoy = timezone.localdate()
    mis_clases = list(clases_visibles(request.user))

    del_dia = []
    for clase in servicios.clases_del_dia(mis_clases, hoy):
        del_dia.append({
            'clase': clase,
            'inscritos': _inscritos(clase),
            'confirmados': _confirmados(clase, hoy),
            'ya_paso_lista': RegistroAsistencia.objects.filter(
                clase=clase, fecha=hoy).exists(),
        })
    del_dia.sort(key=lambda c: c['clase'].hora_inicio)

    # Si hoy no hay nada, se muestra cuándo vuelve a haber.
    siguiente = None if del_dia else servicios.proxima_sesion(mis_clases)

    semana = servicios.sesiones_proximas(mis_clases, dias=7, desde=hoy + timedelta(days=1))

    return render(request, 'profesoras/panel.html', {
        **_contexto_base(request),
        'activo': 'panel',
        'hoy': hoy,
        'clases_hoy': del_dia,
        'siguiente': siguiente,
        'semana': semana,
        'total_clases': len(mis_clases),
    })


# ---------------------------------------------------------------------------
# 1.2 Listado de clases
# ---------------------------------------------------------------------------
@acceso_profesoras
def clases(request):
    dia = request.GET.get('dia', '')
    mis_clases = list(clases_visibles(request.user))

    if dia:
        mis_clases = [c for c in mis_clases if dia in c.dias_lista]

    filas = [{
        'clase': clase,
        'inscritos': _inscritos(clase),
        'toca_hoy': servicios.clase_ocurre_en(clase, timezone.localdate()),
    } for clase in mis_clases]

    return render(request, 'profesoras/clases.html', {
        **_contexto_base(request),
        'activo': 'clases',
        'filas': filas,
        'dias': DiaSemana.choices,
        'dia': dia,
        'hoy': timezone.localdate(),
    })


# ---------------------------------------------------------------------------
# 1.3 Historial
# ---------------------------------------------------------------------------
def _rango_historial(request):
    hoy = timezone.localdate()
    try:
        anio = int(request.GET.get('anio', hoy.year))
        mes = int(request.GET.get('mes', hoy.month))
        referencia = hoy.replace(year=anio, month=mes, day=1)
    except (ValueError, TypeError):
        referencia = hoy.replace(day=1)
    return servicios.rango_mes(referencia)


def _sesiones_dictadas(usuario, inicio, fin):
    """Una fila por clase y fecha en que se pasó lista, con su desglose."""
    visibles = clases_visibles(usuario, solo_activas=False)

    agrupado = (
        RegistroAsistencia.objects
        .filter(clase__in=visibles, fecha__gte=inicio, fecha__lte=fin)
        .values('clase', 'fecha')
        .annotate(
            presentes=Count('id', filter=Q(estado=RegistroAsistencia.Estado.PRESENTE)),
            ausentes=Count('id', filter=Q(estado=RegistroAsistencia.Estado.AUSENTE)),
            justificados=Count('id', filter=Q(estado=RegistroAsistencia.Estado.JUSTIFICADO)),
            total=Count('id'),
        )
        .order_by('-fecha')
    )

    por_id = {c.pk: c for c in visibles}
    filas = []
    for fila in agrupado:
        clase = por_id.get(fila['clase'])
        if not clase:
            continue
        filas.append({
            'clase': clase,
            'fecha': fila['fecha'],
            'presentes': fila['presentes'],
            'ausentes': fila['ausentes'],
            'justificados': fila['justificados'],
            'total': fila['total'],
            'porcentaje': round(fila['presentes'] / fila['total'] * 100) if fila['total'] else 0,
        })
    return filas


@acceso_profesoras
def historial(request):
    inicio, fin = _rango_historial(request)
    filas = _sesiones_dictadas(request.user, inicio, fin)

    total_marcas = sum(f['total'] for f in filas)
    total_presentes = sum(f['presentes'] for f in filas)

    hoy = timezone.localdate()
    anios = list(range(hoy.year, hoy.year - 4, -1))

    return render(request, 'profesoras/historial.html', {
        **_contexto_base(request),
        'activo': 'historial',
        'filas': filas,
        'inicio': inicio,
        'nombre_mes': servicios.nombre_mes(inicio),
        'sesiones': len(filas),
        'promedio': round(total_presentes / total_marcas * 100) if total_marcas else None,
        'total_presentes': total_presentes,
        'total_marcas': total_marcas,
        'meses': list(enumerate(servicios.MESES_LARGO, start=1)),
        'anios': anios,
        'mes_actual': inicio.month,
        'anio_actual': inicio.year,
    })


@acceso_profesoras
def historial_exportar(request):
    from apps.gestion.excel import exportar_historial_profesora

    inicio, fin = _rango_historial(request)
    filas = _sesiones_dictadas(request.user, inicio, fin)

    respuesta = HttpResponse(
        exportar_historial_profesora(filas, servicios.nombre_mes(inicio)),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    nombre = f'historial_{inicio:%Y-%m}.xlsx'
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return respuesta


# ---------------------------------------------------------------------------
# 1.4 Pasar lista (optimizado para tablet)
# ---------------------------------------------------------------------------
@acceso_profesoras
def asistencia(request, clase_id, fecha):
    clase = clase_visible_o_404(request.user, clase_id)
    hoy = timezone.localdate()

    try:
        dia = datetime.fromisoformat(fecha).date()
    except (ValueError, TypeError):
        dia = hoy

    if dia > hoy:
        messages.warning(request, 'No se puede pasar lista de una clase que aún no ocurre.')
        return redirect('profesoras:panel')

    inscripciones = (
        clase.inscripciones
        .filter(alumno__eliminado=False)
        .select_related('alumno')
        .order_by('alumno__nombre_completo')
    )

    # ------------------------------------------------------------------
    if request.method == 'POST':
        guardados = 0
        for inscripcion in inscripciones:
            alumno = inscripcion.alumno
            estado = request.POST.get(f'estado_{alumno.pk}')
            if estado not in dict(RegistroAsistencia.Estado.choices):
                continue
            RegistroAsistencia.objects.update_or_create(
                clase=clase, alumno=alumno, fecha=dia,
                defaults={
                    'estado': estado,
                    'observacion': request.POST.get(f'obs_{alumno.pk}', '')[:200],
                },
            )
            guardados += 1

        registrar(request, AuditLog.Accion.ASISTENCIA, clase,
                  f'Pasó lista de {clase} el {dia:%d/%m/%Y} ({guardados} alumnos)')
        messages.success(request, f'Asistencia guardada: {guardados} alumno{"s" if guardados != 1 else ""}.')
        return redirect('profesoras:panel')

    # ------------------------------------------------------------------
    previos = {r.alumno_id: r for r in
               RegistroAsistencia.objects.filter(clase=clase, fecha=dia)}
    confirmados = set(
        ConfirmacionAsistencia.objects
        .filter(clase=clase, fecha=dia)
        .values_list('alumno_id', flat=True)
    )
    inicio_mes, fin_mes = servicios.rango_mes(dia)

    filas = []
    for inscripcion in inscripciones:
        alumno = inscripcion.alumno
        del_mes = RegistroAsistencia.objects.filter(
            clase=clase, alumno=alumno, fecha__gte=inicio_mes, fecha__lte=fin_mes)
        total = del_mes.count()
        presentes = del_mes.filter(estado=RegistroAsistencia.Estado.PRESENTE).count()

        filas.append({
            'alumno': alumno,
            'registro': previos.get(alumno.pk),
            'confirmo': alumno.pk in confirmados,
            'porcentaje_mes': round(presentes / total * 100) if total else None,
        })

    return render(request, 'profesoras/asistencia.html', {
        **_contexto_base(request),
        'activo': 'panel',
        'clase': clase,
        'fecha': dia,
        'hoy': hoy,
        'filas': filas,
        'estados': RegistroAsistencia.Estado.choices,
        'ya_registrada': any(f['registro'] for f in filas),
        'total_confirmados': len(confirmados),
    })
