from django.urls import path

from . import views, vistas_privacidad

app_name = 'web'

# Tres páginas y nada más. Mi espacio queda fuera del menú a propósito:
# solo la usa quien ya es parte del estudio, y llega por el pie o por el
# botón "Entrar".
urlpatterns = [
    path('', views.index, name='index'),
    path('clases/', views.clases, name='clases'),
    path('contacto/', views.contacto, name='contacto'),
    path('mi-espacio/', views.mi_espacio, name='mi_espacio'),

    # Proteccion de datos personales (Ley 21.719)
    path('privacidad/', vistas_privacidad.politica_privacidad, name='privacidad'),
    path('mis-derechos/', vistas_privacidad.mis_derechos, name='mis_derechos'),
]
