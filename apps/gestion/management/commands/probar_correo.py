"""Prueba el envío real por SMTP, sin importar el valor de DEBUG.

Uso:
    python manage.py probar_correo destino@ejemplo.cl
    python manage.py probar_correo destino@ejemplo.cl --plantilla bienvenida

Sirve para verificar que la clave de Brevo funciona y para revisar cómo se
ve cada plantilla en un cliente de correo de verdad. Fuerza el backend SMTP
porque en desarrollo (DEBUG=True) los correos solo se imprimen en consola y
eso no prueba nada.
"""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string
from django.utils import timezone

PLANTILLAS = [
    'bienvenida', 'recibo_pago', 'recordatorio',
    'mensaje_contacto', 'resumen_alertas',
]


class Command(BaseCommand):
    help = 'Envía un correo de prueba por SMTP real para verificar Brevo.'

    def add_arguments(self, parser):
        parser.add_argument('destino', help='Correo que recibirá la prueba.')
        parser.add_argument(
            '--plantilla',
            choices=PLANTILLAS,
            help='Envía una plantilla real con datos de la base en vez del correo simple.',
        )

    def handle(self, *args, **opciones):
        destino = opciones['destino']
        plantilla = opciones.get('plantilla')

        if not settings.EMAIL_HOST_PASSWORD:
            raise CommandError(
                'Falta EMAIL_HOST_PASSWORD en el archivo .env. '
                'Sin la clave SMTP de Brevo no se puede enviar nada.'
            )

        self.stdout.write('Configuración:')
        self.stdout.write(f'  Servidor:   {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
        self.stdout.write(f'  Usuario:    {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'  Remitente:  {settings.DEFAULT_FROM_EMAIL}')
        self.stdout.write(f'  Destino:    {destino}')
        self.stdout.write('')

        if plantilla:
            asunto, texto, html = self._plantilla_real(plantilla)
        else:
            asunto, texto, html = self._correo_simple()

        # Conexión SMTP explícita: ignora el backend de consola de DEBUG.
        conexion = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
            fail_silently=False,
        )

        mensaje = EmailMultiAlternatives(
            subject=asunto,
            body=texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destino],
            connection=conexion,
        )
        if html:
            mensaje.attach_alternative(html, 'text/html')

        try:
            enviados = mensaje.send()
        except Exception as error:
            self.stdout.write(self.style.ERROR(f'FALLÓ: {error}'))
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('Posibles causas:'))
            self.stdout.write('  · La clave SMTP no es la correcta.')
            self.stdout.write('  · El remitente no está verificado en Brevo.')
            self.stdout.write('  · Se acabaron los créditos del día (300 en el plan gratis).')
            raise CommandError('No se pudo enviar.')

        if enviados:
            self.stdout.write(self.style.SUCCESS(f'Enviado. Revisa la bandeja de {destino}.'))
            self.stdout.write(self.style.WARNING(
                'Si no llega en unos minutos, mira también la carpeta de spam.'
            ))
        else:
            self.stdout.write(self.style.ERROR('El servidor no aceptó el mensaje.'))

    # ------------------------------------------------------------------
    def _correo_simple(self):
        ahora = timezone.localtime()
        asunto = f'Prueba de correo · Área Latina Estudio ({ahora:%H:%M})'
        texto = (
            'Esta es una prueba de la conexión con Brevo.\n\n'
            f'Enviada el {ahora:%d/%m/%Y a las %H:%M}.\n'
            'Si te llegó, el sistema de correos está funcionando.\n'
        )
        html = render_to_string('gestion/emails/prueba.html', {
            'ahora': ahora,
            'academia': settings.ACADEMIA,
        })
        return asunto, texto, html

    def _plantilla_real(self, plantilla):
        """Arma la plantilla pedida con datos que ya estén en la base."""
        from apps.gestion.models import Alumno, Pago, Suscripcion
        from apps.gestion.servicios import generar_alertas, nombre_mes
        from apps.web.models import MensajeContacto

        base = {'academia': settings.ACADEMIA}
        hoy = timezone.localdate()

        if plantilla == 'bienvenida':
            alumno = Alumno.objects.first()
            if not alumno:
                raise CommandError('No hay alumnos en la base para armar el ejemplo.')
            ctx = {**base, 'alumno': alumno,
                   'suscripcion': alumno.suscripcion_vigente,
                   'clases': [i.clase for i in alumno.inscripciones.select_related('clase')]}
            asunto = f'[PRUEBA] ¡Bienvenido/a a Área Latina Estudio, {alumno.primer_nombre}!'

        elif plantilla == 'recibo_pago':
            pago = Pago.objects.select_related('alumno').first()
            if not pago:
                raise CommandError('No hay pagos en la base para armar el ejemplo.')
            ctx = {**base, 'pago': pago, 'alumno': pago.alumno,
                   'suscripcion': pago.suscripcion}
            asunto = '[PRUEBA] Comprobante de pago · Área Latina Estudio'

        elif plantilla == 'recordatorio':
            sus = Suscripcion.objects.select_related('plan', 'alumno').first()
            if not sus:
                raise CommandError('No hay suscripciones en la base.')
            ctx = {**base, 'alumno': sus.alumno, 'suscripcion': sus,
                   'dias': sus.dias_restantes, 'vencido': sus.dias_restantes < 0}
            asunto = '[PRUEBA] Tu plan en Área Latina está por vencer'

        elif plantilla == 'mensaje_contacto':
            ctx = {**base, 'mensaje': MensajeContacto(
                nombre='Persona de Prueba', email='prueba@ejemplo.cl',
                telefono='+56 9 1234 5678',
                mensaje='Hola, quiero saber los horarios de bachata.',
                created_at=timezone.now())}
            asunto = '[PRUEBA] Nuevo mensaje web'

        else:  # resumen_alertas
            resumen = generar_alertas()
            ctx = {**base, 'fecha': hoy, 'mes': nombre_mes(hoy),
                   'por_vencer': resumen['por_vencer'],
                   'vencidos': resumen['vencidos'],
                   'sin_pago': resumen['sin_pago']}
            asunto = f'[PRUEBA] Área Latina — Resumen de alertas {hoy:%d/%m/%Y}'

        html = render_to_string(f'gestion/emails/{plantilla}.html', ctx)
        texto = render_to_string(f'gestion/emails/{plantilla}.txt', ctx)
        return asunto, texto, html
