"""Envío del resumen diario de alertas."""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import ConfiguracionAlertas
from .servicios import nombre_mes


def enviar_resumen(resumen):
    """Manda el correo con las alertas del día.

    Devuelve (enviado, motivo). Nunca lanza: si el SMTP está mal configurado
    el cron debe seguir corriendo igual, las alertas ya quedaron en el panel.
    """
    config = ConfiguracionAlertas.obtener()

    if not config.envio_activo:
        return False, 'El envío por correo está desactivado en la configuración.'

    destinatarios = config.lista_emails
    if not destinatarios:
        return False, 'No hay destinatarios configurados.'

    if not settings.EMAIL_HOST_PASSWORD and not settings.DEBUG:
        return False, 'Falta la contraseña SMTP en el archivo .env.'

    hay_algo = resumen['por_vencer'] or resumen['vencidos'] or resumen['sin_pago']
    if not hay_algo:
        return False, 'No hay nada que informar hoy.'

    fecha = resumen['fecha']
    contexto = {
        'fecha': fecha,
        'mes': nombre_mes(fecha),
        'por_vencer': resumen['por_vencer'],
        'vencidos': resumen['vencidos'],
        'sin_pago': resumen['sin_pago'],
        'academia': settings.ACADEMIA,
    }

    html = render_to_string('gestion/emails/resumen_alertas.html', contexto)
    texto = render_to_string('gestion/emails/resumen_alertas.txt', contexto)

    mensaje = EmailMultiAlternatives(
        subject=f'Área Latina — Resumen de alertas {fecha:%d/%m/%Y}',
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=destinatarios,
    )
    mensaje.attach_alternative(html, 'text/html')

    try:
        mensaje.send(fail_silently=False)
        return True, f'Enviado a {", ".join(destinatarios)}.'
    except Exception as error:
        return False, f'No se pudo enviar: {error}'
