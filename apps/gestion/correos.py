"""Todos los correos que manda el sistema.

Se envían por el relay SMTP de Brevo. Cada envío queda registrado en
CorreoEnviado, por dos motivos concretos:

- No repetir un aviso que ya se mandó (el cron corre todos los días).
- Poder responder "sí se envió / no se envió y este fue el error" cuando
  alguien reclama que no le llegó nada.

Ninguna función de este módulo lanza excepciones: si el correo falla, la
operación que lo originó (inscribir, cobrar) ya se completó y no debe
deshacerse por un problema de email.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import ConfiguracionAlertas, CorreoEnviado
from .servicios import nombre_mes, variacion

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Motor de envío
# ---------------------------------------------------------------------------
def _enviar(tipo, destinatarios, asunto, plantilla, contexto,
            alumno=None, referencia=''):
    """Renderiza, envía y registra. Devuelve (enviado, motivo)."""
    destinatarios = [d for d in destinatarios if d]
    if not destinatarios:
        return False, 'Sin destinatario: el alumno no tiene email registrado.'

    # Si ya se mandó este mismo aviso, no se repite.
    if referencia and CorreoEnviado.objects.filter(
        tipo=tipo, referencia=referencia, enviado=True
    ).exists():
        return False, 'Ya se había enviado este aviso.'

    contexto = {**contexto, 'academia': settings.ACADEMIA}

    try:
        html = render_to_string(f'gestion/emails/{plantilla}.html', contexto)
        texto = render_to_string(f'gestion/emails/{plantilla}.txt', contexto)
    except Exception as error:
        logger.exception('No se pudo armar el correo %s', plantilla)
        return False, f'Error al armar el correo: {error}'

    mensaje = EmailMultiAlternatives(
        subject=asunto,
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=destinatarios,
        reply_to=[settings.ACADEMIA['email']],
    )
    mensaje.attach_alternative(html, 'text/html')

    registro = CorreoEnviado(
        tipo=tipo,
        destinatario=destinatarios[0],
        asunto=asunto[:250],
        alumno=alumno,
        referencia=referencia[:60],
    )

    try:
        mensaje.send(fail_silently=False)
        registro.enviado = True
        registro.save()
        return True, f'Enviado a {", ".join(destinatarios)}.'
    except Exception as error:
        registro.enviado = False
        registro.error = str(error)[:2000]
        registro.save()
        logger.warning('Falló el correo %s a %s: %s', tipo, destinatarios, error)
        return False, f'No se pudo enviar: {error}'


def _url(nombre, *args):
    """URL absoluta para los botones de los correos.

    En el correo no sirve una ruta relativa: se abre desde Gmail, no desde
    el sitio. El dominio sale de settings.SITIO_URL.
    """
    from django.urls import reverse

    base = getattr(settings, 'SITIO_URL', 'http://localhost:8000').rstrip('/')
    return f'{base}{reverse(nombre, args=args)}'


def _configurado():
    """En producción sin clave SMTP no se intenta siquiera."""
    if settings.DEBUG:
        return True
    return bool(settings.EMAIL_HOST_PASSWORD)


# ---------------------------------------------------------------------------
# 1. Bienvenida
# ---------------------------------------------------------------------------
def enviar_bienvenida(alumno, enlace_activacion='', usuario=None):
    config = ConfiguracionAlertas.obtener()
    if not config.enviar_bienvenida or not _configurado():
        return False, 'Correo de bienvenida desactivado.'

    suscripcion = alumno.suscripcion_vigente
    return _enviar(
        tipo=CorreoEnviado.Tipo.BIENVENIDA,
        destinatarios=[alumno.email],
        asunto=f'¡Bienvenido/a a Área Latina Estudio, {alumno.nombre_completo.split()[0]}!',
        plantilla='bienvenida',
        contexto={
            'alumno': alumno,
            'suscripcion': suscripcion,
            'clases': [i.clase for i in alumno.inscripciones.select_related('clase')],
            'enlace': enlace_activacion,
            'usuario': usuario or alumno.usuario,
            'url_portal': _url('portal:login'),
        },
        alumno=alumno,
        referencia=f'BIENVENIDA-{alumno.pk}',
    )


# ---------------------------------------------------------------------------
# 2. Comprobante de pago
# ---------------------------------------------------------------------------
def enviar_recibo(pago):
    config = ConfiguracionAlertas.obtener()
    if not config.enviar_recibos or not _configurado():
        return False, 'Comprobantes desactivados.'
    if pago.estado != pago.Estado.PAGADO:
        return False, 'El pago no está marcado como pagado.'

    return _enviar(
        tipo=CorreoEnviado.Tipo.RECIBO,
        destinatarios=[pago.alumno.email],
        asunto=f'Comprobante de pago · Área Latina Estudio',
        plantilla='recibo_pago',
        contexto={
            'pago': pago,
            'alumno': pago.alumno,
            'suscripcion': pago.suscripcion,
        },
        alumno=pago.alumno,
        referencia=f'RECIBO-{pago.pk}',
    )


# ---------------------------------------------------------------------------
# 3. Aviso de vencimiento al alumno
# ---------------------------------------------------------------------------
def enviar_recordatorio(suscripcion):
    config = ConfiguracionAlertas.obtener()
    if not config.enviar_recordatorios or not _configurado():
        return False, 'Recordatorios desactivados.'

    alumno = suscripcion.alumno
    dias = suscripcion.dias_restantes

    if dias < 0:
        asunto = 'Tu plan en Área Latina venció'
    elif dias == 0:
        asunto = 'Tu plan en Área Latina vence hoy'
    else:
        asunto = f'Tu plan en Área Latina vence en {dias} día{"s" if dias != 1 else ""}'

    return _enviar(
        tipo=CorreoEnviado.Tipo.RECORDATORIO,
        destinatarios=[alumno.email],
        asunto=asunto,
        plantilla='recordatorio',
        contexto={
            'alumno': alumno,
            'suscripcion': suscripcion,
            'dias': dias,
            'vencido': dias < 0,
        },
        alumno=alumno,
        # Una vez por suscripción y por fecha de vencimiento: si renueva,
        # la nueva suscripción tiene otra referencia y sí puede avisar.
        referencia=f'RECORD-{suscripcion.pk}-{suscripcion.fecha_vencimiento:%Y%m%d}',
    )


# ---------------------------------------------------------------------------
# 3b. Bienvenida a la profesora
# ---------------------------------------------------------------------------
def enviar_bienvenida_profesora(profesora, enlace_activacion=''):
    """Se manda cuando la administración le crea la cuenta."""
    if not _configurado():
        return False, 'SMTP sin configurar.'
    if not profesora.email:
        return False, 'La profesora no tiene email registrado.'

    from .models import Clase

    return _enviar(
        tipo=CorreoEnviado.Tipo.BIENV_PROFE,
        destinatarios=[profesora.email],
        asunto=f'Bienvenida al equipo, {profesora.nombre_corto} — Área Latina',
        plantilla='bienvenida_profesora',
        contexto={
            'profesora': profesora,
            'clases': Clase.objects.filter(profesora=profesora, activa=True),
            'enlace': enlace_activacion,
            'url_portal': _url('profesoras:panel'),
        },
        referencia=f'BIENVPROF-{profesora.pk}',
    )


# ---------------------------------------------------------------------------
# 3c. Recordatorio del día a la profesora
# ---------------------------------------------------------------------------
def enviar_recordatorio_profesora(profesora, clases_hoy, fecha):
    """Un solo correo por profesora al día, con todas sus clases juntas.

    Mandar uno por clase sería spam para quien dicta tres seguidas.
    """
    if not _configurado() or not profesora.email or not clases_hoy:
        return False, 'Sin datos para enviar.'

    cantidad = len(clases_hoy)
    return _enviar(
        tipo=CorreoEnviado.Tipo.REC_PROFE,
        destinatarios=[profesora.email],
        asunto=f'Hoy tienes {cantidad} clase{"s" if cantidad != 1 else ""} — Área Latina',
        plantilla='recordatorio_profesora',
        contexto={
            'profesora': profesora,
            'clases': clases_hoy,
            'fecha': fecha,
            'cantidad': cantidad,
            'url_portal': _url('profesoras:panel'),
        },
        referencia=f'RECPROF-{profesora.pk}-{fecha:%Y%m%d}',
    )


def enviar_recordatorios_profesoras(fecha=None):
    """Recorre las profesoras con clase hoy y les manda su resumen."""
    from django.contrib.auth import get_user_model

    from .models import Clase, ConfirmacionAsistencia
    from .servicios import clase_ocurre_en

    fecha = fecha or timezone.localdate()
    Usuario = get_user_model()

    enviados = omitidos = 0
    for profesora in Usuario.objects.filter(rol=Usuario.Rol.PROFESOR, is_active=True):
        clases = [
            c for c in Clase.objects.filter(profesora=profesora, activa=True)
            if clase_ocurre_en(c, fecha)
        ]
        if not clases:
            continue

        detalle = [{
            'clase': clase,
            'inscritos': clase.inscripciones.filter(alumno__eliminado=False).count(),
            'confirmados': ConfirmacionAsistencia.objects.filter(
                clase=clase, fecha=fecha).count(),
        } for clase in sorted(clases, key=lambda c: c.hora_inicio)]

        ok, _ = enviar_recordatorio_profesora(profesora, detalle, fecha)
        enviados += int(ok)
        omitidos += int(not ok)

    return enviados, omitidos


# ---------------------------------------------------------------------------
# 4. Mensaje del formulario web, al equipo
# ---------------------------------------------------------------------------
def enviar_mensaje_contacto(mensaje_web):
    if not _configurado():
        return False, 'SMTP sin configurar.'

    return _enviar(
        tipo=CorreoEnviado.Tipo.CONTACTO,
        destinatarios=[settings.ACADEMIA['email']],
        asunto=f'Nuevo mensaje web de {mensaje_web.nombre}',
        plantilla='mensaje_contacto',
        contexto={'mensaje': mensaje_web},
        referencia=f'CONTACTO-{mensaje_web.pk}',
    )


# ---------------------------------------------------------------------------
# 4b. Recordatorio de clase al alumno (la víspera)
# ---------------------------------------------------------------------------
def enviar_recordatorio_clase(alumno, clase, fecha):
    if not _configurado() or not alumno.email:
        return False, 'Sin email.'

    return _enviar(
        tipo=CorreoEnviado.Tipo.RECORDATORIO_CLASE,
        destinatarios=[alumno.email],
        asunto=f'Mañana tienes {clase.get_nombre_display()} a las {clase.hora_inicio:%H:%M} — Área Latina',
        plantilla='recordatorio_clase',
        contexto={
            'alumno': alumno,
            'clase': clase,
            'fecha': fecha,
            'url_confirmar': _url('portal:confirmar', clase.pk, fecha.isoformat()),
            'url_mapa': _mapa(),
        },
        alumno=alumno,
        referencia=f'RECCLASE-{alumno.pk}-{clase.pk}-{fecha:%Y%m%d}',
    )


def enviar_recordatorios_clases(fecha=None):
    """Avisa a los alumnos de las clases de mañana que aún no confirmaron.

    Al que ya confirmó no se le escribe: sería insistirle por algo que ya hizo.
    """
    from .models import Alumno, Clase, ConfirmacionAsistencia
    from .servicios import clase_ocurre_en

    manana = fecha or (timezone.localdate() + timedelta(days=1))

    enviados = omitidos = 0
    for clase in Clase.objects.filter(activa=True).select_related('profesora'):
        if not clase_ocurre_en(clase, manana):
            continue

        ya_confirmaron = set(
            ConfirmacionAsistencia.objects
            .filter(clase=clase, fecha=manana)
            .values_list('alumno_id', flat=True)
        )

        inscritos = clase.inscripciones.filter(
            alumno__eliminado=False,
            alumno__estado=Alumno.Estado.ACTIVO,
        ).select_related('alumno')

        for inscripcion in inscritos:
            alumno = inscripcion.alumno
            if alumno.pk in ya_confirmaron or not alumno.email:
                omitidos += 1
                continue
            ok, _ = enviar_recordatorio_clase(alumno, clase, manana)
            enviados += int(ok)
            omitidos += int(not ok)

    return enviados, omitidos


# ---------------------------------------------------------------------------
# 4c. Confirmación de asistencia
# ---------------------------------------------------------------------------
def enviar_confirmacion_asistencia(confirmacion):
    alumno = confirmacion.alumno
    if not _configurado() or not alumno.email:
        return False, 'Sin email.'

    return _enviar(
        tipo=CorreoEnviado.Tipo.CONFIRMACION,
        destinatarios=[alumno.email],
        asunto=f'Asistencia confirmada · {confirmacion.clase.get_nombre_display()} '
               f'{confirmacion.fecha:%d/%m}',
        plantilla='confirmacion_asistencia',
        contexto={
            'alumno': alumno,
            'clase': confirmacion.clase,
            'fecha': confirmacion.fecha,
            'url_mapa': _mapa(),
        },
        alumno=alumno,
        referencia=f'CONF-{confirmacion.pk}',
    )


# ---------------------------------------------------------------------------
# 4d. Avisos internos al equipo
# ---------------------------------------------------------------------------
def avisar_solicitud_renovacion(alumno):
    """El alumno pidió renovar desde su portal."""
    if not _configurado():
        return False, 'SMTP sin configurar.'

    suscripcion = (alumno.suscripcion_vigente
                   or alumno.suscripciones.order_by('-fecha_vencimiento').first())

    return _enviar(
        tipo=CorreoEnviado.Tipo.CONTACTO,
        destinatarios=ConfiguracionAlertas.obtener().lista_emails,
        asunto=f'{alumno.nombre_completo} quiere renovar su plan',
        plantilla='solicitud_renovacion',
        contexto={
            'alumno': alumno,
            'suscripcion': suscripcion,
            'url_ficha': _url('gestion:alumno_detalle', alumno.pk),
        },
        alumno=alumno,
        referencia=f'RENOV-{alumno.pk}-{timezone.localdate():%Y%m%d}',
    )


def avisar_token_expirado(usuario):
    """Alguien intentó activar su cuenta con un enlace vencido."""
    if not _configurado():
        return False, 'SMTP sin configurar.'

    return _enviar(
        tipo=CorreoEnviado.Tipo.CONTACTO,
        destinatarios=ConfiguracionAlertas.obtener().lista_emails,
        asunto=f'{usuario.get_full_name() or usuario.username} necesita un enlace nuevo',
        plantilla='token_expirado',
        contexto={'usuario': usuario},
        referencia=f'TOKENEXP-{usuario.pk}-{timezone.localdate():%Y%m%d}',
    )


def _mapa():
    from urllib.parse import quote

    direccion = settings.ACADEMIA.get('direccion_maps', '')
    return f'https://www.google.com/maps/dir/?api=1&destination={quote(direccion)}'


# ---------------------------------------------------------------------------
# 5. Resumen diario al equipo
# ---------------------------------------------------------------------------
def enviar_resumen(resumen):
    config = ConfiguracionAlertas.obtener()

    if not config.envio_activo:
        return False, 'El resumen diario está desactivado.'
    if not _configurado():
        return False, 'Falta la clave SMTP en el archivo .env.'

    destinatarios = config.lista_emails
    if not destinatarios:
        return False, 'No hay destinatarios configurados.'

    if not (resumen['por_vencer'] or resumen['vencidos'] or resumen['sin_pago']):
        return False, 'No hay nada que informar hoy.'

    fecha = resumen['fecha']
    return _enviar(
        tipo=CorreoEnviado.Tipo.RESUMEN,
        destinatarios=destinatarios,
        asunto=f'Área Latina — Resumen de alertas {fecha:%d/%m/%Y}',
        plantilla='resumen_alertas',
        contexto={
            'fecha': fecha,
            'mes': nombre_mes(fecha),
            'por_vencer': resumen['por_vencer'],
            'vencidos': resumen['vencidos'],
            'sin_pago': resumen['sin_pago'],
        },
        referencia=f'RESUMEN-{fecha:%Y%m%d}',
    )


# ---------------------------------------------------------------------------
# Recordatorios masivos (los llama el cron)
# ---------------------------------------------------------------------------
def enviar_recordatorios_del_dia(resumen):
    """Avisa a cada alumno con plan por vencer o recién vencido.

    Devuelve (enviados, omitidos). Los omitidos son casi siempre alumnos
    sin email registrado o avisos que ya se mandaron.
    """
    config = ConfiguracionAlertas.obtener()
    if not config.enviar_recordatorios:
        return 0, 0

    enviados = omitidos = 0
    for item in resumen['por_vencer'] + resumen['vencidos']:
        alumno = item['alumno']
        suscripcion = (
            alumno.suscripcion_vigente
            or alumno.suscripciones.order_by('-fecha_vencimiento').first()
        )
        if not suscripcion:
            omitidos += 1
            continue

        ok, _ = enviar_recordatorio(suscripcion)
        enviados += int(ok)
        omitidos += int(not ok)

    return enviados, omitidos


# ---------------------------------------------------------------------------
# 6. Cumpleaños
# ---------------------------------------------------------------------------
def enviar_cumpleanos(alumno, clase_hoy=None):
    if not _configurado() or not alumno.email:
        return False, 'Sin email.'

    hoy = timezone.localdate()
    return _enviar(
        tipo=CorreoEnviado.Tipo.CUMPLEANOS,
        destinatarios=[alumno.email],
        asunto=f'¡Feliz cumpleaños, {alumno.primer_nombre}! — Área Latina',
        plantilla='cumpleanos',
        contexto={'alumno': alumno, 'clase_hoy': clase_hoy, 'hoy': hoy},
        alumno=alumno,
        referencia=f'CUMPLE-{alumno.pk}-{hoy:%Y}',
    )


def enviar_saludos_cumpleanos(fecha=None):
    """Saluda a quien cumple hoy, una vez al año."""
    from .servicios import clase_ocurre_en, cumpleaneros

    fecha = fecha or timezone.localdate()
    enviados = 0

    for alumno in cumpleaneros(fecha):
        clase_hoy = next(
            (i.clase for i in alumno.inscripciones.select_related('clase')
             if i.clase.activa and clase_ocurre_en(i.clase, fecha)),
            None,
        )
        ok, _ = enviar_cumpleanos(alumno, clase_hoy)
        enviados += int(ok)

    return enviados


# ---------------------------------------------------------------------------
# 7. Aviso de ausencia prolongada al equipo
# ---------------------------------------------------------------------------
def avisar_ausencias(detectados):
    """Un solo correo con todos los que llevan tiempo sin venir."""
    if not _configurado() or not detectados:
        return False, 'Nada que informar.'

    hoy = timezone.localdate()
    cantidad = len(detectados)

    return _enviar(
        tipo=CorreoEnviado.Tipo.AUSENCIA,
        destinatarios=ConfiguracionAlertas.obtener().lista_emails,
        asunto=f'{cantidad} alumno{"s" if cantidad != 1 else ""} '
               f'lleva{"n" if cantidad != 1 else ""} 2 semanas sin venir',
        plantilla='ausencias',
        contexto={
            'detectados': detectados,
            'cantidad': cantidad,
            'hoy': hoy,
            'url_alertas': _url('gestion:alertas'),
        },
        referencia=f'AUSENCIA-{hoy:%Y%m%d}',
    )


# ---------------------------------------------------------------------------
# 8. Informe mensual al dueño
# ---------------------------------------------------------------------------
def enviar_informe_mensual(referencia=None):
    from .servicios import cierre_mensual

    if not _configurado():
        return False, 'SMTP sin configurar.'

    datos = cierre_mensual(referencia)

    return _enviar(
        tipo=CorreoEnviado.Tipo.INFORME,
        destinatarios=ConfiguracionAlertas.obtener().lista_emails,
        asunto=f'Cierre de {datos["nombre_mes"]} — Área Latina',
        plantilla='informe_mensual',
        contexto={
            **datos,
            'variacion_ingresos': variacion(datos['ingresos'], datos['ingresos_previo']),
            'url_resumen': _url('gestion:resumen_financiero'),
        },
        referencia=f'INFORME-{datos["inicio"]:%Y%m}',
    )
