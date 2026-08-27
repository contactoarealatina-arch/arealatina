"""Módulo 3 — Gestión de clases."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.asistencia.models import RegistroAsistencia

from ..auditoria import registrar
from ..forms import ClaseForm
from ..models import AuditLog, Clase
from ..permisos import gestion_requerida
from .. import servicios


@gestion_requerida
def clases(request):
    mostrar = request.GET.get('mostrar', 'activas')

    qs = Clase.objects.select_related('profesora').prefetch_related('inscripciones')
    if mostrar == 'activas':
        qs = qs.filter(activa=True)
    elif mostrar == 'inactivas':
        qs = qs.filter(activa=False)

    return render(request, 'gestion/clases/listado.html', {
        'activo': 'clases',
        'clases': qs,
        'mostrar': mostrar,
        'total_activas': Clase.objects.filter(activa=True).count(),
        'total_inactivas': Clase.objects.filter(activa=False).count(),
    })


@gestion_requerida
def clase_nueva(request):
    if request.method == 'POST':
        form = ClaseForm(request.POST)
        if form.is_valid():
            clase = form.save()
            registrar(request, AuditLog.Accion.CREAR, clase, f'Creó la clase {clase}')
            messages.success(request, 'Clase creada.')
            return redirect('gestion:clase_detalle', pk=clase.pk)
        messages.error(request, 'Revisa los datos de la clase.')
    else:
        form = ClaseForm()

    return render(request, 'gestion/clases/formulario.html', {
        'activo': 'clases',
        'form': form,
        'editando': False,
    })


@gestion_requerida
def clase_editar(request, pk):
    clase = get_object_or_404(Clase, pk=pk)

    if request.method == 'POST':
        form = ClaseForm(request.POST, instance=clase)
        if form.is_valid():
            clase = form.save()
            registrar(request, AuditLog.Accion.EDITAR, clase, f'Editó la clase {clase}')
            messages.success(request, 'Clase actualizada.')
            return redirect('gestion:clase_detalle', pk=clase.pk)
        messages.error(request, 'Revisa los datos de la clase.')
    else:
        form = ClaseForm(instance=clase)

    return render(request, 'gestion/clases/formulario.html', {
        'activo': 'clases',
        'form': form,
        'clase': clase,
        'editando': True,
    })


@gestion_requerida
def clase_detalle(request, pk):
    clase = get_object_or_404(
        Clase.objects.select_related('profesora'), pk=pk
    )
    inicio_mes, fin_mes = servicios.rango_mes()

    registros_mes = RegistroAsistencia.objects.filter(
        clase=clase, fecha__gte=inicio_mes, fecha__lte=fin_mes
    )
    total_marcas = registros_mes.count()
    presentes = registros_mes.filter(estado=RegistroAsistencia.Estado.PRESENTE).count()

    # Historial agrupado por fecha, de la más reciente hacia atrás.
    fechas = (
        RegistroAsistencia.objects.filter(clase=clase)
        .values('fecha')
        .distinct()
        .order_by('-fecha')[:12]
    )
    historial = []
    for item in fechas:
        dia = RegistroAsistencia.objects.filter(clase=clase, fecha=item['fecha'])
        historial.append({
            'fecha': item['fecha'],
            'presentes': dia.filter(estado=RegistroAsistencia.Estado.PRESENTE).count(),
            'total': dia.count(),
        })

    return render(request, 'gestion/clases/detalle.html', {
        'activo': 'clases',
        'clase': clase,
        'inscripciones': clase.inscripciones.select_related('alumno').filter(
            alumno__eliminado=False
        ),
        'promedio_asistencia': round(presentes / total_marcas * 100) if total_marcas else None,
        'historial': historial,
        'nombre_mes': servicios.nombre_mes(timezone.localdate()),
    })
