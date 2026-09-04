# -*- coding: utf-8 -*-
"""Las cinco áreas pasan a ser dos pilares: Baile Urbano y Bienestar.

El estudio decidió contar solo dos cosas. Danza y Kids & Teens se funden
en Baile Urbano (Kids Dance es una clase de baile, y con dos pilares no
hay dónde más ponerla); Wellness pasa a llamarse Bienestar. En Escena y
Compañías se eliminan: nunca tuvieron clases asignadas.

Va como migración y no como comando porque el sitio no se puede pintar
sin pilares: si el despliegue queda sin ellos, /clases/ sale vacía.
"""
from django.db import migrations

PILARES = [
    ('baile-urbano', 'Baile Urbano',
     'Salsa, bachata, reggaetón, heels, urbano y tango.',
     'bi-music-note-beamed', 1),
    ('bienestar', 'Bienestar',
     'Pilates Mat, Barre, Flexibilidad y Reformer.',
     'bi-flower1', 2),
]

# De dónde viene cada pilar nuevo.
FUSION = {
    'baile-urbano': ['danza', 'kids-teens'],
    'bienestar': ['wellness'],
}

# Sin clases asignadas: se van sin dejar nada huérfano.
A_ELIMINAR = ['en-escena', 'companias']


def fusionar(apps, schema_editor):
    Categoria = apps.get_model('gestion', 'Categoria')
    Clase = apps.get_model('gestion', 'Clase')

    for slug, nombre, bajada, icono, orden in PILARES:
        origen = FUSION[slug]

        # Si una de las categorías de origen ya existe, se reutiliza en vez
        # de crear una nueva: así las clases no quedan apuntando al vacío.
        pilar = Categoria.objects.filter(slug__in=origen).order_by('orden').first()
        if pilar is None:
            pilar = Categoria(slug=slug)

        pilar.slug = slug
        pilar.nombre = nombre
        pilar.bajada = bajada
        pilar.icono = icono
        pilar.orden = orden
        pilar.activa = True
        pilar.save()

        # Las clases de las otras categorías de origen se mudan acá.
        sobrantes = Categoria.objects.filter(slug__in=origen).exclude(pk=pilar.pk)
        Clase.objects.filter(categoria__in=sobrantes).update(categoria=pilar)
        sobrantes.delete()

    # Las que se eliminan no deberían tener clases, pero si el estudio
    # alcanzó a asignar alguna, se rescata en Baile Urbano antes de borrar.
    baile = Categoria.objects.get(slug='baile-urbano')
    fuera = Categoria.objects.filter(slug__in=A_ELIMINAR)
    Clase.objects.filter(categoria__in=fuera).update(categoria=baile)
    fuera.delete()


def revertir(apps, schema_editor):
    """Vuelve a los nombres anteriores, sin recrear las cinco áreas.

    Separar de nuevo Danza de Kids & Teens no se puede: al fusionar se
    perdió cuál clase venía de cuál. Se deja el estado más cercano.
    """
    Categoria = apps.get_model('gestion', 'Categoria')
    for slug, nombre in (('baile-urbano', 'Danza'), ('bienestar', 'Wellness')):
        Categoria.objects.filter(slug=slug).update(
            slug='danza' if slug == 'baile-urbano' else 'wellness',
            nombre=nombre,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0015_foto_delete_evento_alter_categoria_options_and_more'),
    ]

    operations = [
        migrations.RunPython(fusionar, revertir),
    ]
