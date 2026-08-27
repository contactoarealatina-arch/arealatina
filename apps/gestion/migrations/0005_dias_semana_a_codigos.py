"""Convierte Clase.dias_semana de texto libre a códigos separados por coma.

Antes:  'Lunes y Miércoles'
Ahora:  'LU,MI'
"""
from django.db import migrations

# Se acepta con y sin tilde: los datos viejos tenían ambas formas.
NOMBRES = [
    ('LU', ('lunes',)),
    ('MA', ('martes',)),
    ('MI', ('miercoles', 'miércoles')),
    ('JU', ('jueves',)),
    ('VI', ('viernes',)),
    ('SA', ('sabado', 'sábado')),
    ('DO', ('domingo',)),
]


def texto_a_codigos(apps, schema_editor):
    Clase = apps.get_model('gestion', 'Clase')
    for clase in Clase.objects.all():
        original = (clase.dias_semana or '').lower()

        # Si ya está en formato de códigos, no se toca.
        if original and all(
            trozo.strip().upper() in dict(NOMBRES)
            for trozo in original.split(',') if trozo.strip()
        ):
            continue

        codigos = [cod for cod, variantes in NOMBRES
                   if any(v in original for v in variantes)]
        clase.dias_semana = ','.join(codigos)
        clase.save(update_fields=['dias_semana'])


def codigos_a_texto(apps, schema_editor):
    Clase = apps.get_model('gestion', 'Clase')
    etiquetas = {
        'LU': 'Lunes', 'MA': 'Martes', 'MI': 'Miércoles', 'JU': 'Jueves',
        'VI': 'Viernes', 'SA': 'Sábado', 'DO': 'Domingo',
    }
    for clase in Clase.objects.all():
        nombres = [etiquetas[c] for c in clase.dias_semana.split(',') if c in etiquetas]
        if len(nombres) > 1:
            clase.dias_semana = ', '.join(nombres[:-1]) + ' y ' + nombres[-1]
        else:
            clase.dias_semana = nombres[0] if nombres else ''
        clase.save(update_fields=['dias_semana'])


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0004_configuracionalertas_alter_inscripcion_options_and_more'),
    ]

    operations = [
        migrations.RunPython(texto_a_codigos, codigos_a_texto),
    ]
