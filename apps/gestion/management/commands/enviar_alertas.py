"""Genera las alertas del día y manda el resumen por correo.

Uso:
    python manage.py enviar_alertas
    python manage.py enviar_alertas --sin-correo   (solo genera, no envía)

Es el mismo trabajo que corre el cron a diario, pero se puede lanzar a mano
para probar o para ponerlo en el cron del hosting.
"""
from django.core.management.base import BaseCommand

from apps.gestion.correos import enviar_recordatorios_del_dia, enviar_resumen
from apps.gestion.servicios import generar_alertas


class Command(BaseCommand):
    help = 'Genera las alertas de vencimientos y pagos, y envía el resumen por email.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sin-correo',
            action='store_true',
            help='Genera las alertas pero no manda el email.',
        )

    def handle(self, *args, **opciones):
        resumen = generar_alertas()

        self.stdout.write(self.style.SUCCESS(
            f'Alertas nuevas: {resumen["creadas"]}'
        ))
        self.stdout.write(f'  Por vencer:      {len(resumen["por_vencer"])}')
        self.stdout.write(f'  Planes vencidos: {len(resumen["vencidos"])}')
        self.stdout.write(f'  Sin pago del mes: {len(resumen["sin_pago"])}')

        if opciones['sin_correo']:
            self.stdout.write(self.style.WARNING('Correo omitido (--sin-correo).'))
            return

        # 1. Aviso a cada alumno con plan por vencer o vencido.
        enviados, omitidos = enviar_recordatorios_del_dia(resumen)
        self.stdout.write(self.style.SUCCESS(
            f'Recordatorios a alumnos: {enviados} enviados, {omitidos} omitidos'
        ))

        # 2. Resumen para el equipo.
        enviado, motivo = enviar_resumen(resumen)
        if enviado:
            self.stdout.write(self.style.SUCCESS(motivo))
        else:
            self.stdout.write(self.style.WARNING(f'Sin resumen: {motivo}'))
