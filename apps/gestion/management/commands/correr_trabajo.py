"""Corre un trabajo automático a mano.

Uso:
    python manage.py correr_trabajo                    lista los disponibles
    python manage.py correr_trabajo alertas_manana     corre ese
    python manage.py correr_trabajo --todos            corre todos, en orden

Pensado para dos cosas: probar un trabajo sin esperar su horario, y para
ponerlo en el cron del hosting sin necesitar un proceso permanente:

    0  8 * * *  cd /ruta && venv/bin/python manage.py correr_trabajo recordatorio_profesoras
    0  9 * * *  cd /ruta && venv/bin/python manage.py correr_trabajo alertas_manana
    0 18 * * *  cd /ruta && venv/bin/python manage.py correr_trabajo recordatorio_clases
    1  0 * * *  cd /ruta && venv/bin/python manage.py correr_trabajo planes_vencidos
    0  8 1 * *  cd /ruta && venv/bin/python manage.py correr_trabajo informe_mensual
"""
from django.core.management.base import BaseCommand, CommandError

from apps.gestion.jobs import TRABAJOS

POR_ID = {identificador: funcion for identificador, funcion, *_ in TRABAJOS}


class Command(BaseCommand):
    help = 'Corre uno de los trabajos automáticos a mano.'

    def add_arguments(self, parser):
        parser.add_argument('trabajo', nargs='?', help='Identificador del trabajo.')
        parser.add_argument('--todos', action='store_true', help='Corre todos en orden.')

    def handle(self, *args, **opciones):
        if opciones['todos']:
            for identificador, funcion, *_ in TRABAJOS:
                self.stdout.write(self.style.HTTP_INFO(f'>> {identificador}'))
                self.stdout.write(f'  {funcion()}')
            return

        elegido = opciones.get('trabajo')

        if not elegido:
            self.stdout.write('Trabajos disponibles:')
            for identificador, _, hora, minuto, dia in TRABAJOS:
                cuando = f'{hora:02d}:{minuto:02d}'
                if dia:
                    cuando = f'día {dia} a las {cuando}'
                self.stdout.write(f'  {identificador:26} {cuando}')
            return

        if elegido not in POR_ID:
            raise CommandError(
                f'No existe el trabajo "{elegido}". '
                f'Disponibles: {", ".join(POR_ID)}'
            )

        self.stdout.write(self.style.HTTP_INFO(f'Corriendo {elegido}...'))
        resultado = POR_ID[elegido]()
        self.stdout.write(self.style.SUCCESS(f'Resultado: {resultado}'))
