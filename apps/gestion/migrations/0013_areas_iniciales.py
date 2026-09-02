# -*- coding: utf-8 -*-
"""Crea las cinco áreas del brief y engancha las clases que ya existen.

Va como migración y no como comando porque el sitio público las necesita
para poder pintarse: si el despliegue queda sin áreas, /clases/ y
/wellness/ salen vacías.
"""
from django.db import migrations

# (slug, nombre, bajada, icono, orden)
AREAS = [
    ('danza', 'Danza',
     'Salsa, bachata, heels, urbano y más.',
     'bi-music-note-beamed', 1),
    ('wellness', 'Wellness',
     'Pilates Mat, Barre, Flexibilidad y Reformer.',
     'bi-flower1', 2),
    ('kids-teens', 'Kids & Teens',
     'Movimiento y formación desde los 4 años.',
     'bi-emoji-smile', 3),
    ('en-escena', 'En Escena',
     'Procesos formativos que terminan en escenario.',
     'bi-lamp', 4),
    ('companias', 'Compañías',
     'Entrenamiento, representación y competencia.',
     'bi-people', 5),
]

# Cada disciplina existente cae en un área. Las que no están acá quedan
# sin área y el equipo la asigna a mano desde el panel.
POR_DISCIPLINA = {
    'SALSA': 'danza',
    'BACHATA': 'danza',
    'REGGAETON': 'danza',
    'URBANO': 'danza',
    'HEELS': 'danza',
    'TANGO': 'danza',
    'KIDS': 'kids-teens',
    'PILATES': 'wellness',
    'BARRE': 'wellness',
    'FLEXIBILIDAD': 'wellness',
    'REFORMER': 'wellness',
}


def crear(apps, schema_editor):
    Categoria = apps.get_model('gestion', 'Categoria')
    Clase = apps.get_model('gestion', 'Clase')

    creadas = {}
    for slug, nombre, bajada, icono, orden in AREAS:
        creadas[slug], _ = Categoria.objects.get_or_create(
            slug=slug,
            defaults={'nombre': nombre, 'bajada': bajada,
                      'icono': icono, 'orden': orden},
        )

    for disciplina, slug in POR_DISCIPLINA.items():
        Clase.objects.filter(nombre=disciplina, categoria__isnull=True).update(
            categoria=creadas[slug],
        )


def borrar(apps, schema_editor):
    Categoria = apps.get_model('gestion', 'Categoria')
    Categoria.objects.filter(slug__in=[a[0] for a in AREAS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0012_categoria_evento_testimonio_clase_edad_minima_and_more'),
    ]

    operations = [
        migrations.RunPython(crear, borrar),
    ]
