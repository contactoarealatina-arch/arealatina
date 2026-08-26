"""Modelos de gestion academica: clases, planes, alumnos, suscripciones y pagos."""
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.usuarios.models import TimeStampedModel


class Clase(TimeStampedModel):
    """Una clase regular del estudio, con su horario y profesora a cargo."""

    class Estilo(models.TextChoices):
        SALSA = 'SALSA', 'Salsa'
        BACHATA = 'BACHATA', 'Bachata'
        REGGAETON = 'REGGAETON', 'Reggaetón'
        URBANO = 'URBANO', 'Urbano'
        TANGO = 'TANGO', 'Tango'
        KIDS = 'KIDS', 'Kids Dance'

    class Nivel(models.TextChoices):
        INICIAL = 'INICIAL', 'Inicial'
        INTERMEDIO = 'INTERMEDIO', 'Intermedio'
        AVANZADO = 'AVANZADO', 'Avanzado'
        TODOS = 'TODOS', 'Todos los niveles'

    nombre = models.CharField('Estilo', max_length=15, choices=Estilo.choices)
    descripcion = models.TextField('Descripcion', blank=True)
    nivel = models.CharField(
        'Nivel',
        max_length=12,
        choices=Nivel.choices,
        default=Nivel.TODOS,
    )
    dias_semana = models.CharField(
        'Dias de la semana',
        max_length=120,
        help_text='Ej: Lunes y Miercoles',
    )
    hora_inicio = models.TimeField('Hora de inicio')
    hora_fin = models.TimeField('Hora de termino')
    sala = models.CharField('Sala', max_length=50, default='Sala 1')
    cupo_maximo = models.PositiveSmallIntegerField('Cupo maximo', default=20)
    activa = models.BooleanField('Activa', default=True)

    profesora = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clases_dictadas',
        verbose_name='Profesor/a',
        limit_choices_to={'rol': 'PROFESOR'},
    )

    class Meta:
        verbose_name = 'Clase'
        verbose_name_plural = 'Clases'
        ordering = ['nombre', 'hora_inicio']

    def __str__(self):
        return f'{self.get_nombre_display()} - {self.get_nivel_display()} ({self.dias_semana})'

    @property
    def horario(self):
        return f'{self.dias_semana} | {self.hora_inicio:%H:%M} - {self.hora_fin:%H:%M}'

    @property
    def cupos_disponibles(self):
        return max(self.cupo_maximo - self.inscripciones.count(), 0)

    @property
    def emoji(self):
        return {
            self.Estilo.SALSA: '\U0001F483',
            self.Estilo.BACHATA: '\U0001F339',
            self.Estilo.REGGAETON: '\U0001F525',
            self.Estilo.URBANO: '\U0001F3A4',
            self.Estilo.TANGO: '\U0001F3B6',
            self.Estilo.KIDS: '\U0001F476',
        }.get(self.nombre, '\U0001F3B5')


class Plan(TimeStampedModel):
    """Plan o mensualidad que puede contratar un alumno."""

    nombre = models.CharField('Nombre', max_length=80, unique=True)
    precio_clp = models.PositiveIntegerField('Precio (CLP)')
    duracion_dias = models.PositiveSmallIntegerField('Duracion (dias)', default=30)
    descripcion = models.TextField('Descripcion', blank=True)
    activo = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Plan'
        verbose_name_plural = 'Planes'
        ordering = ['precio_clp']

    def __str__(self):
        return f'{self.nombre} - ${self.precio_clp:,.0f} CLP'.replace(',', '.')


