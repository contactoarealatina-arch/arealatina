"""Histórico por curso o por plan.

Responde dos preguntas que el estudio hoy no puede contestar sin revisar
fichas una por una: cuánto genera cada curso, y quién ha pasado por él a
lo largo del tiempo.

Es histórico de verdad: incluye a quien ya no está inscrito y a los
alumnos dados de baja. Mostrar solo los activos daría una cifra de
recaudación más baja que la real.
"""
from datetime import date

from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from ..models import Alumno, Clase, Pago, Plan, Suscripcion
from ..permisos import gestion_requerida

# El valor es cuántos días hacia atrás; None es todo el histórico.
RANGOS = {
    'mes': ('Este mes', 'mes'),
    'anio': ('Este año', 'anio'),
    'todo': ('Todo el histórico', None),
}


def _limites(rango):
    """Devuelve (desde, hasta). None y None significa sin límite."""
    hoy = timezone.localdate()
    if rango == 'mes':
        return date(hoy.year, hoy.month, 1), hoy
    if rango == 'anio':
        return date(hoy.year, 1, 1), hoy
    return None, None


def _consultar(request):
    """Arma el resultado. Se comparte entre la vista y la exportación."""
    tipo = request.GET.get('tipo', 'clase')
    if tipo not in ('clase', 'plan'):
        tipo = 'clase'

    objeto_id = request.GET.get('id', '')
    rango = request.GET.get('rango', 'todo')
    if rango not in RANGOS:
        rango = 'todo'

    desde, hasta = _limites(rango)

    objeto = None
    alumnos = Alumno.objects.none()
    pagos = Pago.objects.none()

    if objeto_id.isdigit():
        pk = int(objeto_id)

        if tipo == 'clase':
            objeto = Clase.objects.filter(pk=pk).first()
            if objeto:
                # Todos los que alguna vez se inscribieron, incluidos los
                # dados de baja: es histórico, no la foto de hoy.
                alumnos = (
                    Alumno.todos.filter(inscripciones__clase=objeto)
                    .distinct()
                    .order_by('nombre_completo')
                )
                # Una clase no tiene pagos propios: el alumno paga un plan
                # que le da acceso. Se cuenta lo que pagó quien estuvo
                # inscrito acá, y la plantilla lo dice explícitamente.
                pagos = Pago.objects.filter(
                    estado=Pago.Estado.PAGADO,
                    alumno__in=alumnos,
                )
        else:
            objeto = Plan.objects.filter(pk=pk).first()
            if objeto:
                alumnos = (
                    Alumno.todos.filter(suscripciones__plan=objeto)
                    .distinct()
                    .order_by('nombre_completo')
                )
                pagos = Pago.objects.filter(
                    estado=Pago.Estado.PAGADO,
                    suscripcion__plan=objeto,
                )

        if desde:
            pagos = pagos.filter(fecha_pago__gte=desde, fecha_pago__lte=hasta)

    total = pagos.aggregate(t=Sum('monto_clp'))['t'] or 0

    # Cuánto puso cada alumno, para ordenar la tabla por aporte.
    aportes = {
        fila['alumno_id']: fila
        for fila in pagos.values('alumno_id').annotate(
            monto=Sum('monto_clp'), cuantos=Count('id'),
        )
    }

    filas = []
    for alumno in alumnos.select_related():
        aporte = aportes.get(alumno.pk, {})
        filas.append({
            'alumno': alumno,
            'monto': aporte.get('monto', 0) or 0,
            'pagos': aporte.get('cuantos', 0),
            'activo': alumno.estado == Alumno.Estado.ACTIVO and not alumno.eliminado,
        })
    filas.sort(key=lambda f: (-f['monto'], f['alumno'].nombre_completo))

    return {
        'tipo': tipo,
        'objeto': objeto,
        'objeto_id': objeto_id,
        'rango': rango,
        'desde': desde,
        'hasta': hasta,
        'filas': filas,
        'total': total,
        'cuantos_pagos': pagos.count(),
        'activos': sum(1 for f in filas if f['activo']),
    }


@gestion_requerida
def por_curso(request):
    datos = _consultar(request)

    return render(request, 'gestion/reportes/por_curso.html', {
        'activo': 'por_curso',
        **datos,
        'clases': Clase.objects.all().order_by('nombre', 'hora_inicio'),
        'planes': Plan.objects.all().order_by('orden', 'precio_clp'),
        'rangos': [(k, v[0]) for k, v in RANGOS.items()],
    })


@gestion_requerida
def por_curso_exportar(request):
    from ..excel import exportar_por_curso

    datos = _consultar(request)
    if not datos['objeto']:
        from django.contrib import messages
        from django.shortcuts import redirect

        messages.error(request, 'Elige primero un curso o un plan.')
        return redirect('gestion:por_curso')

    nombre = (
        datos['objeto'].nombre
        if datos['tipo'] == 'clase' else datos['objeto'].nombre
    )
    respuesta = HttpResponse(
        exportar_por_curso(datos, nombre),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    limpio = ''.join(c if c.isalnum() else '-' for c in nombre).strip('-')
    respuesta['Content-Disposition'] = (
        f'attachment; filename="historico-{limpio}-{timezone.localdate()}.xlsx"'
    )
    return respuesta
