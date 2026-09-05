"""Módulo 2 — Gestión de alumnos (CRUD completo)."""
import re
from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..auditoria import registrar
from ..correos import enviar_bienvenida, enviar_recibo
from ..forms import (
    AlumnoForm,
    InscripcionPlanForm,
    NotaInternaForm,
    PagoInicialForm,
    RenovarPlanForm,
)
from ..models import (
    Alumno,
    AuditLog,
    Clase,
    ConfiguracionAlertas,
    Inscripcion,
    Pago,
    Plan,
    Suscripcion,
)
from ..permisos import gestion_requerida
from .. import servicios

POR_PAGINA = 20


def _url_activacion(token):
    """Enlace absoluto de activación para el correo."""
    from django.conf import settings
    from django.urls import reverse

    if not token:
        return ''
    base = getattr(settings, 'SITIO_URL', 'http://localhost:8000').rstrip('/')
    return base + reverse('portal:activar', args=[token.token])


# ---------------------------------------------------------------------------
# 2.1 Listado
# ---------------------------------------------------------------------------
def _filtrar_por_estado_pago(qs, filtro, hoy, dias_aviso):
    """Traduce el estado de pago a filtros de base de datos.

    Se hace por consulta y no en Python porque el listado se pagina: filtrar
    después de paginar daría páginas con distinta cantidad de filas.
    """
    con_plan_vigente = Q(
        suscripciones__estado=Suscripcion.Estado.ACTIVA,
        suscripciones__fecha_vencimiento__gte=hoy,
    )

    if filtro == 'al_dia':
        return qs.filter(
            suscripciones__estado=Suscripcion.Estado.ACTIVA,
            suscripciones__fecha_vencimiento__gt=hoy + timedelta(days=dias_aviso),
        ).distinct()

    if filtro == 'por_vencer':
        return qs.filter(
            suscripciones__estado=Suscripcion.Estado.ACTIVA,
            suscripciones__fecha_vencimiento__gte=hoy,
            suscripciones__fecha_vencimiento__lte=hoy + timedelta(days=dias_aviso),
        ).distinct()

    if filtro == 'vencido':
        return qs.filter(suscripciones__isnull=False).exclude(con_plan_vigente).distinct()

    if filtro == 'sin_plan':
        return qs.filter(suscripciones__isnull=True)

    return qs


def _alumnos_filtrados(request):
    """Queryset compartido por el listado y la exportación a Excel."""
    hoy = timezone.localdate()
    dias_aviso = ConfiguracionAlertas.obtener().dias_anticipacion

    qs = Alumno.objects.select_related().prefetch_related(
        'inscripciones__clase', 'suscripciones__plan'
    )

    buscar = request.GET.get('q', '').strip()
    if buscar:
        qs = qs.filter(
            Q(nombre_completo__icontains=buscar)
            | Q(rut__icontains=buscar)
            | Q(email__icontains=buscar)
            | Q(telefono__icontains=buscar)
        )

    estado = request.GET.get('estado', '')
    if estado:
        qs = qs.filter(estado=estado)

    clase = request.GET.get('clase', '')
    if clase:
        qs = qs.filter(inscripciones__clase_id=clase).distinct()

    plan = request.GET.get('plan', '')
    if plan:
        qs = qs.filter(
            suscripciones__plan_id=plan,
            suscripciones__estado=Suscripcion.Estado.ACTIVA,
        ).distinct()

    pago = request.GET.get('pago', '')
    if pago:
        qs = _filtrar_por_estado_pago(qs, pago, hoy, dias_aviso)

    return qs


