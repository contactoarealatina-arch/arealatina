"""Portal del alumno: su plan, sus clases, sus pagos y su perfil."""
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
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
        'plan': _detalle_del_plan(alumno, suscripcion),
        'semana': _semana_del_alumno(alumno),
        # Solo el último, y solo para que pueda confirmar que su pago se
        # registró. El historial completo se quitó: ver la suma de todo lo
        # que lleva gastado en bailar no le sirve de nada y desanima.
        'ultimo_pago': alumno.pagos.filter(estado=Pago.Estado.PAGADO).first(),
        'whatsapp': _enlace_whatsapp(alumno, 'renovar'),
    })


def _detalle_del_plan(alumno, suscripcion):
    """Lo que el alumno necesita saber de su plan.

    Es lo primero que mira al entrar: qué contrató, hasta cuándo le sirve
    y qué incluye. Antes era una línea con la fecha de vencimiento.
    """
    if not suscripcion or not suscripcion.plan:
        return None

    plan = suscripcion.plan
    hoy = timezone.localdate()

    total = (suscripcion.fecha_vencimiento - suscripcion.fecha_inicio).days
    usados = (hoy - suscripcion.fecha_inicio).days
    # Se limita entre 0 y 100: un plan vencido no muestra 130% consumido,
    # y uno que parte mañana no muestra negativo.
    avance = max(0, min(100, round(usados / total * 100))) if total > 0 else 0

    inscritas = alumno.inscripciones.count()
    cubre = plan.clases_incluidas

    return {
        'plan': plan,
        'suscripcion': suscripcion,
        'avance': avance,
        'dias_totales': total,
        'inscritas': inscritas,
        'cubre': cubre,
        # None cuando el plan es ilimitado: no hay cupo que llenar.
        'le_sobran': (cubre - inscritas) if cubre is not None else None,
        'pasado': cubre is not None and inscritas > cubre,
        'beneficios': plan.beneficios_lista,
        'pilares': list(plan.pilares.all()),
    }


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


def _destino_de(usuario):
    """A dónde mandarlo según su rol, después de poner su contraseña."""
    if usuario.puede_gestionar:
        return 'gestion:dashboard'
    if usuario.es_profesor:
        return 'profesoras:panel'
    return 'portal:panel'


@login_required
def cambiar_clave(request):
    if request.method == 'POST':
        form = CambiarClaveForm(request.user, request.POST)
        if form.is_valid():
            usuario = form.guardar()

            # Se apaga la marca: la clave que viajó por correo ya no vale
            # y la persona puede usar el sistema.
            era_temporal = usuario.debe_cambiar_clave
            if era_temporal:
                usuario.debe_cambiar_clave = False
                usuario.save(update_fields=['debe_cambiar_clave', 'updated_at'])

            # Cambiar la clave invalida la sesión: se vuelve a iniciar.
            usuario.backend = 'apps.usuarios.backends.CorreoOUsuarioBackend'
            login(request, usuario)

            if era_temporal:
                messages.success(
                    request,
                    'Listo, tu contraseña quedó puesta. Ya puedes usar tu espacio.',
                )
                return redirect(_destino_de(usuario))

            messages.success(request, 'Tu contraseña quedó cambiada.')
            return redirect('portal:perfil')
    else:
        form = CambiarClaveForm(request.user)

    return render(request, 'portal/cambiar_clave.html', {
        'activo': 'perfil',
        'form': form,
    })
