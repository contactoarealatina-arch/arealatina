from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.gestion.models import Alumno


class LimpiezaDatosDemoTests(TestCase):
    def test_borra_solo_demo_y_su_acceso_ficticio(self):
        Usuario = get_user_model()
        acceso_demo = Usuario.objects.create_user(
            username='demo@ejemplo.cl',
            email='demo@ejemplo.cl',
            password='solo-prueba',
            rol=Usuario.Rol.ALUMNO,
        )
        Alumno.todos.create(
            nombre_completo='Persona Demo',
            rut='90.999.999-1',
            contacto_emergencia='',
            telefono_emergencia='',
            usuario=acceso_demo,
        )
        real = Alumno.todos.create(
            nombre_completo='Persona Real',
            rut='12.345.678-5',
            contacto_emergencia='',
            telefono_emergencia='',
        )

        call_command('datos_demo', '--borrar-demo')

        self.assertFalse(Alumno.todos.filter(rut__startswith='90.').exists())
        self.assertFalse(Usuario.objects.filter(pk=acceso_demo.pk).exists())
        self.assertTrue(Alumno.todos.filter(pk=real.pk).exists())

    @override_settings(DEBUG=False)
    def test_no_permite_generar_demo_en_produccion(self):
        with self.assertRaises(CommandError):
            call_command('datos_demo', '--con-alumnos')
