"""Datos que necesita el layout de gestión en todas sus páginas."""
from .models import Alerta, AlertaNegocio, AlertaSistema


def panel(request):
    """Contadores de los badges del sidebar."""
    if (not request.user.is_authenticated
            or not getattr(request.user, 'puede_gestionar', False)):
        return {}

    datos = {
        'alertas_pendientes': Alerta.objects.filter(gestionada=False).count(),
        'negocio_sin_leer': AlertaNegocio.objects.filter(leida=False).count(),
        'version_sistema': '1.0',
    }

    # El estado del sistema solo lo ve el superadmin: contarlo para el
    # resto sería mostrar un badge de una pantalla a la que no puede
    # entrar.
    if getattr(request.user, 'es_superadmin', False):
        datos['sistema_sin_leer'] = AlertaSistema.objects.filter(
            leida=False).count()

    return datos
