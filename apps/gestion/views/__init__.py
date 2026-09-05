"""Vistas del módulo de gestión, agrupadas por área."""
from .alertas import (  # noqa: F401
    alerta_gestionar,
    alertas,
    alertas_configuracion,
    alertas_regenerar,
)
from .alumnos import (  # noqa: F401
    alumno_detalle,
    alumno_editar,
    alumno_eliminar,
    alumno_estado,
    alumno_nota,
    alumno_nuevo,
    alumno_reenviar_acceso,
    alumno_renovar,
    alumnos,
    alumnos_exportar,
)
from .asistencia import asistencia  # noqa: F401
from .auditoria import auditoria  # noqa: F401
from .clases import clase_detalle, clase_editar, clase_nueva, clases  # noqa: F401
from .dashboard import dashboard  # noqa: F401
from .pagos import pago_nuevo, pagos, pagos_exportar, resumen_financiero  # noqa: F401
from .planes import plan_alternar, plan_editar, plan_nuevo, planes  # noqa: F401
from .profesoras import (  # noqa: F401
    profesora_detalle,
    profesora_editar,
    profesora_reenviar_acceso,
    profesora_nueva,
    profesoras,
)
from .reportes import reporte_descargar, reportes  # noqa: F401
