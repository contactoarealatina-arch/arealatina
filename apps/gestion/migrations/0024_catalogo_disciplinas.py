# -*- coding: utf-8 -*-
"""Llena el catálogo de disciplinas y convierte los códigos en nombres.

Hasta acá la disciplina se guardaba como código ('SALSA') y la etiqueta
vivía en el modelo. Ahora se guarda ya escrita ('Salsa'), porque el
estudio puede abrir ritmos nuevos sin tocar el código.

También reparte los planes entre los dos pilares y marca como Kids las
clases que antes tenían edad mínima de niños.
"""
from django.db import migrations

# (código antiguo, nombre, emoji, orden)
DISCIPLINAS = [
    ('SALSA', 'Salsa', '\U0001F483', 1),
    ('BACHATA', 'Bachata', '\U0001F339', 2),
    ('REGGAETON', 'Reggaetón', '\U0001F525', 3),
    ('URBANO', 'Urbano', '\U0001F3A4', 4),
    ('HEELS', 'Heels', '\U0001F460', 5),
    ('TANGO', 'Tango', '\U0001F3B6', 6),
    ('KIDS', 'Kids Dance', '\U0001F476', 7),
    ('PILATES', 'Pilates Mat', '\U0001F9D8', 8),
    ('BARRE', 'Barre', '\U0001FA70', 9),
    ('FLEXIBILIDAD', 'Flexibilidad', '\U0001F938', 10),
    ('REFORMER', 'Reformer', '\U0001F4AA', 11),
]

# Cuántas clases distintas cubre cada plan que ya existe.
CLASES_POR_PLAN = {
    '1 Curso': 1,
    '2 Cursos': 2,
    'Clase suelta': 1,
    # Pase Libre queda en nulo: es ilimitado.
}


def poblar(apps, schema_editor):
    Disciplina = apps.get_model('gestion', 'Disciplina')
    Clase = apps.get_model('gestion', 'Clase')
    Plan = apps.get_model('gestion', 'Plan')

    for codigo, nombre, emoji, orden in DISCIPLINAS:
        Disciplina.objects.get_or_create(
            nombre=nombre,
            defaults={'emoji': emoji, 'orden': orden},
        )
        # Las clases que usaban el código pasan a guardar el nombre.
        Clase.objects.filter(nombre=codigo).update(nombre=nombre)

    # Kids Dance era la única con edad de niños.
    Clase.objects.filter(nombre='Kids Dance').update(publico='KIDS')

    for nombre_plan, cuantas in CLASES_POR_PLAN.items():
        Plan.objects.filter(nombre=nombre_plan).update(clases_incluidas=cuantas)


def revertir(apps, schema_editor):
    """Vuelve a los códigos. El catálogo se queda: no estorba."""
    Clase = apps.get_model('gestion', 'Clase')
    for codigo, nombre, _, _ in DISCIPLINAS:
        Clase.objects.filter(nombre=nombre).update(nombre=codigo)


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0023_disciplina_remove_clase_edad_minima_clase_publico_and_more'),
    ]

    operations = [
        migrations.RunPython(poblar, revertir),
    ]
