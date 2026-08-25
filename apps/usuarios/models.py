"""Modelo de usuario personalizado con roles para Area Latina Estudio."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class TimeStampedModel(models.Model):
    """Base abstracta con marcas de tiempo para todos los modelos."""

    created_at = models.DateTimeField('Creado el', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado el', auto_now=True)

    class Meta:
        abstract = True


class CustomUser(AbstractUser):
    """Usuario del sistema. El rol define a que modulos puede acceder."""

    class Rol(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        PROFESOR = 'PROFESOR', 'Profesor/a'
        ALUMNO = 'ALUMNO', 'Alumno/a'

    rol = models.CharField(
        'Rol',
        max_length=10,
        choices=Rol.choices,
        default=Rol.ALUMNO,
    )
    telefono = models.CharField('Telefono', max_length=20, blank=True)
    rut = models.CharField(
        'RUT',
        max_length=12,
        blank=True,
        null=True,
        unique=True,
        help_text='Formato 12345678-9',
    )

    created_at = models.DateTimeField('Creado el', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado el', auto_now=True)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['first_name', 'last_name', 'username']

    def __str__(self):
        nombre = self.get_full_name().strip() or self.username
        return f'{nombre} ({self.get_rol_display()})'

    @property
    def es_admin(self):
        return self.rol == self.Rol.ADMIN or self.is_superuser

    @property
    def es_profesor(self):
        return self.rol == self.Rol.PROFESOR

    @property
    def nombre_corto(self):
        return self.first_name or self.username
