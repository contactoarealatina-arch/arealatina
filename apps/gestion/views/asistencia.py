"""Módulo 8 — Registro de asistencia desde el panel."""
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.asistencia.models import RegistroAsistencia

from ..auditoria import registrar
from ..models import AuditLog, Clase
from ..permisos import profesor_o_gestion
from .. import servicios


@profesor_o_gestion
def asistencia(request):
    hoy = timezone.localdate()

    clases_qs = Clase.objects.filter(activa=True).select_related('profesora')
    # Una profesora solo pasa lista de sus propias clases.
    if request.user.es_profesor and not request.user.puede_gestionar:
        clases_qs = clases_qs.filter(profesora=request.user)

    clase_id = request.GET.get('clase') or request.POST.get('clase')
    fecha_texto = request.GET.get('fecha') or request.POST.get('fecha') or hoy.isoformat()

    try:
        fecha = timezone.datetime.fromisoformat(fecha_texto).date()
    except (ValueError, TypeError):
        fecha = hoy

    clase = clases_qs.filter(pk=clase_id).first() if clase_id else None

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------
    if request.method == 'POST' and clase:
        guardados = 0
        with transaction.atomic():
            for inscripcion in clase.inscripciones.filter(alumno__eliminado=False):
                alumno = inscripcion.alumno
                estado = request.POST.get(f'estado_{alumno.pk}')
                if estado not in dict(RegistroAsistencia.Estado.choices):
                    continue
                RegistroAsistencia.objects.update_or_create(
                    clase=clase, alumno=alumno, fecha=fecha,
                    defaults={
                        'estado': estado,
                        'observacion': request.POST.get(f'obs_{alumno.pk}', '')[:200],
                    },
                )
                guardados += 1

        registrar(request, AuditLog.Accion.ASISTENCIA, clase,
                  f'Pasó lista de {clase} el {fecha:%d/%m/%Y} ({guardados} alumnos)')
        messages.success(request, f'Asistencia guardada: {guardados} alumnos.')
        return redirect(f'{request.path}?clase={clase.pk}&fecha={fecha.isoformat()}')

    # ------------------------------------------------------------------
    # Mostrar
    # ------------------------------------------------------------------
    filas = []
    if clase:
        previos = {
            r.alumno_id: r
            for r in RegistroAsistencia.objects.filter(clase=clase, fecha=fecha)
        }
        inicio_mes, fin_mes = servicios.rango_mes(fecha)

        for inscripcion in clase.inscripciones.filter(
            alumno__eliminado=False
        ).select_related('alumno').order_by('alumno__nombre_completo'):
            alumno = inscripcion.alumno
            del_mes = RegistroAsistencia.objects.filter(
                clase=clase, alumno=alumno, fecha__gte=inicio_mes, fecha__lte=fin_mes
            )
            total = del_mes.count()
            presentes = del_mes.filter(estado=RegistroAsistencia.Estado.PRESENTE).count()

            filas.append({
                'alumno': alumno,
                'registro': previos.get(alumno.pk),
                'porcentaje_mes': round(presentes / total * 100) if total else None,
            })

    return render(request, 'gestion/asistencia/pasar_lista.html', {
        'activo': 'asistencia',
        'clases': clases_qs,
        'clase': clase,
        'fecha': fecha,
        'hoy': hoy,
        'filas': filas,
        'estados': RegistroAsistencia.Estado.choices,
        'ya_registrada': any(f['registro'] for f in filas),
    })
