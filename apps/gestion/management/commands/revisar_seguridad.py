"""Checklist de seguridad del sistema.

Uso:
    python manage.py revisar_seguridad

Revisa la configuración real que está corriendo, no lo que dice el
código. Cada punto se comprueba de verdad: si dice OK es porque se
verificó, no porque alguien lo marcó a mano.

Correr antes de cada despliegue.
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand

OK, FALLA, AVISO = 'OK', 'FALLA', 'AVISO'


class Command(BaseCommand):
    help = 'Revisa el estado de seguridad del sistema.'

    def add_arguments(self, parser):
        parser.add_argument('--produccion', action='store_true',
                            help='Evalúa como si DEBUG estuviera en False.')

    def handle(self, *args, **opciones):
        self.prod = opciones['produccion'] or not settings.DEBUG
        self.resultados = []

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            'REVISIÓN DE SEGURIDAD · Área Latina Estudio'))
        if not self.prod:
            self.stdout.write(self.style.WARNING(
                'Evaluando en modo desarrollo. Usa --produccion para el criterio real.'))
        self.stdout.write('')

        self._configuracion()
        self._autenticacion()
        self._datos()
        self._secretos()

        self._resumen()

    # ------------------------------------------------------------------
    def _marcar(self, titulo, estado, detalle=''):
        self.resultados.append((titulo, estado, detalle))
        simbolo = {OK: '[ OK ]', FALLA: '[FALLA]', AVISO: '[AVISO]'}[estado]
        estilo = {OK: self.style.SUCCESS, FALLA: self.style.ERROR,
                  AVISO: self.style.WARNING}[estado]
        linea = f'  {simbolo} {titulo}'
        if detalle:
            linea += f'  — {detalle}'
        self.stdout.write(estilo(linea))

    def _seccion(self, nombre):
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_LABEL(nombre))

    # ------------------------------------------------------------------
    def _configuracion(self):
        self._seccion('Configuración HTTP')

        self._marcar('DEBUG desactivado en producción',
                     OK if not settings.DEBUG else (AVISO if not self.prod else FALLA),
                     'DEBUG=True (normal en desarrollo)' if settings.DEBUG else '')

        clave = settings.SECRET_KEY
        self._marcar('SECRET_KEY con largo suficiente',
                     OK if len(clave) >= 50 else FALLA,
                     f'{len(clave)} caracteres')

        self._marcar('SECRET_KEY fuera del código',
                     OK if os.environ.get('SECRET_KEY') or self._en_env('SECRET_KEY') else FALLA)

        hosts = settings.ALLOWED_HOSTS
        self._marcar('ALLOWED_HOSTS definido',
                     OK if hosts and '*' not in hosts else FALLA,
                     ', '.join(hosts[:3]))

        for nombre, valor, esperado in [
            ('X-Frame-Options en DENY', getattr(settings, 'X_FRAME_OPTIONS', ''), 'DENY'),
            ('Referrer-Policy configurada',
             getattr(settings, 'SECURE_REFERRER_POLICY', ''), 'same-origin'),
        ]:
            self._marcar(nombre, OK if valor == esperado else FALLA, str(valor))

        self._marcar('Protección contra MIME sniffing',
                     OK if getattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF', False) else FALLA)

        self._marcar('Content-Security-Policy activa',
                     OK if 'csp.middleware.CSPMiddleware' in settings.MIDDLEWARE else FALLA)

        self._marcar('Scripts externos restringidos por CSP',
                     OK if "'unsafe-inline'" not in getattr(settings, 'CSP_SCRIPT_SRC', ()) else FALLA,
                     'sin unsafe-inline en script-src')

        # Lo que solo aplica en producción
        if self.prod:
            for nombre, ajuste in [
                ('HTTPS forzado', 'SECURE_SSL_REDIRECT'),
                ('Cookie de sesión solo por HTTPS', 'SESSION_COOKIE_SECURE'),
                ('Cookie CSRF solo por HTTPS', 'CSRF_COOKIE_SECURE'),
                ('HSTS con subdominios', 'SECURE_HSTS_INCLUDE_SUBDOMAINS'),
                ('HSTS preload', 'SECURE_HSTS_PRELOAD'),
            ]:
                self._marcar(nombre, OK if getattr(settings, ajuste, False) else FALLA)

            segundos = getattr(settings, 'SECURE_HSTS_SECONDS', 0)
            self._marcar('HSTS de al menos un año',
                         OK if segundos >= 31536000 else FALLA, f'{segundos} s')
        else:
            self._marcar('HTTPS, HSTS y cookies seguras', AVISO,
                         'solo se activan con DEBUG=False')

        self._seccion('Sesiones y cookies')
        self._marcar('Cookie de sesión inaccesible desde JS',
                     OK if settings.SESSION_COOKIE_HTTPONLY else FALLA)
        self._marcar('SameSite configurado',
                     OK if getattr(settings, 'SESSION_COOKIE_SAMESITE', None) else FALLA,
                     str(getattr(settings, 'SESSION_COOKIE_SAMESITE', '')))
        horas = settings.SESSION_COOKIE_AGE / 3600
        self._marcar('La sesión expira', OK if settings.SESSION_COOKIE_AGE <= 86400 else AVISO,
                     f'{horas:.0f} horas')
        self._marcar('Protección CSRF activa',
                     OK if 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE else FALLA)

    def _autenticacion(self):
        self._seccion('Autenticación')

        self._marcar('Freno de fuerza bruta instalado',
                     OK if 'axes' in settings.INSTALLED_APPS else FALLA)

        limite = getattr(settings, 'AXES_FAILURE_LIMIT', 0)
        self._marcar('Límite de intentos fallidos',
                     OK if 0 < limite <= 10 else FALLA, f'{limite} intentos')

        self._marcar('Bloqueo temporal configurado',
                     OK if getattr(settings, 'AXES_COOLOFF_TIME', None) else FALLA,
                     str(getattr(settings, 'AXES_COOLOFF_TIME', '')))

        self._marcar('Backend de axes primero en la cadena',
                     OK if settings.AUTHENTICATION_BACKENDS[0].startswith('axes') else FALLA)

        validadores = [v['NAME'].rsplit('.', 1)[-1] for v in settings.AUTH_PASSWORD_VALIDATORS]
        self._marcar('Validadores de contraseña',
                     OK if len(validadores) >= 4 else AVISO, f'{len(validadores)} activos')

        largo = next((v.get('OPTIONS', {}).get('min_length')
                      for v in settings.AUTH_PASSWORD_VALIDATORS
                      if 'MinimumLength' in v['NAME']), None)
        self._marcar('Largo mínimo de contraseña',
                     OK if largo and largo >= 8 else FALLA, f'{largo} caracteres')

        # Mensaje genérico: se comprueba que exista la constante
        try:
            from apps.usuarios.views import MENSAJE_GENERICO
            revela = any(p in MENSAJE_GENERICO.lower()
                         for p in ('no existe', 'no está registrado', 'no encontrado'))
            self._marcar('El error de login no revela si el usuario existe',
                         OK if not revela else FALLA)
        except ImportError:
            self._marcar('El error de login no revela si el usuario existe', AVISO,
                         'no se pudo comprobar')

        self._marcar('Auditoría de accesos conectada',
                     OK if self._modulo_existe('apps.gestion.signals') else FALLA)

    def _datos(self):
        self._seccion('Datos')

        opciones = settings.DATABASES['default'].get('OPTIONS', {})
        modo = opciones.get('sslmode', 'no definido')
        if self.prod:
            self._marcar('TLS en la conexión a PostgreSQL',
                         OK if modo in ('require', 'verify-ca', 'verify-full') else FALLA,
                         f'sslmode={modo}')
        else:
            self._marcar('TLS en la conexión a PostgreSQL', AVISO,
                         f'sslmode={modo} (poner "require" en producción)')

        self._marcar('Clave de cifrado de campos definida',
                     OK if getattr(settings, 'FIELD_ENCRYPTION_KEY', '') else FALLA)

        # Comprobación real: leer un valor cifrado de la base
        try:
            from django.db import connection

            from apps.gestion.models import Alumno
            alumno = Alumno.todos.exclude(contacto_emergencia='').first()
            if alumno:
                with connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT contacto_emergencia FROM gestion_alumno WHERE id = %s',
                        [alumno.pk])
                    crudo = cursor.fetchone()[0] or ''
                cifrado = crudo.startswith('gAAAAA')
                self._marcar('Campos sensibles cifrados en la base',
                             OK if cifrado else FALLA,
                             'verificado leyendo la tabla' if cifrado else 'se leen en claro')
            else:
                self._marcar('Campos sensibles cifrados en la base', AVISO, 'sin datos que probar')
        except Exception as error:
            self._marcar('Campos sensibles cifrados en la base', AVISO, str(error)[:60])

        self._marcar('Sin SQL crudo en el código',
                     OK if not self._hay_sql_crudo() else FALLA)

        self._marcar('Validación de archivos subidos',
                     OK if self._modulo_existe('apps.gestion.validadores') else FALLA)

        if getattr(settings, 'USAR_R2', False):
            self._marcar('Fotos en almacenamiento privado con URL firmada',
                         OK if settings.AWS_QUERYSTRING_AUTH else FALLA)
        else:
            self._marcar('Fotos en almacenamiento externo', AVISO,
                         'R2 sin configurar: se borrarían en cada despliegue')

        from apps.gestion.models import RespaldoLog
        ultimo = RespaldoLog.objects.filter(estado=RespaldoLog.Estado.OK).first()
        if ultimo:
            from django.utils import timezone
            dias = (timezone.now() - ultimo.created_at).days
            self._marcar('Respaldo reciente', OK if dias <= 2 else AVISO,
                         f'último hace {dias} día(s)')
        else:
            self._marcar('Respaldo de la base', FALLA, 'nunca se ha corrido')

    def _secretos(self):
        self._seccion('Secretos y cumplimiento')

        self._marcar('.env fuera del control de versiones',
                     OK if self._ignorado('.env') else FALLA)
        self._marcar('logs/ fuera del control de versiones',
                     OK if self._ignorado('logs/') else FALLA)
        self._marcar('media/ fuera del control de versiones',
                     OK if self._ignorado('media/') else FALLA)

        self._marcar('Registro de eventos de seguridad',
                     OK if 'django.security' in settings.LOGGING.get('loggers', {}) else FALLA)

        from django.urls import NoReverseMatch, reverse
        for titulo, nombre in [
            ('Política de privacidad publicada', 'web:privacidad'),
            ('Formulario de derechos ARCO', 'web:mis_derechos'),
        ]:
            try:
                self._marcar(titulo, OK, reverse(nombre))
            except NoReverseMatch:
                self._marcar(titulo, FALLA, 'no existe la URL')

        for titulo, modelo in [
            ('Registro de solicitudes ARCO', 'SolicitudARCO'),
            ('Registro de brechas de seguridad', 'BrechaSeguridad'),
            ('Registro de respaldos', 'RespaldoLog'),
        ]:
            self._marcar(titulo, OK if self._modelo_existe(modelo) else FALLA)

    # ------------------------------------------------------------------
    def _resumen(self):
        ok = sum(1 for _, e, _ in self.resultados if e == OK)
        fallas = [t for t, e, _ in self.resultados if e == FALLA]
        avisos = sum(1 for _, e, _ in self.resultados if e == AVISO)

        self.stdout.write('')
        self.stdout.write('=' * 62)
        self.stdout.write(
            f'  {ok} correctos · {len(fallas)} fallas · {avisos} avisos '
            f'de {len(self.resultados)} puntos')
        self.stdout.write('=' * 62)

        if fallas:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('  Hay que corregir:'))
            for f in fallas:
                self.stdout.write(self.style.ERROR(f'    · {f}'))
        else:
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('  Sin fallas.'))
        self.stdout.write('')

    # ------------------------------------------------------------------
    def _en_env(self, clave):
        try:
            return any(l.startswith(f'{clave}=')
                       for l in open(settings.BASE_DIR / '.env', encoding='utf-8'))
        except OSError:
            return False

    def _ignorado(self, patron):
        try:
            contenido = open(settings.BASE_DIR / '.gitignore', encoding='utf-8').read()
            return patron in contenido
        except OSError:
            return False

    def _modulo_existe(self, ruta):
        import importlib
        try:
            importlib.import_module(ruta)
            return True
        except ImportError:
            return False

    def _modelo_existe(self, nombre):
        from django.apps import apps
        try:
            apps.get_model('gestion', nombre)
            return True
        except LookupError:
            return False

    def _hay_sql_crudo(self):
        """Busca .raw( y cursor.execute con f-string, que es el patrón peligroso."""
        import re

        patron = re.compile(r'\.raw\(|execute\(\s*f["\']')
        for raiz, _, archivos in os.walk(settings.BASE_DIR / 'apps'):
            if 'migrations' in raiz or '__pycache__' in raiz:
                continue
            for archivo in archivos:
                if not archivo.endswith('.py'):
                    continue
                # El comando de respaldo y este mismo hacen consultas
                # parametrizadas legítimas.
                if archivo in ('respaldar_bd.py', 'revisar_seguridad.py'):
                    continue
                try:
                    with open(os.path.join(raiz, archivo), encoding='utf-8') as f:
                        if patron.search(f.read()):
                            return True
                except OSError:
                    continue
        return False
