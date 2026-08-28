"""Portal del alumno: su plan, sus clases, sus pagos y su perfil."""
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from apps.asistencia.models import RegistroAsistencia
from apps.gestion import servicios
from apps.gestion.models import (
    ConfirmacionAsistencia,
    Pago,
    Suscripcion,
    TokenActivacion,
)
from apps.usuarios.views import LoginSeguro

from .forms import CambiarClaveForm, ClaveNuevaForm, PerfilForm
from .permisos import alumno_requerido


class PortalLogin(LoginSeguro):
    """Mismo motor de login (con su freno a la fuerza bruta), otra portada."""

    template_name = 'portal/login.html'


# ---------------------------------------------------------------------------
# 2.1 Activación con enlace de un solo uso
# ---------------------------------------------------------------------------
def activar(request, token):
    registro = TokenActivacion.objects.filter(token=token).select_related('usuario').first()

    if registro is None or not registro.valido:
        return redirect('portal:token_expirado', token=token)

    usuario = registro.usuario

    if request.method == 'POST':
        form = ClaveNuevaForm(usuario, request.POST)
        if form.is_valid():
            form.guardar()
            registro.marcar_usado()

            usuario.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, usuario)

            messages.success(request, '¡Listo! Tu cuenta quedó activada.')
            if usuario.es_profesor:
                return redirect('profesoras:panel')
            return redirect('portal:panel')
    else:
        form = ClaveNuevaForm(usuario)

    return render(request, 'portal/activar.html', {
        'form': form,
        'usuario': usuario,
        'es_profesora': usuario.es_profesor,
    })


def token_expirado(request, token):
    """El enlace venció o ya se usó. Se le ofrece pedir uno nuevo."""
    if request.method == 'POST':
        from apps.gestion.correos import avisar_token_expirado

        registro = TokenActivacion.objects.filter(token=token).select_related('usuario').first()
        if registro:
            avisar_token_expirado(registro.usuario)
        messages.success(
            request,
            'Le avisamos a la administración. Te van a mandar un enlace nuevo.'
        )
        return redirect('portal:login')

    return render(request, 'portal/token_expirado.html')


# ---------------------------------------------------------------------------
# 2.2 Panel
# ---------------------------------------------------------------------------
def _clases_del_alumno(alumno):
    return [i.clase for i in alumno.inscripciones.select_related('clase__profesora')
            if i.clase.activa]


def _estado_barra(dias):
    """Color de la barra según lo que queda de plan."""
    if dias is None:
        return 'bien'
    if dias < 3:
        return 'urgente'
    if dias < 7:
        return 'pronto'
    if dias < 14:
        return 'atento'
    return 'bien'


@alumno_requerido
def panel(request):
    alumno = request.alumno
    servicios.vencer_suscripciones_pasadas()

    suscripcion = alumno.suscripcion_vigente
    if not suscripcion:
        suscripcion = alumno.suscripciones.order_by('-fecha_vencimiento').first()

    mis_clases = _clases_del_alumno(alumno)
    siguiente = servicios.proxima_sesion(mis_clases)

    ya_confirmada = False
    puede_confirmar_siguiente = False
    if siguiente:
        ya_confirmada = ConfirmacionAsistencia.objects.filter(
            alumno=alumno, clase=siguiente['clase'], fecha=siguiente['fecha']
        ).exists()
        puede_confirmar_siguiente = servicios.puede_confirmar(siguiente) and not ya_confirmada

    dias = alumno.dias_para_vencer

    return render(request, 'portal/panel.html', {
        'activo': 'panel',
        'alumno': alumno,
        'suscripcion': suscripcion,
        'dias_restantes': dias,
        'estado_pago': alumno.estado_pago,
        'color_barra': _estado_barra(dias),
        'siguiente': siguiente,
        'inicio_siguiente': servicios.inicio_sesion(siguiente) if siguiente else None,
        'ya_confirmada': ya_confirmada,
        'puede_confirmar': puede_confirmar_siguiente,
        'total_clases': len(mis_clases),
        'ultimos_pagos': alumno.pagos.filter(estado=Pago.Estado.PAGADO)[:3],
        'whatsapp': _enlace_whatsapp(alumno),
    })


