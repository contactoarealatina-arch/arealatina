from unittest.mock import Mock, patch

from django.core.mail import EmailMultiAlternatives
from django.test import SimpleTestCase, override_settings

from apps.gestion.email_backends import BrevoAPIBackend


@override_settings(
    BREVO_API_KEY='clave-de-prueba',
    DEFAULT_FROM_EMAIL='Area Latina Estudio <contacto@arealatinaestudio.cl>',
)
class BrevoAPIBackendTests(SimpleTestCase):
    @patch('apps.gestion.email_backends.requests.post')
    def test_envia_texto_html_y_reply_to(self, post):
        post.return_value = Mock(status_code=201, text='')
        mensaje = EmailMultiAlternatives(
            subject='Bienvenida',
            body='Hola en texto',
            from_email='Area Latina Estudio <contacto@arealatinaestudio.cl>',
            to=['Alumno <alumno@example.com>'],
            reply_to=['contacto.arealatina@gmail.com'],
        )
        mensaje.attach_alternative('<strong>Hola</strong>', 'text/html')

        enviados = BrevoAPIBackend().send_messages([mensaje])

        self.assertEqual(enviados, 1)
        llamada = post.call_args
        self.assertEqual(llamada.kwargs['timeout'], 30)
        self.assertEqual(llamada.kwargs['headers']['api-key'], 'clave-de-prueba')
        payload = llamada.kwargs['json']
        self.assertEqual(payload['sender'], {
            'email': 'contacto@arealatinaestudio.cl',
            'name': 'Area Latina Estudio',
        })
        self.assertEqual(payload['to'], [{
            'email': 'alumno@example.com',
            'name': 'Alumno',
        }])
        self.assertEqual(payload['replyTo'], {
            'email': 'contacto.arealatina@gmail.com',
        })
        self.assertEqual(payload['textContent'], 'Hola en texto')
        self.assertEqual(payload['htmlContent'], '<strong>Hola</strong>')

    @patch('apps.gestion.email_backends.requests.post')
    def test_informa_el_error_de_brevo(self, post):
        post.return_value = Mock(
            status_code=401,
            text='{"code":"unauthorized","message":"Key not found"}',
        )
        mensaje = EmailMultiAlternatives(
            subject='Prueba', body='Texto', to=['alumno@example.com'],
        )

        with self.assertRaisesRegex(RuntimeError, 'HTTP 401'):
            BrevoAPIBackend().send_messages([mensaje])

    @override_settings(BREVO_API_KEY='')
    def test_rechaza_configuracion_sin_api_key(self):
        mensaje = EmailMultiAlternatives(
            subject='Prueba', body='Texto', to=['alumno@example.com'],
        )

        with self.assertRaisesRegex(ValueError, 'BREVO_API_KEY'):
            BrevoAPIBackend().send_messages([mensaje])

    @override_settings(BREVO_API_KEY='')
    def test_fail_silently_no_lanza_excepcion(self):
        mensaje = EmailMultiAlternatives(
            subject='Prueba', body='Texto', to=['alumno@example.com'],
        )

        enviados = BrevoAPIBackend(fail_silently=True).send_messages([mensaje])

        self.assertEqual(enviados, 0)
