from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class SeguridadSesionesTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='seguridad',
            email='seguridad@example.com',
            password='Clave-fuerte-2026!',
            rol='SUPERADMIN',
            is_staff=True,
        )

    def test_sesion_termina_con_navegador_y_por_inactividad(self):
        self.assertTrue(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)
        self.assertLessEqual(settings.SESSION_COOKIE_AGE, 30 * 60)

    def test_revisores_separados_son_superadmins_y_cambian_su_clave(self):
        Usuario = get_user_model()
        for identidad in (
            'sergio@arealatinaestudio.cl',
            'katy@arealatinaestudio.cl',
        ):
            usuario = Usuario.objects.get(username=identidad)
            self.assertTrue(usuario.is_superuser)
            self.assertTrue(usuario.is_staff)
            self.assertEqual(usuario.rol, Usuario.Rol.SUPERADMIN)
            self.assertTrue(usuario.debe_cambiar_clave)

    def test_clave_temporal_no_puede_saltar_al_admin(self):
        revisor = get_user_model().objects.get(
            username='sergio@arealatinaestudio.cl')
        self.client.force_login(revisor)

        respuesta = self.client.get('/admin/')

        self.assertRedirects(
            respuesta,
            reverse('portal:cambiar_clave'),
            fetch_redirect_response=False,
        )

    def test_panel_privado_nunca_se_guarda_en_cache(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('gestion:dashboard'))
        cache_control = respuesta.headers.get('Cache-Control', '')

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('no-store', cache_control)
        self.assertIn('private', cache_control)
        self.assertEqual(respuesta.headers['Pragma'], 'no-cache')
        self.assertEqual(respuesta.headers['Expires'], '0')

    def test_otro_navegador_no_hereda_la_sesion(self):
        navegador_a = Client()
        navegador_b = Client()
        navegador_a.force_login(self.usuario)

        self.assertEqual(
            navegador_a.get(reverse('gestion:dashboard')).status_code, 200)
        self.assertRedirects(
            navegador_b.get(reverse('gestion:dashboard')),
            f"{reverse('usuarios:login')}?next={reverse('gestion:dashboard')}",
            fetch_redirect_response=False,
        )
        self.assertNotEqual(
            navegador_a.cookies.get(settings.SESSION_COOKIE_NAME),
            navegador_b.cookies.get(settings.SESSION_COOKIE_NAME),
        )

    def test_alumno_autenticado_no_puede_entrar_a_gestion(self):
        alumno = get_user_model().objects.create_user(
            username='alumno-seguridad',
            password='Clave-alumno-2026!',
            rol='ALUMNO',
        )
        self.client.force_login(alumno)

        respuesta = self.client.get(reverse('gestion:dashboard'))

        self.assertEqual(respuesta.status_code, 403)