def _enlace_whatsapp(alumno, motivo='renovar'):
    """Enlace a WhatsApp con el mensaje ya escrito. Sin API ni costo."""
    from django.conf import settings
    from urllib.parse import quote

    numero = (settings.ACADEMIA.get('whatsapp_numero') or '').strip()
    if not numero:
        return ''

    textos = {
        'renovar': f'Hola, soy {alumno.nombre_completo}. Quiero renovar mi plan en Área Latina.',
        'consulta': f'Hola, soy {alumno.nombre_completo}. Tengo una consulta.',
    }
    return f'https://wa.me/{numero}?text={quote(textos.get(motivo, textos["consulta"]))}'


# ---------------------------------------------------------------------------
# 2.3 Mis clases
# ---------------------------------------------------------------------------
@alumno_requerido
def clases(request):
    alumno = request.alumno
    mis_clases = _clases_del_alumno(alumno)
    hoy = timezone.localdate()
    ahora = timezone.now()

    confirmadas = {
        (c.clase_id, c.fecha)
        for c in ConfirmacionAsistencia.objects.filter(alumno=alumno, fecha__gte=hoy - timedelta(days=1))
    }
    marcas = {
        (r.clase_id, r.fecha): r.estado
        for r in RegistroAsistencia.objects.filter(
            alumno=alumno, fecha__gte=hoy - timedelta(days=1))
    }

    sesiones = []
    for sesion in servicios.sesiones_proximas(mis_clases, dias=7, desde=hoy):
        llave = (sesion['clase'].pk, sesion['fecha'])
        inicio = servicios.inicio_sesion(sesion)
        fin = timezone.make_aware(
            datetime.combine(sesion['fecha'], sesion['clase'].hora_fin),
            timezone.get_current_timezone())

        marca = marcas.get(llave)
        if marca == RegistroAsistencia.Estado.PRESENTE:
            estado = 'asistio'
        elif marca == RegistroAsistencia.Estado.AUSENTE:
            estado = 'ausente'
        elif marca == RegistroAsistencia.Estado.JUSTIFICADO:
            estado = 'justificado'
        elif inicio <= ahora <= fin:
            estado = 'en_curso'
        elif llave in confirmadas:
            estado = 'confirmada'
        elif servicios.puede_confirmar(sesion):
            estado = 'puede_confirmar'
        elif ahora > fin:
            estado = 'sin_confirmar'
        else:
            estado = 'fuera_de_plazo'

        sesiones.append({**sesion, 'estado': estado, 'inicio': inicio})

    return render(request, 'portal/clases.html', {
        'activo': 'clases',
        'alumno': alumno,
        'mis_clases': mis_clases,
        'sesiones': sesiones,
    })


# ---------------------------------------------------------------------------
# 2.4 Confirmar asistencia
# ---------------------------------------------------------------------------
@alumno_requerido
def confirmar(request, clase_id, fecha):
    alumno = request.alumno

    inscripcion = alumno.inscripciones.filter(clase_id=clase_id).select_related('clase').first()
    if inscripcion is None:
        messages.error(request, 'No estás inscrito en esa clase.')
        return redirect('portal:clases')

    clase = inscripcion.clase

    try:
        dia = datetime.fromisoformat(fecha).date()
    except (ValueError, TypeError):
        messages.error(request, 'Esa fecha no es válida.')
        return redirect('portal:clases')

    sesion = {'clase': clase, 'fecha': dia}

    if not servicios.clase_ocurre_en(clase, dia):
        messages.error(request, 'Esa clase no se dicta ese día.')
        return redirect('portal:clases')

    ya = ConfirmacionAsistencia.objects.filter(
        alumno=alumno, clase=clase, fecha=dia).exists()
    a_tiempo = servicios.puede_confirmar(sesion)

    if request.method == 'POST' and not ya and a_tiempo:
        from apps.gestion.correos import enviar_confirmacion_asistencia

        confirmacion = ConfirmacionAsistencia.objects.create(
            alumno=alumno, clase=clase, fecha=dia)
        enviar_confirmacion_asistencia(confirmacion)

        messages.success(request, f'Asistencia confirmada para el {dia:%d/%m}. ¡Te esperamos!')
        return redirect('portal:panel')

    return render(request, 'portal/confirmar.html', {
        'activo': 'clases',
        'clase': clase,
        'fecha': dia,
        'inicio': servicios.inicio_sesion(sesion),
        'ya_confirmada': ya,
        'a_tiempo': a_tiempo,
    })


