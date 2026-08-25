"""Vistas internas del modulo de gestion."""
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from .models import Alumno, Clase, Pago, Suscripcion


@login_required
def dashboard(request):
    """Resumen rapido para el equipo administrativo."""
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)

    ingresos_mes = Pago.objects.filter(
        estado=Pago.Estado.PAGADO,
        fecha_pago__gte=inicio_mes,
    ).aggregate(total=Sum('monto_clp'))['total'] or 0

    contexto = {
        'alumnos_activos': Alumno.objects.filter(estado=Alumno.Estado.ACTIVO).count(),
        'alumnos_total': Alumno.objects.count(),
        'clases_activas': Clase.objects.filter(activa=True).count(),
        'ingresos_mes': ingresos_mes,
        'pagos_pendientes': Pago.objects.exclude(estado=Pago.Estado.PAGADO).count(),
        'por_vencer': Suscripcion.objects.filter(
            activa=True,
            fecha_vencimiento__range=(hoy, hoy + timedelta(days=7)),
        ).select_related('alumno', 'plan'),
        'ultimos_pagos': Pago.objects.select_related('alumno')[:8],
    }
    return render(request, 'gestion/dashboard.html', contexto)
