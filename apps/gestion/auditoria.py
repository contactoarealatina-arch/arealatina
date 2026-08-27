"""Registro de acciones importantes del sistema."""
from .models import AuditLog


def ip_del_request(request):
    """Toma la IP real cuando hay proxy delante (hosting con balanceador)."""
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR')
    if reenviada:
        return reenviada.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def registrar(request, accion, objeto=None, descripcion='', modelo=''):
    """Deja constancia de una acción.

    Nunca debe romper la operación que la origina: si el log falla, la
    acción del usuario igual se completó.
    """
    try:
        AuditLog.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            accion=accion,
            modelo=modelo or (objeto.__class__.__name__ if objeto else ''),
            objeto_id=getattr(objeto, 'pk', None),
            descripcion=descripcion[:250],
            ip=ip_del_request(request),
        )
    except Exception:
        pass
