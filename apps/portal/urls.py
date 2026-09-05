from django.urls import path

from . import views

app_name = 'portal'

urlpatterns = [
    path('login/', views.PortalLogin.as_view(), name='login'),
    path('activar/<str:token>/', views.activar, name='activar'),
    path('activar/<str:token>/expirado/', views.token_expirado, name='token_expirado'),

    path('terminos/', views.terminos, name='terminos'),
    path('', views.panel, name='panel'),
    path('renovar/', views.solicitar_renovacion, name='solicitar_renovacion'),
    path('pagos/', views.pagos, name='pagos'),
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/clave/', views.cambiar_clave, name='cambiar_clave'),
]