class Alumno(TimeStampedModel):
    """Ficha del alumno del estudio."""

    class Estado(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        INACTIVO = 'INACTIVO', 'Inactivo'
        SUSPENDIDO = 'SUSPENDIDO', 'Suspendido'

    class Genero(models.TextChoices):
        FEMENINO = 'F', 'Femenino'
        MASCULINO = 'M', 'Masculino'
        OTRO = 'O', 'Otro'
        NO_INFORMA = 'N', 'Prefiere no informar'

    nombre_completo = models.CharField('Nombre completo', max_length=150)
    rut = models.CharField('RUT', max_length=12, unique=True, help_text='Formato 12345678-9')
    fecha_nacimiento = models.DateField('Fecha de nacimiento', null=True, blank=True)
    genero = models.CharField(
        'Genero',
        max_length=1,
        choices=Genero.choices,
        default=Genero.NO_INFORMA,
    )

    telefono = models.CharField('Telefono', max_length=20, blank=True)
    email = models.EmailField('Email', blank=True)
    direccion = models.CharField('Direccion', max_length=200, blank=True)

    contacto_emergencia = models.CharField('Contacto de emergencia', max_length=150, blank=True)
    telefono_emergencia = models.CharField('Telefono de emergencia', max_length=20, blank=True)

    fecha_ingreso = models.DateField('Fecha de ingreso', default=timezone.localdate)
    foto = models.ImageField('Foto', upload_to='alumnos/', null=True, blank=True)
    estado = models.CharField(
        'Estado',
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVO,
    )
    observaciones = models.TextField('Observaciones', blank=True)

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ficha_alumno',
        verbose_name='Usuario asociado',
    )

    class Meta:
        verbose_name = 'Alumno'
        verbose_name_plural = 'Alumnos'
        ordering = ['nombre_completo']

    def __str__(self):
        return f'{self.nombre_completo} ({self.rut})'

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = timezone.localdate()
        return hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )

    @property
    def suscripcion_vigente(self):
        return self.suscripciones.filter(
            activa=True,
            fecha_vencimiento__gte=timezone.localdate(),
        ).order_by('-fecha_vencimiento').first()

    @property
    def al_dia(self):
        return self.suscripcion_vigente is not None


class Inscripcion(TimeStampedModel):
    """Relaciona a un alumno con una clase a la que asiste."""

    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name='inscripciones',
        verbose_name='Alumno',
    )
    clase = models.ForeignKey(
        Clase,
        on_delete=models.CASCADE,
        related_name='inscripciones',
        verbose_name='Clase',
    )
    fecha_inscripcion = models.DateField('Fecha de inscripcion', default=timezone.localdate)

    class Meta:
        verbose_name = 'Inscripcion'
        verbose_name_plural = 'Inscripciones'
        ordering = ['-fecha_inscripcion']
        constraints = [
            models.UniqueConstraint(
                fields=['alumno', 'clase'],
                name='inscripcion_unica_alumno_clase',
            )
        ]

    def __str__(self):
        return f'{self.alumno.nombre_completo} en {self.clase}'


class Suscripcion(TimeStampedModel):
    """Plan contratado por un alumno durante un periodo determinado."""

    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name='suscripciones',
        verbose_name='Alumno',
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name='suscripciones',
        verbose_name='Plan',
    )
    fecha_inicio = models.DateField('Fecha de inicio', default=timezone.localdate)
    fecha_vencimiento = models.DateField(
        'Fecha de vencimiento',
        blank=True,
        help_text='Se calcula automaticamente segun la duracion del plan.',
    )
    activa = models.BooleanField('Activa', default=True)

    class Meta:
        verbose_name = 'Suscripcion'
        verbose_name_plural = 'Suscripciones'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f'{self.alumno.nombre_completo} - {self.plan.nombre} (vence {self.fecha_vencimiento})'

    def save(self, *args, **kwargs):
        if not self.fecha_vencimiento and self.fecha_inicio and self.plan_id:
            self.fecha_vencimiento = self.fecha_inicio + timedelta(days=self.plan.duracion_dias)
        super().save(*args, **kwargs)

    @property
    def vigente(self):
        return self.activa and self.fecha_vencimiento >= timezone.localdate()

    @property
    def dias_restantes(self):
        return (self.fecha_vencimiento - timezone.localdate()).days


class Pago(TimeStampedModel):
    """Pago realizado por un alumno (mensualidad, matricula, clase suelta, etc.)."""

    class Metodo(models.TextChoices):
        EFECTIVO = 'EFECTIVO', 'Efectivo'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia'

    class Estado(models.TextChoices):
        PAGADO = 'PAGADO', 'Pagado'
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ATRASADO = 'ATRASADO', 'Atrasado'

    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name='pagos',
        verbose_name='Alumno',
    )
    suscripcion = models.ForeignKey(
        Suscripcion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagos',
        verbose_name='Suscripcion',
    )
    concepto = models.CharField('Concepto', max_length=150)
    monto_clp = models.PositiveIntegerField('Monto (CLP)')
    metodo = models.CharField(
        'Metodo de pago',
        max_length=15,
        choices=Metodo.choices,
        default=Metodo.EFECTIVO,
    )
    pago_matricula = models.BooleanField('Es pago de matricula', default=False)
    fecha_pago = models.DateField('Fecha de pago', default=timezone.localdate)
    estado = models.CharField(
        'Estado',
        max_length=10,
        choices=Estado.choices,
        default=Estado.PAGADO,
    )

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha_pago', '-created_at']

    def __str__(self):
        monto = f'{self.monto_clp:,.0f}'.replace(',', '.')
        return f'{self.alumno.nombre_completo} - ${monto} ({self.get_estado_display()})'
