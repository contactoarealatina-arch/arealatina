from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.LoginSeguro.as_view(), name='login'),
    path('logout/', views.salir, name='logout'),
]
