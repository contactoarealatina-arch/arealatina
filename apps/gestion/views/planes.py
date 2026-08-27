"""Módulo 4 — Planes y suscripciones."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from ..auditoria import registrar
from ..forms import PlanForm
from ..models import AuditLog, Plan, Suscripcion
from ..permisos import gestion_requerida


@gestion_requerida
def planes(request):
    return render(request, 'gestion/planes/listado.html', {
        'activo': 'planes',
        'planes': Plan.objects.all(),
        'suscripciones_recientes': Suscripcion.objects.select_related(
            'alumno', 'plan'
        ).filter(alumno__eliminado=False)[:10],
    })


@gestion_requerida
def plan_nuevo(request):
    if request.method == 'POST':
        form = PlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            registrar(request, AuditLog.Accion.CREAR, plan, f'Creó el plan {plan.nombre}')
            messages.success(request, 'Plan creado.')
            return redirect('gestion:planes')
        messages.error(request, 'Revisa los datos del plan.')
    else:
        form = PlanForm()

    return render(request, 'gestion/planes/formulario.html', {
        'activo': 'planes', 'form': form, 'editando': False,
    })


@gestion_requerida
def plan_editar(request, pk):
    plan = get_object_or_404(Plan, pk=pk)

    if request.method == 'POST':
        form = PlanForm(request.POST, instance=plan)
        if form.is_valid():
            plan = form.save()
            registrar(request, AuditLog.Accion.EDITAR, plan, f'Editó el plan {plan.nombre}')
            messages.success(request, 'Plan actualizado.')
            return redirect('gestion:planes')
        messages.error(request, 'Revisa los datos del plan.')
    else:
        form = PlanForm(instance=plan)

    return render(request, 'gestion/planes/formulario.html', {
        'activo': 'planes', 'form': form, 'plan': plan, 'editando': True,
    })


@gestion_requerida
def plan_alternar(request, pk):
    """Activa o desactiva un plan sin borrarlo: el histórico lo necesita."""
    if request.method != 'POST':
        return redirect('gestion:planes')

    plan = get_object_or_404(Plan, pk=pk)
    plan.activo = not plan.activo
    plan.save(update_fields=['activo', 'updated_at'])

    registrar(request, AuditLog.Accion.EDITAR, plan,
              f'{"Activó" if plan.activo else "Desactivó"} el plan {plan.nombre}')
    messages.success(request, f'Plan {"activado" if plan.activo else "desactivado"}.')
    return redirect('gestion:planes')
