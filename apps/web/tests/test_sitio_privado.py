from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.web.context_processors import academia
from apps.web.middleware import SitioPrivado


@override_settings(SITIO_PRIVADO=True)
class SitioPrivadoTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = SitioPrivado(lambda request: HttpResponse('visible'))

    def _get(self, ruta):
        request = self.factory.get(ruta)
        request.user = AnonymousUser()
        return self.middleware(request)

    def test_paginas_publicas_siguen_visibles(self):
        for ruta in ('/', '/clases/', '/contacto/', '/privacidad/'):
            with self.subTest(ruta=ruta):
                respuesta = self._get(ruta)
                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.content, b'visible')

    def test_ruta_interna_anonima_sigue_tapada(self):
        respuesta = self._get('/gestion/')

        self.assertEqual(respuesta.status_code, 503)
        self.assertContains(
            respuesta, 'Estamos preparando el sitio', status_code=503,
        )

    def test_contexto_muestra_el_aviso(self):
        contexto = academia(self.factory.get('/'))

        self.assertTrue(contexto['sitio_en_preparacion'])
