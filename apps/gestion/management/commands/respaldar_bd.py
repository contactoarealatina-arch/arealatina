"""Respaldo de la base de datos.

Uso:
    python manage.py respaldar_bd
    python manage.py respaldar_bd --sin-subir   (solo local, no sube a R2)

Corre pg_dump, comprime, y si hay credenciales de R2 configuradas lo sube
y borra los respaldos de más de 30 días. Cada corrida deja constancia en
RespaldoLog: si algún día falta un respaldo, se sabe qué pasó y cuándo.

Una base sin respaldos probados no está respaldada. Después de configurar
esto, restaura una vez en una base de prueba para comprobar que sirve.
"""
import gzip
import os
import shutil
import subprocess
import tempfile
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.gestion.models import RespaldoLog

DIAS_RETENCION = 30


class Command(BaseCommand):
    help = 'Respalda la base de datos y la sube a Cloudflare R2.'

    def add_arguments(self, parser):
        parser.add_argument('--sin-subir', action='store_true',
                            help='Genera el archivo pero no lo sube.')
        parser.add_argument('--carpeta', default='',
                            help='Dónde dejar el archivo local.')

    def handle(self, *args, **opciones):
        bd = settings.DATABASES['default']
        marca = timezone.localtime().strftime('%Y%m%d-%H%M')
        nombre = f'arealatina-{marca}.sql.gz'

        carpeta = opciones['carpeta'] or tempfile.gettempdir()
        destino = os.path.join(carpeta, nombre)

        self.stdout.write(f'Respaldando {bd["NAME"]}...')

        try:
            self._volcar(bd, destino)
        except Exception as error:
            RespaldoLog.objects.create(
                archivo=nombre, estado=RespaldoLog.Estado.ERROR,
                detalle=str(error)[:2000])
            self.stdout.write(self.style.ERROR(f'Falló el volcado: {error}'))
            return

        tamano = os.path.getsize(destino)
        self.stdout.write(self.style.SUCCESS(
            f'  Archivo: {destino} ({tamano / 1024:.0f} KB)'))

        ruta_remota = ''
        if not opciones['sin_subir'] and getattr(settings, 'USAR_R2', False):
            try:
                ruta_remota = self._subir(destino, nombre)
                self.stdout.write(self.style.SUCCESS(f'  Subido a: {ruta_remota}'))
                borrados = self._limpiar_viejos()
                if borrados:
                    self.stdout.write(f'  Respaldos antiguos eliminados: {borrados}')
            except Exception as error:
                RespaldoLog.objects.create(
                    archivo=nombre, tamano_bytes=tamano,
                    estado=RespaldoLog.Estado.ERROR,
                    detalle=f'Volcado correcto, falló la subida: {error}'[:2000])
                self.stdout.write(self.style.ERROR(f'  No se pudo subir: {error}'))
                return
        elif not opciones['sin_subir']:
            self.stdout.write(self.style.WARNING(
                '  R2 sin configurar: el respaldo quedó solo en disco local.'))

        registro = RespaldoLog.objects.create(
            archivo=nombre, destino=ruta_remota, tamano_bytes=tamano,
            estado=RespaldoLog.Estado.OK)

        self._avisar(registro)
        self.stdout.write(self.style.SUCCESS('Respaldo completo.'))

    # ------------------------------------------------------------------
    def _volcar(self, bd, destino):
        """pg_dump a un archivo comprimido."""
        entorno = os.environ.copy()
        entorno['PGPASSWORD'] = bd['PASSWORD']

        comando = [
            self._ruta_pg_dump(),
            '--host', bd.get('HOST') or 'localhost',
            '--port', str(bd.get('PORT') or 5432),
            '--username', bd['USER'],
            '--no-password',
            '--clean', '--if-exists',
            bd['NAME'],
        ]

        with tempfile.NamedTemporaryFile(delete=False, suffix='.sql') as plano:
            ruta_plano = plano.name

        try:
            with open(ruta_plano, 'wb') as salida:
                proceso = subprocess.run(
                    comando, stdout=salida, stderr=subprocess.PIPE,
                    env=entorno, timeout=600)
            if proceso.returncode != 0:
                raise RuntimeError(proceso.stderr.decode('utf-8', 'replace')[:500])

            with open(ruta_plano, 'rb') as origen, gzip.open(destino, 'wb') as comprimido:
                shutil.copyfileobj(origen, comprimido)
        finally:
            if os.path.exists(ruta_plano):
                os.unlink(ruta_plano)

    def _ruta_pg_dump(self):
        """pg_dump no siempre está en el PATH, sobre todo en Windows."""
        encontrado = shutil.which('pg_dump')
        if encontrado:
            return encontrado

        candidatos = [
            r'C:\Program Files\PostgreSQL\18\bin\pg_dump.exe',
            r'C:\Program Files\PostgreSQL\17\bin\pg_dump.exe',
            r'C:\Program Files\PostgreSQL\16\bin\pg_dump.exe',
            '/usr/bin/pg_dump',
            '/usr/local/bin/pg_dump',
        ]
        for ruta in candidatos:
            if os.path.exists(ruta):
                return ruta
        raise RuntimeError('No se encontró pg_dump. Instálalo o agrégalo al PATH.')

    def _subir(self, ruta_local, nombre):
        import boto3

        cliente = boto3.client(
            's3',
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name='auto',
        )
        clave = f'respaldos/{nombre}'
        cliente.upload_file(ruta_local, settings.AWS_STORAGE_BUCKET_NAME, clave)
        return f'{settings.AWS_STORAGE_BUCKET_NAME}/{clave}'

    def _limpiar_viejos(self):
        """Borra de R2 los respaldos que pasaron la ventana de retención."""
        import boto3

        cliente = boto3.client(
            's3',
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name='auto',
        )
        limite = timezone.now() - timedelta(days=DIAS_RETENCION)
        respuesta = cliente.list_objects_v2(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME, Prefix='respaldos/')

        borrados = 0
        for objeto in respuesta.get('Contents', []):
            if objeto['LastModified'] < limite:
                cliente.delete_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=objeto['Key'])
                borrados += 1
        return borrados

    def _avisar(self, registro):
        from django.test.utils import override_settings

        from apps.gestion import correos
        from apps.gestion.models import ConfiguracionAlertas, CorreoEnviado

        config = ConfiguracionAlertas.obtener()
        if not config.envio_activo or not settings.EMAIL_HOST_PASSWORD:
            return

        backend = 'django.core.mail.backends.smtp.EmailBackend'
        with override_settings(EMAIL_BACKEND=backend):
            correos._enviar(
                tipo=CorreoEnviado.Tipo.RESUMEN,
                destinatarios=config.lista_emails,
                asunto=f'Respaldo correcto · {registro.archivo}',
                plantilla='respaldo',
                contexto={'respaldo': registro},
                referencia=f'RESPALDO-{registro.pk}',
            )
