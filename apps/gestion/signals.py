"""Captura automática de eventos de autenticación en la auditoría.

Registrar el login desde la vista funciona para el login propio, pero se
escapan el admin de Django, el cierre de sesión por expiración y los
intentos fallidos. Con señales queda cubierto todo, venga de donde venga.
"""
import logging

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

registro = logging.getLogger('arealatina.seguridad')


def ip_de(request):
    if request is None:
        return None
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR')
    if reenviada:
        return reenviada.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def navegador_de(request):
    if request is None:
        return ''
    return request.META.get('HTTP_USER_AGENT', '')[:250]


def _anotar(accion, usuario, request, descripcion):
    """Escribe en AuditLog sin romper nunca el flujo de autenticación."""
    from .models import AuditLog

    try:
        AuditLog.objects.create(
            usuario=usuario if (usuario and usuario.pk) else None,
            accion=accion,
            modelo='CustomUser',
            objeto_id=getattr(usuario, 'pk', None),
            descripcion=descripcion[:250],
            ip=ip_de(request),
            user_agent=navegador_de(request),
        )
    except Exception:
        registro.exception('No se pudo escribir en la auditoría')


@receiver(user_logged_in)
def al_entrar(sender, request, user, **kwargs):
    _anotar('LOGIN', user, request, f'Inició sesión {user.username}')
    registro.info('Acceso de %s desde %s', user.username, ip_de(request))


@receiver(user_logged_out)
def al_salir(sender, request, user, **kwargs):
    if user is None:
        return
    _anotar('LOGOUT', user, request, f'Cerró sesión {user.username}')


@receiver(user_login_failed)
def al_fallar(sender, credentials, request=None, **kwargs):
    # Nunca se guarda la contraseña intentada, solo el usuario probado.
    intento = (credentials or {}).get('username', '')
    _anotar('LOGIN_FALLIDO', None, request,
            f'Intento fallido para "{intento[:60]}"')
    registro.warning('Intento fallido para "%s" desde %s', intento[:60], ip_de(request))
