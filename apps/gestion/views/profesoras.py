"""Módulo 9 — Gestión de profesoras."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render

from apps.asistencia.models import RegistroAsistencia

from ..auditoria import registrar
from ..forms import ProfesoraForm
from ..models import AuditLog, Clase
from ..permisos import gestion_requerida

User = get_user_model()


@gestion_requerida
def profesoras(request):
    equipo = User.objects.filter(rol=User.Rol.PROFESOR).prefetch_related('clases_dictadas')
    return render(request, 'gestion/profesoras/listado.html', {
        'activo': 'profesoras',
        'profesoras': equipo,
        'total': equipo.count(),
    })


@gestion_requerida
def profesora_nueva(request):
    if request.method == 'POST':
        form = ProfesoraForm(request.POST)
        if form.is_valid():
            profesora = form.save()
            registrar(request, AuditLog.Accion.CREAR, profesora,
                      f'Creó a la profesora {profesora.get_full_name()}')
            messages.success(request, 'Profesora registrada.')
            return redirect('gestion:profesora_detalle', pk=profesora.pk)
        messages.error(request, 'Revisa los datos.')
    else:
        form = ProfesoraForm()

    return render(request, 'gestion/profesoras/formulario.html', {
        'activo': 'profesoras', 'form': form, 'editando': False,
    })


@gestion_requerida
def profesora_editar(request, pk):
    profesora = get_object_or_404(User, pk=pk, rol=User.Rol.PROFESOR)

    if request.method == 'POST':
        form = ProfesoraForm(request.POST, instance=profesora)
        if form.is_valid():
            profesora = form.save()
            registrar(request, AuditLog.Accion.EDITAR, profesora,
                      f'Editó a la profesora {profesora.get_full_name()}')
            messages.success(request, 'Datos actualizados.')
            return redirect('gestion:profesora_detalle', pk=profesora.pk)
        messages.error(request, 'Revisa los datos.')
    else:
        form = ProfesoraForm(instance=profesora)

    return render(request, 'gestion/profesoras/formulario.html', {
        'activo': 'profesoras', 'form': form, 'profesora': profesora, 'editando': True,
    })


@gestion_requerida
def profesora_detalle(request, pk):
    profesora = get_object_or_404(User, pk=pk, rol=User.Rol.PROFESOR)

    clases = Clase.objects.filter(profesora=profesora).prefetch_related('inscripciones')

    # Últimas fechas en que pasó lista, agrupadas por clase y día.
    marcas = (
        RegistroAsistencia.objects.filter(clase__profesora=profesora)
        .select_related('clase')
        .order_by('-fecha')
    )
    vistas = set()
    sesiones = []
    for marca in marcas[:200]:
        llave = (marca.clase_id, marca.fecha)
        if llave in vistas:
            continue
        vistas.add(llave)
        sesiones.append({
            'clase': marca.clase,
            'fecha': marca.fecha,
            'total': RegistroAsistencia.objects.filter(
                clase=marca.clase, fecha=marca.fecha).count(),
        })
        if len(sesiones) >= 15:
            break

    return render(request, 'gestion/profesoras/detalle.html', {
        'activo': 'profesoras',
        'profesora': profesora,
        'clases': clases,
        'sesiones': sesiones,
        'total_marcas': marcas.count(),
    })
