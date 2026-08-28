"""Crea una cuenta de acceso y le manda su correo de bienvenida.

Uso:
    python manage.py crear_acceso --rol profesor --email ana@gmail.com \\
        --nombre "Ana Pérez" --clave "SuClave123"

    python manage.py crear_acceso --rol alumno --email juan@gmail.com \\
        --nombre "Juan Soto" --rut 11.111.111-1 --enlace

Si se pasa --clave, la cuenta queda lista para entrar de inmediato.
Si se pasa --enlace, se manda un enlace de un solo uso para que la persona
elija su propia contraseña (es lo recomendable con gente real: así nadie
más la conoce).

Con --sin-correo se crea la cuenta pero no se envía nada.

El envío va por SMTP real aunque DEBUG esté en True: si no, el correo se
imprimiría en la consola y no llegaría a ninguna parte.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test.utils import override_settings
from django.utils import timezone

from apps.gestion.forms import validar_rut
from apps.gestion.models import Alumno, Clase, Plan, Suscripcion, TokenActivacion

Usuario = get_user_model()

BACKEND_REAL = 'django.core.mail.backends.smtp.EmailBackend'


class Command(BaseCommand):
    help = 'Crea una cuenta de profesor o alumno y le envía su bienvenida.'

    def add_arguments(self, parser):
        parser.add_argument('--rol', required=True, choices=['profesor', 'alumno'])
        parser.add_argument('--email', required=True)
        parser.add_argument('--nombre', required=True, help='Nombre y apellido.')
        parser.add_argument('--usuario', help='Nombre de usuario. Por defecto se sugiere uno.')
        parser.add_argument('--clave', help='Contraseña inicial. Si se omite, usa --enlace.')
        parser.add_argument('--enlace', action='store_true',
                            help='Manda un enlace de un solo uso en vez de una contraseña.')
        parser.add_argument('--rut', help='Solo para alumnos.')
        parser.add_argument('--telefono', default='')
        parser.add_argument('--sin-correo', action='store_true')

    # ------------------------------------------------------------------
    def handle(self, *args, **opciones):
        if not opciones['clave'] and not opciones['enlace']:
            raise CommandError('Indica --clave o --enlace.')

        if opciones['rol'] == 'profesor':
            usuario, token, alumno = self._profesor(opciones)
        else:
            usuario, token, alumno = self._alumno(opciones)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Cuenta lista:'))
        self.stdout.write(f'  Nombre  : {usuario.get_full_name()}')
        self.stdout.write(f'  Usuario : {usuario.username}')
        self.stdout.write(f'  Email   : {usuario.email}')
        self.stdout.write(f'  Rol     : {usuario.get_rol_display()}')
        self.stdout.write(f'  Acceso  : {"enlace de un solo uso" if token else "contraseña fijada"}')

        if opciones['sin_correo']:
            self.stdout.write(self.style.WARNING('Correo omitido (--sin-correo).'))
            return

        self._enviar(usuario, token, alumno)

    # ------------------------------------------------------------------
    def _profesor(self, opciones):
        usuario = self._usuario_base(opciones, Usuario.Rol.PROFESOR)
        usuario.especialidad = opciones.get('especialidad', '') or usuario.especialidad
        usuario.save()

        token = None
        if opciones['enlace']:
            usuario.set_unusable_password()
            usuario.save(update_fields=['password'])
            token = TokenActivacion.crear_para(usuario)

        # Sin clases asignadas el correo queda vacío: se le da la primera libre.
        if not Clase.objects.filter(profesora=usuario).exists():
            clase = Clase.objects.filter(activa=True, profesora__isnull=True).first()
            if clase:
                clase.profesora = usuario
                clase.save(update_fields=['profesora'])
                self.stdout.write(f'  Se le asignó la clase: {clase}')

        return usuario, token, None

    def _alumno(self, opciones):
        rut = opciones.get('rut')
        if not rut:
            raise CommandError('Un alumno necesita --rut.')
        rut = validar_rut(rut)

        usuario = self._usuario_base(opciones, Usuario.Rol.ALUMNO)
        usuario.rut = rut
        usuario.save(update_fields=['rut'])

        alumno, creado = Alumno.todos.get_or_create(
            rut=rut,
            defaults={
                'nombre_completo': opciones['nombre'],
                'email': opciones['email'],
                'telefono': opciones['telefono'],
                'contacto_emergencia': 'Por completar',
                'telefono_emergencia': 'Por completar',
                'fecha_ingreso': timezone.localdate(),
            },
        )
        if not creado:
            alumno.email = opciones['email']
            alumno.eliminado = False
            alumno.save(update_fields=['email', 'eliminado'])

        alumno.usuario = usuario
        alumno.save(update_fields=['usuario'])

        # Para que el correo y el portal tengan algo que mostrar.
        if not alumno.inscripciones.exists():
            for clase in Clase.objects.filter(activa=True)[:2]:
                alumno.inscripciones.create(clase=clase)
            self.stdout.write(f'  Inscrito en {alumno.inscripciones.count()} clases')

        if not alumno.suscripcion_vigente:
            plan = Plan.objects.filter(activo=True, duracion_dias__gt=1).first()
            if plan:
                Suscripcion.objects.create(alumno=alumno, plan=plan)
                self.stdout.write(f'  Plan asignado: {plan.nombre}')

        token = None
        if opciones['enlace']:
            usuario.set_unusable_password()
            usuario.save(update_fields=['password'])
            token = TokenActivacion.crear_para(usuario)

        return usuario, token, alumno

    # ------------------------------------------------------------------
    def _usuario_base(self, opciones, rol):
        partes = opciones['nombre'].split()
        nombre = partes[0]
        apellido = ' '.join(partes[1:])

        username = opciones.get('usuario')
        if not username:
            import re
            import unicodedata

            limpio = ''.join(
                c for c in unicodedata.normalize('NFD', opciones['nombre'].lower())
                if unicodedata.category(c) != 'Mn'
            )
            trozos = limpio.split()
            base = f'{trozos[0]}.{trozos[-1]}' if len(trozos) > 1 else trozos[0]
            username = re.sub(r'[^a-z0-9._]', '', base)[:26]

        usuario, creado = Usuario.objects.get_or_create(
            username=username,
            defaults={'email': opciones['email'], 'first_name': nombre,
                      'last_name': apellido, 'rol': rol},
        )
        usuario.email = opciones['email']
        usuario.first_name = nombre
        usuario.last_name = apellido
        usuario.rol = rol
        usuario.is_active = True
        if opciones['telefono']:
            usuario.telefono = opciones['telefono']
        if opciones['clave']:
            usuario.set_password(opciones['clave'])
        usuario.save()

        self.stdout.write(f'  {"Creado" if creado else "Actualizado"}: {username}')
        return usuario

    # ------------------------------------------------------------------
    def _enviar(self, usuario, token, alumno):
        from apps.gestion import correos
        from django.conf import settings
        from django.urls import reverse

        if not settings.EMAIL_HOST_PASSWORD:
            self.stdout.write(self.style.ERROR(
                'Falta EMAIL_HOST_PASSWORD en el .env: el correo no puede salir.'))
            return

        enlace = ''
        if token:
            base = getattr(settings, 'SITIO_URL', 'http://localhost:8000').rstrip('/')
            enlace = base + reverse('portal:activar', args=[token.token])

        # SMTP real aunque DEBUG esté activo: si no, el correo solo se
        # imprimiría en la consola.
        with override_settings(EMAIL_BACKEND=BACKEND_REAL):
            if alumno is not None:
                enviado, motivo = correos.enviar_bienvenida(alumno, enlace, usuario)
            else:
                enviado, motivo = correos.enviar_bienvenida_profesora(usuario, enlace)

        estilo = self.style.SUCCESS if enviado else self.style.WARNING
        self.stdout.write(estilo(f'  Correo: {motivo}'))

        if enlace:
            self.stdout.write(f'  Enlace de activación: {enlace}')