# ---------------------------------------------------------------------------
# 2.5 Mi plan
# ---------------------------------------------------------------------------
@alumno_requerido
def plan(request):
    alumno = request.alumno
    servicios.vencer_suscripciones_pasadas()

    activa = alumno.suscripcion_vigente
    dias = alumno.dias_para_vencer

    return render(request, 'portal/plan.html', {
        'activo': 'plan',
        'alumno': alumno,
        'suscripcion': activa,
        'dias_restantes': dias,
        'color_barra': _estado_barra(dias),
        'estado_pago': alumno.estado_pago,
        'historial': alumno.suscripciones.select_related('plan'),
        'avisar': dias is not None and dias <= 7,
        'whatsapp': _enlace_whatsapp(alumno, 'renovar'),
    })


@alumno_requerido
def solicitar_renovacion(request):
    if request.method != 'POST':
        return redirect('portal:plan')

    from apps.gestion.correos import avisar_solicitud_renovacion

    enviado, _ = avisar_solicitud_renovacion(request.alumno)
    if enviado:
        messages.success(
            request,
            'Le avisamos a la academia que quieres renovar. Te van a contactar.'
        )
    else:
        messages.info(
            request,
            'Anotamos tu solicitud. Si tienes apuro, escríbenos por WhatsApp.'
        )
    return redirect('portal:plan')


# ---------------------------------------------------------------------------
# 2.6 Mis pagos
# ---------------------------------------------------------------------------
@alumno_requerido
def pagos(request):
    alumno = request.alumno
    hoy = timezone.localdate()

    del_anio = alumno.pagos.filter(
        estado=Pago.Estado.PAGADO, fecha_pago__year=hoy.year)
    total_anio = sum(p.monto_clp for p in del_anio)

    return render(request, 'portal/pagos.html', {
        'activo': 'pagos',
        'alumno': alumno,
        'pagos': alumno.pagos.select_related('suscripcion__plan'),
        'total_anio': total_anio,
        'anio': hoy.year,
    })


# ---------------------------------------------------------------------------
# 2.7 Mi perfil
# ---------------------------------------------------------------------------
@alumno_requerido
def perfil(request):
    alumno = request.alumno

    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=alumno)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tus datos quedaron guardados.')
            return redirect('portal:perfil')
        messages.error(request, 'Revisa los datos, hay algo que corregir.')
    else:
        form = PerfilForm(instance=alumno)

    return render(request, 'portal/perfil.html', {
        'activo': 'perfil',
        'alumno': alumno,
        'form': form,
    })


@alumno_requerido
def cambiar_clave(request):
    if request.method == 'POST':
        form = CambiarClaveForm(request.user, request.POST)
        if form.is_valid():
            usuario = form.guardar()
            # Cambiar la clave invalida la sesión: se vuelve a iniciar.
            usuario.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, usuario)
            messages.success(request, 'Tu contraseña quedó cambiada.')
            return redirect('portal:perfil')
    else:
        form = CambiarClaveForm(request.user)

    return render(request, 'portal/cambiar_clave.html', {
        'activo': 'perfil',
        'form': form,
    })
