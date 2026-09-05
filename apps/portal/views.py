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


# ---------------------------------------------------------------------------
# Términos y condiciones
# ---------------------------------------------------------------------------
@alumno_requerido
def terminos(request):
    """Pantalla obligatoria antes de entrar al portal.

    No se puede saltar: el decorador redirige acá desde cualquier vista
    mientras falte la aceptación. Al aceptar se manda un correo con copia
    de lo aceptado, que es la evidencia del consentimiento informado que
    pide la Ley 21.719.
    """
    from apps.gestion.models import AceptacionTerminos, TerminoCondicion

    vigente = TerminoCondicion.vigente()
    if vigente is None:
        return redirect('portal:panel')

    ya = AceptacionTerminos.objects.filter(
        usuario=request.user, termino=vigente,
    ).first()
    if ya:
        return redirect('portal:panel')

    if request.method == 'POST':
        if not request.POST.get('acepto'):
            messages.error(
                request,
                'Tienes que marcar la casilla para poder continuar.',
            )
        else:
            from apps.gestion.correos import enviar_confirmacion_terminos

            aceptacion = AceptacionTerminos.objects.create(
                usuario=request.user,
                alumno=request.alumno,
                termino=vigente,
                ip=_ip_del_visitante(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:250],
            )
            enviar_confirmacion_terminos(aceptacion)

            messages.success(request, 'Gracias. Ya puedes usar tu portal.')
            return redirect('portal:panel')

    return render(request, 'portal/terminos.html', {
        'activo': 'terminos',
        'termino': vigente,
    })


def _ip_del_visitante(request):
    """La IP real, mirando primero la cabecera del proxy.

    En Railway la petición llega por un balanceador, así que REMOTE_ADDR
    es la del balanceador y no la de la persona.
    """
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if reenviada:
        return reenviada.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@alumno_requerido
def panel(request):
    """Todo lo que el alumno necesita, en una sola pantalla.

    Antes eran tres páginas —panel, mis clases y mi plan— y ninguna se
    entendía sola: el plan estaba en una, el horario en otra. Ahora al
    entrar ve su plan y su semana, que es a lo que viene.
    """
    alumno = request.alumno
    servicios.vencer_suscripciones_pasadas()

    suscripcion = alumno.suscripcion_vigente
    if not suscripcion:
        suscripcion = alumno.suscripciones.order_by('-fecha_vencimiento').first()

    dias = alumno.dias_para_vencer

    return render(request, 'portal/panel.html', {
        'activo': 'panel',
        'alumno': alumno,
        'suscripcion': suscripcion,
        'dias_restantes': dias,
        'estado_pago': alumno.estado_pago,
        'avisar_renovacion': dias is not None and dias <= 7,
        'semana': _semana_del_alumno(alumno),
        'ultimos_pagos': alumno.pagos.filter(estado=Pago.Estado.PAGADO)[:3],
        'whatsapp': _enlace_whatsapp(alumno, 'renovar'),
    })


def _semana_del_alumno(alumno):
    """Las clases de los próximos siete días, agrupadas por día.

    Sin estados ni botones: día, hora y sala. Lo que ya pasó se marca
    solo si la profesora alcanzó a pasar lista, y es informativo.
    """
    hoy = timezone.localdate()
    ahora = timezone.now()

    marcas = {
        (r.clase_id, r.fecha): r.estado
        for r in RegistroAsistencia.objects.filter(alumno=alumno, fecha__gte=hoy)
    }

    dias = {}
    for sesion in servicios.sesiones_proximas(
        _clases_del_alumno(alumno), dias=7, desde=hoy
    ):
        clase = sesion['clase']
        fecha = sesion['fecha']
        inicio = servicios.inicio_sesion(sesion)
        fin = timezone.make_aware(
            datetime.combine(fecha, clase.hora_fin),
            timezone.get_current_timezone(),
        )

        dias.setdefault(fecha, []).append({
            'clase': clase,
            'fecha': fecha,
            'inicio': inicio,
            'en_curso': inicio <= ahora <= fin,
            'paso': ahora > fin,
            'asistencia': marcas.get((clase.pk, fecha)),
        })

    return [
        {'fecha': fecha, 'es_hoy': fecha == hoy, 'clases': clases}
        for fecha, clases in sorted(dias.items())
    ]


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


@alumno_requerido
def solicitar_renovacion(request):
    if request.method != 'POST':
        return redirect('portal:panel')

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
    return redirect('portal:panel')


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