@gestion_requerida
def alumnos(request):
    servicios.vencer_suscripciones_pasadas()
    qs = _alumnos_filtrados(request)

    paginador = Paginator(qs, POR_PAGINA)
    pagina = paginador.get_page(request.GET.get('page'))

    # Se conservan los filtros al cambiar de página.
    parametros = request.GET.copy()
    parametros.pop('page', None)

    return render(request, 'gestion/alumnos/listado.html', {
        'activo': 'alumnos',
        'pagina': pagina,
        'total': paginador.count,
        'clases': Clase.objects.filter(activa=True),
        'planes': Plan.objects.filter(activo=True),
        'estados': Alumno.Estado.choices,
        'filtros': {
            'q': request.GET.get('q', ''),
            'estado': request.GET.get('estado', ''),
            'clase': request.GET.get('clase', ''),
            'plan': request.GET.get('plan', ''),
            'pago': request.GET.get('pago', ''),
            'vista': request.GET.get('vista', 'tabla'),
        },
        'querystring': parametros.urlencode(),
    })


# ---------------------------------------------------------------------------
# 2.2 Alta en pasos
# ---------------------------------------------------------------------------
@gestion_requerida
def alumno_nuevo(request):
    if request.method == 'POST':
        form = AlumnoForm(request.POST, request.FILES)
        form_plan = InscripcionPlanForm(request.POST)
        form_pago = PagoInicialForm(request.POST)

        if form.is_valid() and form_plan.is_valid() and form_pago.is_valid():
            with transaction.atomic():
                alumno = form.save(commit=False)
                alumno.creado_por = request.user
                alumno.actualizado_por = request.user
                alumno.save()

                _guardar_inscripcion_y_plan(request, alumno, form_plan, form_pago)

            registrar(request, AuditLog.Accion.CREAR, alumno,
                      f'Creó al alumno {alumno.nombre_completo}')

            # El correo va fuera de la transacción: si el SMTP falla, el
            # alumno igual quedó guardado.
            aviso = f'{alumno.nombre_completo} quedó registrado.'
            if alumno.email:
                from apps.portal.cuentas import crear_acceso

                usuario, token = crear_acceso(alumno)
                enlace = _url_activacion(token)
                enviado, motivo = enviar_bienvenida(alumno, enlace, usuario)
                aviso += (' Le mandamos la bienvenida con su acceso al portal.' if enviado
                          else f' Ojo: no salió el correo de bienvenida ({motivo})')
            else:
                aviso += ' Sin email no se le puede crear acceso al portal.'
            messages.success(request, aviso)
            return redirect('gestion:alumno_detalle', pk=alumno.pk)

        messages.error(request, 'Revisa los datos: hay campos con errores.')
    else:
        form = AlumnoForm()
        form_plan = InscripcionPlanForm()
        form_pago = PagoInicialForm()

    return render(request, 'gestion/alumnos/formulario.html', {
        'activo': 'alumnos',
        'form': form,
        'form_plan': form_plan,
        'form_pago': form_pago,
        'editando': False,
        # {id_del_plan: dias} para calcular el vencimiento sin recargar.
        'duraciones_planes': {
            str(p.pk): p.duracion_dias for p in Plan.objects.filter(activo=True)
        },
    })


def _guardar_inscripcion_y_plan(request, alumno, form_plan, form_pago):
    """Crea inscripciones, suscripción y pagos del alta. Todo es opcional."""
    datos = form_plan.cleaned_data

    for clase in datos.get('clases') or []:
        Inscripcion.objects.get_or_create(alumno=alumno, clase=clase)

    suscripcion = None
    plan = datos.get('plan')
    if plan:
        suscripcion = Suscripcion.objects.create(
            alumno=alumno,
            plan=plan,
            fecha_inicio=datos.get('fecha_inicio') or timezone.localdate(),
        )

    # Matrícula: es un pago aparte del plan.
    if datos.get('pago_matricula') and datos.get('monto_matricula'):
        Pago.objects.create(
            alumno=alumno,
            concepto=Pago.Concepto.MATRICULA,
            monto_clp=datos['monto_matricula'],
            metodo=form_pago.cleaned_data.get('metodo') or Pago.Metodo.EFECTIVO,
            estado=Pago.Estado.PAGADO,
            registrado_por=request.user,
        )

    pago_datos = form_pago.cleaned_data
    if pago_datos.get('monto_clp'):
        Pago.objects.create(
            alumno=alumno,
            suscripcion=suscripcion,
            concepto=Pago.Concepto.MENSUALIDAD if plan else Pago.Concepto.OTRO,
            detalle='' if plan else 'Pago inicial',
            monto_clp=pago_datos['monto_clp'],
            metodo=pago_datos.get('metodo') or Pago.Metodo.EFECTIVO,
            numero_comprobante=pago_datos.get('numero_comprobante', ''),
            nota_interna=pago_datos.get('nota_interna', ''),
            estado=Pago.Estado.PAGADO,
            registrado_por=request.user,
        )


