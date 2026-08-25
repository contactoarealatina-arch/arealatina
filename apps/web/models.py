"""Modelos del sitio publico: mensajes de contacto y equipo de profesoras."""
from django.db import models

from apps.usuarios.models import TimeStampedModel


class MensajeContacto(TimeStampedModel):
    """Mensaje enviado desde el formulario de contacto del sitio."""

    nombre = models.CharField('Nombre', max_length=120)
    email = models.EmailField('Email')
    telefono = models.CharField('Telefono', max_length=20, blank=True)
    mensaje = models.TextField('Mensaje')
    leido = models.BooleanField('Leido', default=False)

    class Meta:
        verbose_name = 'Mensaje de contacto'
        verbose_name_plural = 'Mensajes de contacto'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.nombre} - {self.created_at:%d/%m/%Y %H:%M}'
