"""Módulo 5 — Control de pagos."""

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from ..auditoria import registrar
from ..forms import PagoForm
from ..models import Alumno, AuditLog, Pago, Plan, Suscripcion
from ..permisos import gestion_requerida
from .. import servicios

POR_PAGINA = 25


def _pagos_filtrados(request):
    qs = Pago.objects.select_related('alumno', 'suscripcion__plan', 'registrado_por')

    buscar = request.GET.get('q', '').strip()
    if buscar:
        qs = qs.filter(
            Q(alumno__nombre_completo__icontains=buscar)
            | Q(alumno__rut__icontains=buscar)
            | Q(numero_comprobante__icontains=buscar)
        )

    mes = request.GET.get('mes', '')
    if mes:
        try:
            anio, numero = mes.split('-')
            qs = qs.filter(fecha_pago__year=int(anio), fecha_pago__month=int(numero))
        except (ValueError, TypeError):
            pass

    for campo in ('metodo', 'estado', 'concepto'):
        valor = request.GET.get(campo, '')
        if valor:
            qs = qs.filter(**{campo: valor})

    alumno = request.GET.get('alumno', '')
    if alumno:
        qs = qs.filter(alumno_id=alumno)

    return qs


@gestion_requerida
def pagos(request):
    qs = _pagos_filtrados(request)

    totales = qs.aggregate(
        cobrado=Sum('monto_clp', filter=Q(estado=Pago.Estado.PAGADO)),
        pendiente=Sum('monto_clp', filter=~Q(estado=Pago.Estado.PAGADO)),
    )

    paginador = Paginator(qs, POR_PAGINA)
    pagina = paginador.get_page(request.GET.get('page'))

    parametros = request.GET.copy()
    parametros.pop('page', None)

    # Meses disponibles para el filtro, sacados de los propios pagos.
    meses = []
    for fecha in Pago.objects.dates('fecha_pago', 'month', order='DESC')[:24]:
        meses.append({
            'valor': f'{fecha.year}-{fecha.month:02d}',
            'etiqueta': servicios.nombre_mes(fecha).capitalize(),
        })

    return render(request, 'gestion/pagos/listado.html', {
        'activo': 'pagos',
        'pagina': pagina,
        'total': paginador.count,
        'total_cobrado': totales['cobrado'] or 0,
        'total_pendiente': totales['pendiente'] or 0,
        'meses': meses,
        'metodos': Pago.Metodo.choices,
        'estados': Pago.Estado.choices,
        'conceptos': Pago.Concepto.choices,
        'filtros': {
            'q': request.GET.get('q', ''),
            'mes': request.GET.get('mes', ''),
            'metodo': request.GET.get('metodo', ''),
            'estado': request.GET.get('estado', ''),
            'concepto': request.GET.get('concepto', ''),
        },
        'querystring': parametros.urlencode(),
    })


@gestion_requerida
def pago_nuevo(request):
    inicial = {}
    alumno_id = request.GET.get('alumno')
    if alumno_id:
        inicial['alumno'] = alumno_id

    if request.method == 'POST':
        form = PagoForm(request.POST)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.registrado_por = request.user
            pago.save()

            # Si el pago salda el mes, la alerta de pago pendiente sobra.
            if pago.estado == Pago.Estado.PAGADO:
                pago.alumno.alertas.filter(
                    tipo='PAGO_PENDIENTE', gestionada=False
                ).update(gestionada=True, gestionada_en=timezone.now(),
                         gestionada_por=request.user)

            registrar(request, AuditLog.Accion.PAGO, pago,
                      f'Registró ${pago.monto_clp} de {pago.alumno.nombre_completo}')
            messages.success(request, 'Pago registrado.')

            if request.POST.get('volver_a_ficha'):
                return redirect('gestion:alumno_detalle', pk=pago.alumno_id)
            return redirect('gestion:pagos')
        messages.error(request, 'Revisa los datos del pago.')
    else:
        form = PagoForm(initial=inicial)

    return render(request, 'gestion/pagos/formulario.html', {
        'activo': 'pagos',
        'form': form,
        'alumnos': Alumno.objects.all().only('id', 'nombre_completo', 'rut'),
    })


