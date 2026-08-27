"""Datos que necesita el layout de gestión en todas sus páginas."""
from .models import Alerta


def panel(request):
    """Contador de alertas para el badge del sidebar."""
    if not request.user.is_authenticated or not getattr(request.user, 'puede_gestionar', False):
        return {}
    return {
        'alertas_pendientes': Alerta.objects.filter(gestionada=False).count(),
        'version_sistema': '1.0',
    }
