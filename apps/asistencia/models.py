"""Registro de asistencia por clase y fecha."""
from django.db import models
from django.utils import timezone

from apps.gestion.models import Alumno, Clase
from apps.usuarios.models import TimeStampedModel


class RegistroAsistencia(TimeStampedModel):
    """Marca la asistencia de un alumno a una clase en una fecha puntual."""

    class Estado(models.TextChoices):
        PRESENTE = 'PRESENTE', 'Presente'
        AUSENTE = 'AUSENTE', 'Ausente'
        JUSTIFICADO = 'JUSTIFICADO', 'Justificado'

    clase = models.ForeignKey(
        Clase,
        on_delete=models.CASCADE,
        related_name='asistencias',
        verbose_name='Clase',
    )
    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name='asistencias',
        verbose_name='Alumno',
    )
    fecha = models.DateField('Fecha', default=timezone.localdate)
    estado = models.CharField(
        'Estado',
        max_length=12,
        choices=Estado.choices,
        default=Estado.PRESENTE,
    )
    observacion = models.CharField('Observacion', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Registro de asistencia'
        verbose_name_plural = 'Registros de asistencia'
        ordering = ['-fecha', 'alumno__nombre_completo']
        constraints = [
            models.UniqueConstraint(
                fields=['clase', 'alumno', 'fecha'],
                name='asistencia_unica_por_clase_alumno_fecha',
            )
        ]

    def __str__(self):
        return f'{self.fecha:%d/%m/%Y} - {self.alumno.nombre_completo}: {self.get_estado_display()}'