@gestion_requerida
def resumen_financiero(request):
    hoy = timezone.localdate()
    inicio_mes, fin_mes = servicios.rango_mes(hoy)
    inicio_ant, fin_ant = servicios.mes_anterior(hoy)

    ingresos_mes = servicios.ingresos_entre(inicio_mes, fin_mes)
    ingresos_ant = servicios.ingresos_entre(inicio_ant, fin_ant)
    serie = servicios.ingresos_por_mes(6)

    del_mes = Pago.objects.filter(fecha_pago__gte=inicio_mes, fecha_pago__lte=fin_mes)

    por_metodo = [
        {
            'etiqueta': dict(Pago.Metodo.choices)[fila['metodo']],
            'total': fila['total'] or 0,
            'cantidad': fila['cantidad'],
        }
        for fila in del_mes.filter(estado=Pago.Estado.PAGADO)
        .values('metodo').annotate(total=Sum('monto_clp'), cantidad=Count('id'))
    ]

    por_concepto = [
        {
            'etiqueta': dict(Pago.Concepto.choices)[fila['concepto']],
            'total': fila['total'] or 0,
            'cantidad': fila['cantidad'],
        }
        for fila in del_mes.filter(estado=Pago.Estado.PAGADO)
        .values('concepto').annotate(total=Sum('monto_clp'), cantidad=Count('id'))
    ]

    por_plan = []
    for plan in Plan.objects.all():
        total = Pago.objects.filter(
            estado=Pago.Estado.PAGADO,
            fecha_pago__gte=inicio_mes,
            fecha_pago__lte=fin_mes,
            suscripcion__plan=plan,
        ).aggregate(t=Sum('monto_clp'))['t'] or 0
        if total:
            por_plan.append({'etiqueta': plan.nombre, 'total': total})

    # Alumnos activos que no han pagado nada este mes.
    sin_pagar = Alumno.objects.filter(estado=Alumno.Estado.ACTIVO).exclude(
        pagos__estado=Pago.Estado.PAGADO,
        pagos__fecha_pago__gte=inicio_mes,
        pagos__fecha_pago__lte=fin_mes,
    ).prefetch_related('suscripciones__plan')

    # Proyección: lo cobrado más lo que entraría si todos los activos con
    # plan vigente pagaran su mensualidad.
    pendiente_proyectado = 0
    for alumno in sin_pagar:
        sus = alumno.suscripcion_vigente
        if sus:
            pendiente_proyectado += sus.plan.precio_clp

    return render(request, 'gestion/pagos/resumen.html', {
        'activo': 'resumen',
        'nombre_mes': servicios.nombre_mes(hoy),
        'nombre_mes_anterior': servicios.nombre_mes(inicio_ant),
        'ingresos_mes': ingresos_mes,
        'ingresos_anterior': ingresos_ant,
        'variacion': servicios.variacion(ingresos_mes, ingresos_ant),
        'diferencia': ingresos_mes - ingresos_ant,
        'serie': serie,
        'por_metodo': por_metodo,
        'por_concepto': por_concepto,
        'por_plan': por_plan,
        'sin_pagar': sin_pagar,
        'total_sin_pagar': sin_pagar.count(),
        'pendiente_proyectado': pendiente_proyectado,
        'proyeccion': ingresos_mes + pendiente_proyectado,
        'grafico_ingresos': {
            'etiquetas': [m['etiqueta'] for m in serie],
            'datos': [m['total'] for m in serie],
        },
    })


@gestion_requerida
def pagos_exportar(request):
    from ..excel import exportar_pagos

    qs = _pagos_filtrados(request)
    respuesta = HttpResponse(
        exportar_pagos(qs),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    nombre = f'pagos_{timezone.localdate():%Y-%m-%d}.xlsx'
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return respuesta
