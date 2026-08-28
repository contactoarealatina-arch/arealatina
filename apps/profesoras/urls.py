from django.urls import path

from . import views

app_name = 'profesoras'

urlpatterns = [
    path('', views.panel, name='panel'),
    path('clases/', views.clases, name='clases'),
    path('historial/', views.historial, name='historial'),
    path('historial/exportar/', views.historial_exportar, name='historial_exportar'),
    path('asistencia/<int:clase_id>/<str:fecha>/', views.asistencia, name='asistencia'),
]