# ---------------------------------------------------------------------------
# 2.3 Ficha
# ---------------------------------------------------------------------------
@gestion_requerida
def alumno_detalle(request, pk):
    alumno = get_object_or_404(
        Alumno.objects.prefetch_related('inscripciones__clase', 'suscripciones__plan'),
        pk=pk,
    )
    servicios.vencer_suscripciones_pasadas()

    asistencias = (
        alumno.asistencias.select_related('clase').order_by('-fecha')[:40]
    )

    # Se saca de la sesion al leerlo: el ofrecimiento aparece una vez,
    # no cada vez que alguien abre la ficha.
    email_corregido = request.session.pop('email_corregido', None)
    if email_corregido and email_corregido.get('alumno') != alumno.pk:
        email_corregido = None

    return render(request, 'gestion/alumnos/detalle.html', {
        'activo': 'alumnos',
        'alumno': alumno,
        'email_corregido': email_corregido,
        'suscripcion': alumno.suscripcion_vigente,
        'suscripciones': alumno.suscripciones.select_related('plan'),
        'pagos': alumno.pagos.select_related('suscripcion__plan'),
        'asistencias': asistencias,
        'notas': alumno.notas.select_related('autor'),
        'form_nota': NotaInternaForm(),
        'form_renovar': RenovarPlanForm(),
        'pagos_pendientes': alumno.pagos.exclude(estado=Pago.Estado.PAGADO).count(),
        'dias_aviso': ConfiguracionAlertas.obtener().dias_anticipacion,
        'whatsapp': _mensajes_whatsapp(alumno),
    })


@gestion_requerida
def alumno_reenviar_acceso(request, pk):
    """Genera un token nuevo y reenvía el correo de bienvenida.

    Se usa cuando el email estaba mal escrito: el alumno nunca recibió su
    enlace y el anterior no sirve de nada. `crear_acceso` borra los tokens
    sin usar de esa persona, así que el enlace viejo queda invalidado.
    """
    if request.method != 'POST':
        return redirect('gestion:alumno_detalle', pk=pk)

    alumno = get_object_or_404(Alumno, pk=pk)

    if not alumno.email:
        messages.error(request, 'El alumno no tiene email registrado.')
        return redirect('gestion:alumno_detalle', pk=pk)

    from apps.portal.cuentas import crear_acceso

    anterior = request.POST.get('anterior', '')
    usuario, token = crear_acceso(alumno)
    enviado, motivo = enviar_bienvenida(alumno, _url_activacion(token), usuario)

    detalle = f'Reenvió el acceso de {alumno.nombre_completo} a {alumno.email}'
    if anterior:
        detalle = (f'Email corregido de {anterior} a {alumno.email}, '
                   f'correo reenviado')
    registrar(request, AuditLog.Accion.EDITAR, alumno, detalle)

    if enviado:
        messages.success(
            request,
            f'Correo de bienvenida reenviado a {alumno.email}. '
            f'El enlace anterior quedó anulado.',
        )
    else:
        messages.error(request, f'No se pudo reenviar: {motivo}')

    return redirect('gestion:alumno_detalle', pk=pk)


