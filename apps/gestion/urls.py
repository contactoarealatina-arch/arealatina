from django.urls import path

from . import views

app_name = 'gestion'

urlpatterns = [
    # Módulo 1 — Dashboard
    path('', views.dashboard, name='dashboard'),

    # Módulo 2 — Alumnos
    path('alumnos/', views.alumnos, name='alumnos'),
    path('alumnos/nuevo/', views.alumno_nuevo, name='alumno_nuevo'),
    path('alumnos/exportar/', views.alumnos_exportar, name='alumnos_exportar'),
    path('alumnos/<int:pk>/', views.alumno_detalle, name='alumno_detalle'),
    path('alumnos/<int:pk>/editar/', views.alumno_editar, name='alumno_editar'),
    path('alumnos/<int:pk>/estado/', views.alumno_estado, name='alumno_estado'),
    path('alumnos/<int:pk>/eliminar/', views.alumno_eliminar, name='alumno_eliminar'),
    path('alumnos/<int:pk>/renovar/', views.alumno_renovar, name='alumno_renovar'),
    path('alumnos/<int:pk>/nota/', views.alumno_nota, name='alumno_nota'),
    path('alumnos/<int:pk>/reenviar-acceso/', views.alumno_reenviar_acceso,
         name='alumno_reenviar_acceso'),

    # Módulo 3 — Clases
    path('clases/', views.clases, name='clases'),
    path('clases/nueva/', views.clase_nueva, name='clase_nueva'),
    path('clases/<int:pk>/', views.clase_detalle, name='clase_detalle'),
    path('clases/<int:pk>/editar/', views.clase_editar, name='clase_editar'),
    path('clases/<int:pk>/alternar/', views.clase_alternar, name='clase_alternar'),
    path('clases/<int:pk>/eliminar/', views.clase_eliminar, name='clase_eliminar'),

    # Módulo 4 — Planes
    path('planes/', views.planes, name='planes'),
    path('planes/nuevo/', views.plan_nuevo, name='plan_nuevo'),
    path('planes/<int:pk>/editar/', views.plan_editar, name='plan_editar'),
    path('planes/<int:pk>/alternar/', views.plan_alternar, name='plan_alternar'),
    path('planes/<int:pk>/eliminar/', views.plan_eliminar, name='plan_eliminar'),

    # Módulo 5 — Pagos
    path('pagos/', views.pagos, name='pagos'),
    path('pagos/nuevo/', views.pago_nuevo, name='pago_nuevo'),
    path('pagos/resumen/', views.resumen_financiero, name='resumen_financiero'),
    path('pagos/exportar/', views.pagos_exportar, name='pagos_exportar'),

    # Módulo 6 — Alertas
    path('alertas/', views.alertas, name='alertas'),
    path('alertas/regenerar/', views.alertas_regenerar, name='alertas_regenerar'),
    path('alertas/configuracion/', views.alertas_configuracion, name='alertas_configuracion'),
    path('alertas/<int:pk>/gestionar/', views.alerta_gestionar, name='alerta_gestionar'),

    # Módulo 7 — Reportes
    path('asistencia/resumen/', views.asistencia_resumen,
         name='asistencia_resumen'),
    path('asistencia/<int:clase_id>/<str:fecha>/', views.asistencia_sesion,
         name='asistencia_sesion'),
    path('reportes/por-curso/', views.por_curso, name='por_curso'),
    path('reportes/por-curso/exportar/', views.por_curso_exportar,
         name='por_curso_exportar'),
    path('reportes/', views.reportes, name='reportes'),
    path('reportes/<slug:slug>/', views.reporte_descargar, name='reporte_descargar'),

    # Módulo 8 — Asistencia
    path('asistencia/', views.asistencia, name='asistencia'),

    # Módulo 9 — Profesoras
    path('profesoras/', views.profesoras, name='profesoras'),
    path('profesoras/nueva/', views.profesora_nueva, name='profesora_nueva'),
    path('profesoras/<int:pk>/', views.profesora_detalle, name='profesora_detalle'),
    path('profesoras/<int:pk>/editar/', views.profesora_editar, name='profesora_editar'),
    path('profesoras/<int:pk>/reenviar-acceso/', views.profesora_reenviar_acceso,
         name='profesora_reenviar_acceso'),
    path('profesoras/<int:pk>/alternar/', views.profesora_alternar,
         name='profesora_alternar'),
    path('profesoras/<int:pk>/eliminar/', views.profesora_eliminar,
         name='profesora_eliminar'),

    # Módulo 10 — Auditoría
    path('auditoria/', views.auditoria, name='auditoria'),
]
