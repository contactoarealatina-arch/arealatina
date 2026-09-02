from django.urls import path

from . import views, vistas_privacidad

app_name = 'web'

urlpatterns = [
    path('', views.index, name='index'),
    path('clases/', views.clases, name='clases'),
    path('planes/', views.planes, name='planes'),
    path('wellness/', views.wellness, name='wellness'),
    path('en-escena/', views.en_escena, name='en_escena'),
    path('comunidad/', views.comunidad, name='comunidad'),
    path('nosotros/', views.nosotros, name='nosotros'),
    path('mi-app/', views.mi_app, name='mi_app'),
    path('contacto/', views.contacto, name='contacto'),

    # Proteccion de datos personales (Ley 21.719)
    path('privacidad/', vistas_privacidad.politica_privacidad, name='privacidad'),
    path('mis-derechos/', vistas_privacidad.mis_derechos, name='mis_derechos'),
]