def _mensajes_whatsapp(alumno):
    """Enlaces wa.me con el mensaje ya escrito.

    Sin API ni costo: es un enlace que abre WhatsApp Web o la app con el
    texto puesto. La persona lo revisa y aprieta enviar.
    """
    from urllib.parse import quote

    numero = re.sub(r'\D', '', alumno.telefono or '')
    if not numero:
        return None
    if not numero.startswith('56'):
        numero = '56' + numero.lstrip('0')

    sus = alumno.suscripcion_vigente
    nombre = alumno.primer_nombre
    vence = f'{sus.fecha_vencimiento:%d/%m}' if sus else ''
    plan = sus.plan.nombre if sus else 'tu plan'
    valor = f'{sus.plan.precio_clp:,}'.replace(',', '.') if sus else ''

    plantillas = [
        ('Aviso de vencimiento',
         f'Hola {nombre}, te escribimos de Área Latina. Tu {plan} vence el '
         f'{vence}. ¿Lo renovamos para que no pierdas tu lugar?'),
        ('Pago pendiente',
         f'Hola {nombre}, te escribimos de Área Latina. Nos aparece un pago '
         f'pendiente en tu ficha. ¿Lo vemos?'),
        ('Renovación de plan',
         f'Hola {nombre}, te escribimos de Área Latina. Puedes renovar tu '
         f'{plan} por ${valor}. ¿Te lo dejamos listo?'),
        ('Hace tiempo que no vienes',
         f'Hola {nombre}, te escribimos de Área Latina. Hace un tiempo que no '
         f'te vemos por la sala. ¿Todo bien? Te echamos de menos.'),
    ]

    return {
        'numero': numero,
        'base': f'https://wa.me/{numero}',
        'opciones': [
            {'titulo': titulo, 'texto': texto,
             'url': f'https://wa.me/{numero}?text={quote(texto)}'}
            for titulo, texto in plantillas
        ],
    }


# ---------------------------------------------------------------------------
# 2.4 Edición
# ---------------------------------------------------------------------------
@gestion_requerida
def alumno_editar(request, pk):
    alumno = get_object_or_404(Alumno, pk=pk)

    if request.method == 'POST':
        # Se guarda antes de tocar nada: despues de form.save() el valor
        # viejo ya no existe en ninguna parte.
        email_anterior = alumno.email

        form = AlumnoForm(request.POST, request.FILES, instance=alumno)
        if form.is_valid():
            alumno = form.save(commit=False)
            alumno.actualizado_por = request.user
            alumno.save()

            cambios = ', '.join(form.changed_data) or 'sin cambios de campo'
            registrar(request, AuditLog.Accion.EDITAR, alumno,
                      f'Editó a {alumno.nombre_completo} ({cambios})')
            messages.success(request, 'Datos actualizados.')

            # Si el email cambio de verdad, la ficha ofrece reenviar el
            # acceso. No se reenvia solo: puede ser una correccion menor
            # (una mayuscula) y mandar otro correo confundiria al alumno.
            if 'email' in form.changed_data and alumno.email:
                request.session['email_corregido'] = {
                    'alumno': alumno.pk,
                    'anterior': email_anterior or '(estaba vacío)',
                    'nuevo': alumno.email,
                }

            return redirect('gestion:alumno_detalle', pk=alumno.pk)
        messages.error(request, 'Revisa los datos: hay campos con errores.')
    else:
        form = AlumnoForm(instance=alumno)

    return render(request, 'gestion/alumnos/formulario.html', {
        'activo': 'alumnos',
        'form': form,
        'alumno': alumno,
        'editando': True,
    })


# ---------------------------------------------------------------------------
# Acciones sobre la ficha
# ---------------------------------------------------------------------------
@gestion_requerida
def alumno_estado(request, pk):
    """Suspender / reactivar."""
    if request.method != 'POST':
        return redirect('gestion:alumno_detalle', pk=pk)

    alumno = get_object_or_404(Alumno, pk=pk)
    nuevo = request.POST.get('estado')
    if nuevo not in dict(Alumno.Estado.choices):
        messages.error(request, 'Estado no válido.')
        return redirect('gestion:alumno_detalle', pk=pk)

    alumno.estado = nuevo
    alumno.actualizado_por = request.user
    alumno.save(update_fields=['estado', 'actualizado_por', 'updated_at'])

    registrar(request, AuditLog.Accion.EDITAR, alumno,
              f'Cambió el estado de {alumno.nombre_completo} a {alumno.get_estado_display()}')
    messages.success(request, f'{alumno.nombre_completo} ahora está {alumno.get_estado_display().lower()}.')
    return redirect('gestion:alumno_detalle', pk=pk)


