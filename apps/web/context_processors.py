"""Expone los datos de contacto de la academia a todos los templates."""
from django.conf import settings


def academia(request):
    return {'academia': settings.ACADEMIA}
