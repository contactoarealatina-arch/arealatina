"""Carga datos de ejemplo para probar el sitio y el panel.

Uso:  python manage.py datos_demo
"""
from datetime import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.gestion.models import Clase, Plan

User = get_user_model()

PROFESORAS = [
    ('camila', 'Camila', 'Soto'),
    ('daniela', 'Daniela', 'Ruiz'),
    ('matias', 'Matias', 'Vera'),
]

PLANES = [
    ('Plan 1 vez por semana', 25000, 30, 'Una clase semanal del estilo que elijas.'),
    ('Plan 2 veces por semana', 38000, 30, 'Dos clases semanales, mismo o distinto estilo.'),
    ('Plan libre', 50000, 30, 'Acceso a todas las clases del horario regular.'),
    ('Clase suelta', 6000, 1, 'Una clase puntual, ideal para probar.'),
]

CLASES = [
    ('SALSA', 'INICIAL', 'Lunes y Miercoles', time(19, 0), time(20, 0), 'Sala 1', 20, 0),
    ('SALSA', 'INTERMEDIO', 'Lunes y Miercoles', time(20, 0), time(21, 0), 'Sala 1', 20, 0),
    ('BACHATA', 'TODOS', 'Martes y Jueves', time(19, 30), time(20, 30), 'Sala 1', 20, 0),
    ('REGGAETON', 'TODOS', 'Miercoles y Viernes', time(20, 0), time(21, 0), 'Sala 2', 25, 1),
    ('URBANO', 'INICIAL', 'Viernes', time(18, 30), time(19, 30), 'Sala 2', 25, 1),
    ('TANGO', 'TODOS', 'Jueves', time(21, 0), time(22, 0), 'Sala 1', 16, 2),
    ('KIDS', 'INICIAL', 'Sabado', time(11, 0), time(12, 0), 'Sala 2', 18, 1),
]


class Command(BaseCommand):
    help = 'Crea planes, profesoras y clases de ejemplo.'

    def handle(self, *args, **options):
        profes = []
        for username, nombre, apellido in PROFESORAS:
            profe, creado = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': nombre,
                    'last_name': apellido,
                    'rol': User.Rol.PROFESOR,
                    'email': f'{username}@arealatinaestudio.cl',
                },
            )
            if creado:
                profe.set_password('arealatina2025')
                profe.save()
            profes.append(profe)
        self.stdout.write(self.style.SUCCESS(f'Profesoras: {len(profes)}'))

        for nombre, precio, dias, descripcion in PLANES:
            Plan.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'precio_clp': precio,
                    'duracion_dias': dias,
                    'descripcion': descripcion,
                },
            )
        self.stdout.write(self.style.SUCCESS(f'Planes: {Plan.objects.count()}'))

        for estilo, nivel, dias, inicio, fin, sala, cupo, idx_profe in CLASES:
            Clase.objects.get_or_create(
                nombre=estilo,
                nivel=nivel,
                dias_semana=dias,
                hora_inicio=inicio,
                defaults={
                    'hora_fin': fin,
                    'sala': sala,
                    'cupo_maximo': cupo,
                    'profesora': profes[idx_profe],
                    'activa': True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f'Clases: {Clase.objects.count()}'))
        self.stdout.write(self.style.SUCCESS('Datos de ejemplo cargados.'))
