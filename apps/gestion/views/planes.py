"""Módulo 4 — Planes y suscripciones."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from ..auditoria import registrar
from ..forms import PlanForm
from ..models import AuditLog, Categoria, Plan, Suscripcion
from ..permisos import gestion_requerida


@gestion_requerida
def planes(request):
    """Los planes, separados por pilar.

    Baile urbano y bienestar se venden distinto, así que verlos juntos en
    una sola tabla obliga a leer plan por plan para saber cuál es cuál.

    Los planes sin pilar sirven en todo el estudio, así que aparecen en
    las dos pestañas: para un alumno de bienestar, un plan general es una
    opción real y esconderlo sería mentir por omisión.
    """
    todos = list(Plan.objects.prefetch_related('pilares'))

    grupos = []
    for pilar in Categoria.objects.filter(activa=True):
        del_pilar = [
            p for p in todos
            if not p.pilares.all() or pilar in p.pilares.all()
        ]
        grupos.append({
            'pilar': pilar,
            'slug': pilar.slug,
            'nombre': pilar.nombre,
            'icono': pilar.icono,
            'planes': del_pilar,
            'cuantos': len(del_pilar),
            'activos': sum(1 for p in del_pilar if p.activo),
        })

    # Una pestaña más con todo junto: para comparar precios entre pilares
    # sin ir y volver.
    grupos.insert(0, {
        'pilar': None,
        'slug': 'todos',
        'nombre': 'Todos los planes',
        'icono': 'bi-collection',
        'planes': todos,
        'cuantos': len(todos),
        'activos': sum(1 for p in todos if p.activo),
    })

    return render(request, 'gestion/planes/listado.html', {
        'activo': 'planes',
        'grupos': grupos,
        'planes': todos,
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


@gestion_requerida
def plan_eliminar(request, pk):
    """Borra un plan, solo si nadie lo contrató nunca.

    Con suscripciones colgando, borrarlo dejaría pagos apuntando a un plan
    que no existe y el histórico por plan quedaría en blanco.
    """
    if request.method != 'POST':
        return redirect('gestion:planes')

    plan = get_object_or_404(Plan, pk=pk)
    contratos = plan.suscripciones.count()

    if contratos:
        messages.error(
            request,
            f'No se puede eliminar «{plan.nombre}»: {contratos} '
            f'suscripción{"es" if contratos != 1 else ""} lo '
            f'{"han" if contratos != 1 else "ha"} usado. Ocúltalo: deja de '
            f'ofrecerse a los alumnos nuevos y el histórico se conserva.',
        )
        return redirect('gestion:planes')

    nombre = plan.nombre
    registrar(request, AuditLog.Accion.ELIMINAR, plan, f'Eliminó el plan {nombre}')
    plan.delete()
    messages.success(request, f'Plan «{nombre}» eliminado.')
    return redirect('gestion:planes')
