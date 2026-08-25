from django.urls import path

from . import views

app_name = 'asistencia'

urlpatterns = [
    path('', views.mis_clases, name='mis_clases'),
]