@gestion_requerida
def alumno_eliminar(request, pk):
    """Borrado lógico: la ficha desaparece del listado pero no se pierde nada."""
    if request.method != 'POST':
        return redirect('gestion:alumno_detalle', pk=pk)

    alumno = get_object_or_404(Alumno, pk=pk)
    nombre = alumno.nombre_completo
    alumno.eliminar_logico(request.user)

    registrar(request, AuditLog.Accion.ELIMINAR, alumno, f'Eliminó a {nombre}')
    messages.success(request, f'{nombre} fue eliminado. Su historial se conserva.')
    return redirect('gestion:alumnos')


@gestion_requerida
def alumno_renovar(request, pk):
    if request.method != 'POST':
        return redirect('gestion:alumno_detalle', pk=pk)

    alumno = get_object_or_404(Alumno, pk=pk)
    form = RenovarPlanForm(request.POST)

    if not form.is_valid():
        messages.error(request, 'No se pudo renovar: revisa el plan y la fecha.')
        return redirect('gestion:alumno_detalle', pk=pk)

    datos = form.cleaned_data
    with transaction.atomic():
        # La suscripción anterior se cierra para no dejar dos activas.
        alumno.suscripciones.filter(estado=Suscripcion.Estado.ACTIVA).update(
            estado=Suscripcion.Estado.VENCIDA
        )
        suscripcion = Suscripcion.objects.create(
            alumno=alumno,
            plan=datos['plan'],
            fecha_inicio=datos['fecha_inicio'],
        )
        if datos.get('registrar_pago'):
            Pago.objects.create(
                alumno=alumno,
                suscripcion=suscripcion,
                concepto=Pago.Concepto.MENSUALIDAD,
                monto_clp=datos['plan'].precio_clp,
                metodo=datos.get('metodo') or Pago.Metodo.EFECTIVO,
                estado=Pago.Estado.PAGADO,
                registrado_por=request.user,
            )

        # Renovar resuelve las alertas de vencimiento del alumno.
        alumno.alertas.filter(gestionada=False).exclude(
            tipo='PAGO_PENDIENTE'
        ).update(gestionada=True, gestionada_en=timezone.now(), gestionada_por=request.user)

    registrar(request, AuditLog.Accion.RENOVAR, alumno,
              f'Renovó el plan de {alumno.nombre_completo}: {suscripcion.plan.nombre}')

    aviso = f'Plan renovado hasta el {suscripcion.fecha_vencimiento:%d/%m/%Y}.'
    if datos.get('registrar_pago') and alumno.email:
        pago = suscripcion.pagos.order_by('-id').first()
        if pago and enviar_recibo(pago)[0]:
            aviso += ' Le enviamos el comprobante.'
    messages.success(request, aviso)
    return redirect('gestion:alumno_detalle', pk=pk)


@gestion_requerida
def alumno_nota(request, pk):
    if request.method != 'POST':
        return redirect('gestion:alumno_detalle', pk=pk)

    alumno = get_object_or_404(Alumno, pk=pk)
    form = NotaInternaForm(request.POST)
    if form.is_valid():
        nota = form.save(commit=False)
        nota.alumno = alumno
        nota.autor = request.user
        nota.save()
        messages.success(request, 'Nota guardada.')
    else:
        messages.error(request, 'La nota no puede ir vacía.')
    return redirect('gestion:alumno_detalle', pk=pk)


# ---------------------------------------------------------------------------
# Exportación
# ---------------------------------------------------------------------------
@gestion_requerida
def alumnos_exportar(request):
    from ..excel import exportar_alumnos

    qs = _alumnos_filtrados(request)
    contenido = exportar_alumnos(qs)

    respuesta = HttpResponse(
        contenido,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    nombre = f'alumnos_{timezone.localdate():%Y-%m-%d}.xlsx'
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return respuesta
