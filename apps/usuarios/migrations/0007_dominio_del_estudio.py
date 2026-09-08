# -*- coding: utf-8 -*-
"""Los correos del estudio pasan al dominio que se compro.

La migracion 0004 los creo con @arealatina.cl, que era el nombre que se
manejaba entonces. El dominio que quedo inscrito en nic.cl es
arealatinaestudio.cl, asi que los correos con que entran las profesoras
apuntaban a un dominio de otra persona.
"""
from django.conf import settings
from django.db import migrations

VIEJO = '@arealatina.cl'


def mudar(apps, schema_editor):
    Usuario = apps.get_model('usuarios', 'CustomUser')
    nuevo = '@' + getattr(settings, 'DOMINIO_PROFESORAS', 'arealatinaestudio.cl')

    ocupados = set(
        Usuario.objects.exclude(correo_institucional=None)
        .exclude(correo_institucional='')
        .values_list('correo_institucional', flat=True)
    )

    for usuario in Usuario.objects.filter(correo_institucional__endswith=VIEJO):
        destino = usuario.correo_institucional[:-len(VIEJO)] + nuevo
        # El correo del estudio es unico. Si ya estuviera tomado se deja
        # como esta: es preferible un correo con el dominio antiguo que
        # una migracion que revienta y deja la base a medio camino.
        if destino in ocupados:
            continue
        ocupados.discard(usuario.correo_institucional)
        ocupados.add(destino)
        usuario.correo_institucional = destino
        usuario.save(update_fields=['correo_institucional'])


def revertir(apps, schema_editor):
    Usuario = apps.get_model('usuarios', 'CustomUser')
    nuevo = '@' + getattr(settings, 'DOMINIO_PROFESORAS', 'arealatinaestudio.cl')
    for usuario in Usuario.objects.filter(correo_institucional__endswith=nuevo):
        usuario.correo_institucional = usuario.correo_institucional[:-len(nuevo)] + VIEJO
        usuario.save(update_fields=['correo_institucional'])


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0006_alumnos_entran_por_correo'),
    ]

    operations = [
        migrations.RunPython(mudar, revertir),
    ]
