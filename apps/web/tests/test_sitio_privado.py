from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(SITIO_PRIVADO=True, SITIO_PIN='5577')
class SitioPrivadoTests(TestCase):
    def test_publico_ve_la_pantalla_de_preparacion(self):
        respuesta = self.client.get(reverse('web:index'))

        self.assertEqual(respuesta.status_code, 503)
        self.assertContains(
            respuesta, 'Estamos preparando el sitio', status_code=503,
        )
        self.assertContains(respuesta, 'Vista previa privada', status_code=503)

    def test_pin_correcto_abre_la_web_en_la_sesion(self):
        respuesta = self.client.post(reverse('web:revision'), {
            'pin': '5577',
            'next': reverse('web:clases'),
        })

        self.assertRedirects(respuesta, reverse('web:clases'),
                             fetch_redirect_response=False)
        self.assertTrue(self.client.session['sitio_revision_autorizada'])
        self.assertEqual(self.client.get(reverse('web:clases')).status_code, 200)

    def test_pin_incorrecto_no_abre_la_web(self):
        respuesta = self.client.post(reverse('web:revision'), {
            'pin': '0000',
            'next': reverse('web:index'),
        })

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'El PIN no es correcto')
        self.assertNotIn('sitio_revision_autorizada', self.client.session)
        self.assertEqual(self.client.get(reverse('web:index')).status_code, 503)

    def test_destino_externo_se_descarta(self):
        respuesta = self.client.post(reverse('web:revision'), {
            'pin': '5577',
            'next': 'https://ejemplo.com/',
        })

        self.assertRedirects(respuesta, '/', fetch_redirect_response=False)

    def test_login_del_equipo_sigue_disponible(self):
        respuesta = self.client.get(reverse('usuarios:login'))

        self.assertEqual(respuesta.status_code, 200)
