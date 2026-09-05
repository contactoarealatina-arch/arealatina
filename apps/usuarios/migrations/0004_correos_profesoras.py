# -*- coding: utf-8 -*-
"""Le da correo institucional a las profesoras que ya existen.

El correo que tenían pasa a ser el personal: es el que revisan de verdad
y donde les llegan los avisos. El institucional es solo la identidad con
la que entran al sistema.
"""
import unicodedata

from django.db import migrations

DOMINIO = 'arealatina.cl'


def limpiar(texto):
    sin_tildes = unicodedata.normalize('NFKD', texto or '')
    sin_tildes = sin_tildes.encode('ascii', 'ignore').decode()
    return ''.join(c for c in sin_tildes.lower() if c.isalnum())


def poblar(apps, schema_editor):
    Usuario = apps.get_model('usuarios', 'CustomUser')

    usados = set()
    for profesora in Usuario.objects.filter(rol='PROFESOR'):
        # Lo que tenía pasa a ser su correo personal.
        if profesora.email and not profesora.correo_personal:
            profesora.correo_personal = profesora.email

        if not profesora.correo_institucional:
            base = limpiar(profesora.first_name)
            apellido = limpiar(profesora.last_name)
            if apellido:
                base = f'{base}.{apellido}'
            base = base or limpiar(profesora.username) or 'profesora'

            candidato = f'{base}@{DOMINIO}'
            contador = 2
            while candidato in usados or Usuario.objects.filter(
                correo_institucional=candidato,
            ).exists():
                candidato = f'{base}{contador}@{DOMINIO}'
                contador += 1

            usados.add(candidato)
            profesora.correo_institucional = candidato

        profesora.save(update_fields=['correo_personal', 'correo_institucional'])


def limpiar_todo(apps, schema_editor):
    Usuario = apps.get_model('usuarios', 'CustomUser')
    Usuario.objects.filter(rol='PROFESOR').update(correo_institucional=None)


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_customuser_correo_institucional_and_more'),
    ]

    operations = [
        migrations.RunPython(poblar, limpiar_todo),
    ]
