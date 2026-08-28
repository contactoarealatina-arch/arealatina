"""Deja corriendo el planificador de tareas automáticas.

Uso:
    python manage.py correr_scheduler

Se queda en primer plano, así que en el hosting va como servicio aparte
(systemd, supervisor o similar).

Alternativa más simple para hosting compartido: poner en el cron del
sistema una línea por horario llamando a `manage.py correr_trabajo <id>`.
Eso no necesita ningún proceso permanente.
"""
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution

from apps.gestion.jobs import TRABAJOS

logger = logging.getLogger(__name__)


def limpiar_historial():
    """Borra ejecuciones viejas para que la tabla no crezca sin control."""
    DjangoJobExecution.objects.delete_old_job_executions(604_800)  # 7 días


class Command(BaseCommand):
    help = 'Corre el planificador de tareas automáticas.'

    def handle(self, *args, **options):
        planificador = BlockingScheduler(timezone='America/Santiago')
        planificador.add_jobstore(DjangoJobStore(), 'default')

        self.stdout.write(self.style.SUCCESS('Trabajos programados:'))

        for identificador, funcion, hora, minuto, dia_mes in TRABAJOS:
            disparador = CronTrigger(
                hour=hora, minute=minuto,
                **({'day': dia_mes} if dia_mes else {}),
            )
            planificador.add_job(
                funcion,
                trigger=disparador,
                id=identificador,
                max_instances=1,
                replace_existing=True,
            )
            cuando = f'{hora:02d}:{minuto:02d}'
            if dia_mes:
                cuando = f'día {dia_mes} a las {cuando}'
            self.stdout.write(f'  {identificador:26} {cuando}')

        planificador.add_job(
            limpiar_historial,
            trigger=CronTrigger(day_of_week='mon', hour=3, minute=0),
            id='limpiar_historial',
            max_instances=1,
            replace_existing=True,
        )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Planificador activo. Ctrl+C para detener.'))

        try:
            planificador.start()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Deteniendo el planificador...'))
            planificador.shutdown()
