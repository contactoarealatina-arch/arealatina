"""Módulo 6 — Sistema de alertas."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import ConfiguracionAlertasForm, RenovarPlanForm
from ..models import Alerta, ConfiguracionAlertas
from ..permisos import gestion_requerida
from .. import servicios


@gestion_requerida
def alertas(request):
    tipo = request.GET.get('tipo', '')
    ver = request.GET.get('ver', 'pendientes')

    qs = Alerta.objects.select_related('alumno', 'suscripcion__plan')
    if ver == 'pendientes':
        qs = qs.filter(gestionada=False)
    elif ver == 'gestionadas':
        qs = qs.filter(gestionada=True)
    if tipo:
        qs = qs.filter(tipo=tipo)

    pendientes = Alerta.objects.filter(gestionada=False)

    return render(request, 'gestion/alertas/listado.html', {
        'activo': 'alertas',
        'alertas': qs[:200],
        'tipos': Alerta.Tipo.choices,
        'tipo': tipo,
        'ver': ver,
        'conteo': {
            'total': pendientes.count(),
            'por_vencer': pendientes.filter(tipo=Alerta.Tipo.VENCIMIENTO_PROXIMO).count(),
            'vencidos': pendientes.filter(tipo=Alerta.Tipo.PLAN_VENCIDO).count(),
            'pagos': pendientes.filter(tipo=Alerta.Tipo.PAGO_PENDIENTE).count(),
        },
        'form_renovar': RenovarPlanForm(),
    })


@gestion_requerida
def alerta_gestionar(request, pk):
    if request.method != 'POST':
        return redirect('gestion:alertas')

    alerta = get_object_or_404(Alerta, pk=pk)
    alerta.marcar_gestionada(request.user)
    messages.success(request, 'Alerta marcada como gestionada.')
    return redirect(request.POST.get('siguiente') or 'gestion:alertas')


@gestion_requerida
def alertas_regenerar(request):
    """Corre el mismo proceso del cron, pero a pedido."""
    if request.method != 'POST':
        return redirect('gestion:alertas')

    resumen = servicios.generar_alertas()
    if resumen['creadas']:
        messages.success(request, f'Se generaron {resumen["creadas"]} alertas nuevas.')
    else:
        messages.info(request, 'No hay alertas nuevas: todo al día.')
    return redirect('gestion:alertas')


@gestion_requerida
def alertas_configuracion(request):
    config = ConfiguracionAlertas.obtener()

    if request.method == 'POST':
        form = ConfiguracionAlertasForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuración guardada.')
            return redirect('gestion:alertas_configuracion')
        messages.error(request, 'Revisa la configuración.')
    else:
        form = ConfiguracionAlertasForm(instance=config)

    return render(request, 'gestion/alertas/configuracion.html', {
        'activo': 'alertas',
        'form': form,
        'config': config,
    })
