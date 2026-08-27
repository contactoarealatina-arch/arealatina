"""Modelo de usuario personalizado con roles para Área Latina Estudio."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class TimeStampedModel(models.Model):
    """Base abstracta con marcas de tiempo para todos los modelos."""

    created_at = models.DateTimeField('Creado el', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado el', auto_now=True)

    class Meta:
        abstract = True


class CustomUser(AbstractUser):
    """Usuario del sistema. El rol define a qué módulos puede acceder.

    SUPERADMIN -> todo, incluida la auditoría
    ADMIN      -> gestión completa salvo auditoría
    PROFESOR   -> solo su módulo de asistencia
    ALUMNO     -> reservado para el portal de alumnos (etapa posterior)
    """

    class Rol(models.TextChoices):
        SUPERADMIN = 'SUPERADMIN', 'Super administrador'
        ADMIN = 'ADMIN', 'Administrador'
        PROFESOR = 'PROFESOR', 'Profesor/a'
        ALUMNO = 'ALUMNO', 'Alumno/a'

    rol = models.CharField(
        'Rol',
        max_length=12,
        choices=Rol.choices,
        default=Rol.ALUMNO,
    )
    telefono = models.CharField('Teléfono', max_length=20, blank=True)
    rut = models.CharField(
        'RUT',
        max_length=12,
        blank=True,
        null=True,
        unique=True,
        help_text='Formato 12345678-9',
    )
    especialidad = models.CharField(
        'Especialidad',
        max_length=120,
        blank=True,
        help_text='Solo para profesores. Ej: Salsa y Bachata',
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

    # ------------------------------------------------------------------
    # Permisos por rol
    # ------------------------------------------------------------------
    @property
    def es_superadmin(self):
        return self.rol == self.Rol.SUPERADMIN or self.is_superuser

    @property
    def es_admin(self):
        """Incluye al superadmin: todo lo que puede un admin, lo puede él."""
        return self.rol in (self.Rol.ADMIN, self.Rol.SUPERADMIN) or self.is_superuser

    @property
    def es_profesor(self):
        return self.rol == self.Rol.PROFESOR

    @property
    def puede_gestionar(self):
        """Acceso al módulo de gestión completo."""
        return self.es_admin

    @property
    def nombre_corto(self):
        return self.first_name or self.username

    @property
    def iniciales(self):
        nombre = self.get_full_name().strip()
        if nombre:
            partes = nombre.split()
            return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else '')).upper()
        return self.username[:2].upper()
