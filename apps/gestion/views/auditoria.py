"""Módulo 10 — Auditoría (solo superadmin)."""
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from ..models import AuditLog
from ..permisos import superadmin_requerido

POR_PAGINA = 50


@superadmin_requerido
def auditoria(request):
    qs = AuditLog.objects.select_related('usuario')

    buscar = request.GET.get('q', '').strip()
    if buscar:
        qs = qs.filter(
            Q(descripcion__icontains=buscar)
            | Q(usuario__first_name__icontains=buscar)
            | Q(usuario__username__icontains=buscar)
        )

    accion = request.GET.get('accion', '')
    if accion:
        qs = qs.filter(accion=accion)

    paginador = Paginator(qs, POR_PAGINA)
    pagina = paginador.get_page(request.GET.get('page'))

    parametros = request.GET.copy()
    parametros.pop('page', None)

    return render(request, 'gestion/auditoria/listado.html', {
        'activo': 'auditoria',
        'pagina': pagina,
        'total': paginador.count,
        'acciones': AuditLog.Accion.choices,
        'filtros': {'q': buscar, 'accion': accion},
        'querystring': parametros.urlencode(),
    })
