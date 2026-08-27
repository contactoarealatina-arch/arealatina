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

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import ConfiguracionAlertas, CorreoEnviado
from .servicios import nombre_mes

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


def _configurado():
    """En producción sin clave SMTP no se intenta siquiera."""
    if settings.DEBUG:
        return True
    return bool(settings.EMAIL_HOST_PASSWORD)


# ---------------------------------------------------------------------------
# 1. Bienvenida
# ---------------------------------------------------------------------------
def enviar_bienvenida(alumno):
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
