"""Deja corriendo el planificador de tareas diarias.

Uso:
    python manage.py correr_scheduler

Se queda en primer plano, así que en el hosting va como servicio aparte
(systemd, supervisor o similar). Alternativa más simple: poner
`python manage.py enviar_alertas` en el cron del sistema y no usar esto.
"""
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution

from apps.gestion.correos import enviar_resumen
from apps.gestion.models import ConfiguracionAlertas
from apps.gestion.servicios import generar_alertas

logger = logging.getLogger(__name__)


def tarea_alertas():
    """Trabajo diario: generar alertas y avisar por correo."""
    resumen = generar_alertas()
    logger.info('Alertas generadas: %s', resumen['creadas'])
    enviado, motivo = enviar_resumen(resumen)
    logger.info('Resumen por correo: %s', motivo)


def limpiar_historial():
    """Borra las ejecuciones viejas para que la tabla no crezca sin control."""
    DjangoJobExecution.objects.delete_old_job_executions(604_800)  # 7 días


class Command(BaseCommand):
    help = 'Corre el planificador de tareas diarias (alertas por email).'

    def handle(self, *args, **options):
        config = ConfiguracionAlertas.obtener()
        hora = config.hora_envio

        planificador = BlockingScheduler(timezone='America/Santiago')
        planificador.add_jobstore(DjangoJobStore(), 'default')

        planificador.add_job(
            tarea_alertas,
            trigger=CronTrigger(hour=hora.hour, minute=hora.minute),
            id='alertas_diarias',
            max_instances=1,
            replace_existing=True,
        )
        planificador.add_job(
            limpiar_historial,
            trigger=CronTrigger(day_of_week='mon', hour=3, minute=0),
            id='limpiar_historial',
            max_instances=1,
            replace_existing=True,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Planificador activo. Alertas todos los días a las {hora:%H:%M}.'
        ))
        self.stdout.write('Ctrl+C para detener.')

        try:
            planificador.start()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Deteniendo el planificador...'))
            planificador.shutdown()
