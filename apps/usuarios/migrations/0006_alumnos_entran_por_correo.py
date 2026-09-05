# -*- coding: utf-8 -*-
"""Los alumnos pasan a entrar con su correo.

Antes el nombre de usuario era nombre.apellido y había que enseñárselo.
Ahora es su propio correo, que ya se saben de memoria.

Solo se toca a quien tenga correo y no lo esté usando ya otra cuenta. El
backend de acceso sigue aceptando el nombre de usuario antiguo, así que
nadie se queda afuera aunque su fila no se pueda migrar.
"""
from django.db import migrations


def usar_correo(apps, schema_editor):
    Usuario = apps.get_model('usuarios', 'CustomUser')

    ocupados = set(
        Usuario.objects.values_list('username', flat=True)
    )

    for usuario in Usuario.objects.filter(rol='ALUMNO').exclude(email=''):
        correo = (usuario.email or '').strip().lower()
        if not correo or usuario.username == correo:
            continue
        # Si ese correo ya es el usuario de otra cuenta, se deja como está:
        # dos cuentas con el mismo nombre de usuario no pueden existir.
        if correo in ocupados:
            continue

        ocupados.discard(usuario.username)
        ocupados.add(correo)
        usuario.username = correo
        usuario.save(update_fields=['username'])


def revertir(apps, schema_editor):
    """No se revierte: los nombres de usuario antiguos no se guardaron.

    El backend acepta el correo igual, así que dejarlo como está no rompe
    el acceso de nadie.
    """


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0005_customuser_debe_cambiar_clave'),
    ]

    operations = [
        migrations.RunPython(usar_correo, revertir),
    ]
