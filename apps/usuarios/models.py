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
    # Identidad interna del estudio, tipo camila@arealatina.cl. NO es una
    # casilla de correo: es el nombre con el que la profesora entra al
    # sistema. Las casillas reales las da un proveedor de correo, no
    # Django. Por eso los avisos van al correo personal de más abajo.
    correo_institucional = models.EmailField(
        'Correo del estudio',
        blank=True,
        unique=True,
        null=True,
        help_text='Se genera solo al crear la profesora. Es con lo que entra '
                  'al sistema.',
    )
    correo_personal = models.EmailField(
        'Correo personal',
        blank=True,
        help_text='Acá le llegan la clave temporal y los avisos. Tiene que '
                  'ser un correo que la persona revise de verdad.',
    )
    # Se marca al crear la cuenta con clave temporal y se apaga cuando la
    # persona elige la suya. Mientras esté encendida, el sistema no la
    # deja usar nada: una clave que viajó por correo la conoce cualquiera
    # que abra esa bandeja.
    debe_cambiar_clave = models.BooleanField(
        'Debe cambiar la contraseña',
        default=False,
        help_text='Se enciende solo al generarle una clave temporal.',
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
    def correo_de_contacto(self):
        """A dónde mandarle los avisos de verdad.

        El correo institucional es solo identidad de acceso: no existe
        como casilla, así que mandarle ahí la clave temporal sería
        mandarla al vacío. El personal manda; el campo `email` queda como
        último recurso para las cuentas antiguas.
        """
        return self.correo_personal or self.email or ''

    @classmethod
    def generar_correo_institucional(cls, nombre, apellido, dominio=None):
        """nombre.apellido@arealatina.cl, sin tildes ni repetidos.

        Si ya existe, agrega un número: no puede haber dos personas con la
        misma identidad de acceso.
        """
        import unicodedata

        from django.conf import settings

        dominio = dominio or getattr(
            settings, 'DOMINIO_PROFESORAS', 'arealatina.cl',
        )

        def limpiar(texto):
            sin_tildes = unicodedata.normalize('NFKD', texto or '')
            sin_tildes = sin_tildes.encode('ascii', 'ignore').decode()
            return ''.join(c for c in sin_tildes.lower() if c.isalnum())

        base = limpiar(nombre)
        apellido_limpio = limpiar(apellido)
        if apellido_limpio:
            base = f'{base}.{apellido_limpio}'
        base = base or 'profesora'

        candidato = f'{base}@{dominio}'
        contador = 2
        while cls.objects.filter(correo_institucional__iexact=candidato).exists():
            candidato = f'{base}{contador}@{dominio}'
            contador += 1
        return candidato

    @property
    def iniciales(self):
        nombre = self.get_full_name().strip()
        if nombre:
            partes = nombre.split()
            return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else '')).upper()
        return self.username[:2].upper()
