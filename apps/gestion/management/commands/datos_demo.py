"""Carga datos de ejemplo para probar el sitio y el panel.

Uso:
    python manage.py datos_demo                 planes, profesoras y clases
    python manage.py datos_demo --con-alumnos   agrega alumnos y pagos de prueba
    python manage.py datos_demo --borrar-demo   borra SOLO los alumnos de prueba

Los alumnos de prueba se reconocen por su RUT: todos empiezan en 90.xxx.xxx,
un rango que no existe en la realidad, así que nunca se confunden con datos
verdaderos de la academia.
"""
import random
from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.asistencia.models import RegistroAsistencia
from apps.gestion.models import Alumno, Clase, Inscripcion, Pago, Plan, Suscripcion

User = get_user_model()

PREFIJO_DEMO = '90.'

PROFESORAS = [
    ('camila', 'Camila', 'Soto', 'Salsa y Bachata'),
    ('daniela', 'Daniela', 'Ruiz', 'Reggaetón y Urbano'),
    ('matias', 'Matías', 'Vera', 'Tango'),
]

PLANES = [
    ('Plan 1 vez por semana', 25000, 30, 'Una clase semanal del estilo que elijas.'),
    ('Plan 2 veces por semana', 38000, 30, 'Dos clases semanales, mismo o distinto estilo.'),
    ('Plan libre', 50000, 30, 'Acceso a todas las clases del horario regular.'),
    ('Clase suelta', 6000, 1, 'Una clase puntual, ideal para probar.'),
]

CLASES = [
    ('SALSA', 'INICIAL', 'LU,MI', time(19, 0), time(20, 0), 'Sala 1', 20, 0),
    ('SALSA', 'INTERMEDIO', 'LU,MI', time(20, 0), time(21, 0), 'Sala 1', 20, 0),
    ('BACHATA', 'TODOS', 'MA,JU', time(19, 30), time(20, 30), 'Sala 1', 20, 0),
    ('REGGAETON', 'TODOS', 'MI,VI', time(20, 0), time(21, 0), 'Sala 2', 25, 1),
    ('URBANO', 'INICIAL', 'VI', time(18, 30), time(19, 30), 'Sala 2', 25, 1),
    ('TANGO', 'TODOS', 'JU', time(21, 0), time(22, 0), 'Sala 1', 16, 2),
    ('KIDS', 'INICIAL', 'SA', time(11, 0), time(12, 0), 'Sala 2', 18, 1),
]

NOMBRES_DEMO = [
    'Valentina Muñoz', 'Sebastián Rojas', 'Antonia Fuentes', 'Benjamín Cárdenas',
    'Josefa Aguilar', 'Martín Oyarzún', 'Catalina Barría', 'Vicente Millán',
    'Isidora Paredes', 'Tomás Alvarado', 'Emilia Contreras', 'Agustín Bahamonde',
]


def rut_demo(indice):
    """RUT del rango 90.000.000 con dígito verificador válido."""
    cuerpo = 90000000 + indice
    suma, multiplo = 0, 2
    for digito in reversed(str(cuerpo)):
        suma += int(digito) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1
    resto = 11 - (suma % 11)
    dv = '0' if resto == 11 else 'K' if resto == 10 else str(resto)
    return f'{cuerpo:,}'.replace(',', '.') + f'-{dv}'


class Command(BaseCommand):
    help = 'Crea planes, profesoras y clases de ejemplo.'

    def add_arguments(self, parser):
        parser.add_argument('--con-alumnos', action='store_true',
                            help='Agrega alumnos, suscripciones y pagos de prueba.')
        parser.add_argument('--borrar-demo', action='store_true',
                            help='Borra solo los alumnos de prueba (RUT 90.xxx.xxx).')

    def handle(self, *args, **options):
        if options['borrar_demo']:
            return self.borrar_demo()

        profes = self.crear_profesoras()
        self.crear_planes()
        self.crear_clases(profes)

        if options['con_alumnos']:
            self.crear_alumnos()

        self.stdout.write(self.style.SUCCESS('Datos de ejemplo cargados.'))

    # ------------------------------------------------------------------
    def crear_profesoras(self):
        profes = []
        for username, nombre, apellido, especialidad in PROFESORAS:
            profe, creado = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': nombre,
                    'last_name': apellido,
                    'rol': User.Rol.PROFESOR,
                    'especialidad': especialidad,
                    'email': f'{username}@arealatinaestudio.cl',
                },
            )
            if creado:
                profe.set_password('arealatina2025')
                profe.save()
            elif not profe.especialidad:
                profe.especialidad = especialidad
                profe.save(update_fields=['especialidad'])
            profes.append(profe)
        self.stdout.write(self.style.SUCCESS(f'Profesoras: {len(profes)}'))
        return profes

    def crear_planes(self):
        for nombre, precio, dias, descripcion in PLANES:
            Plan.objects.get_or_create(
                nombre=nombre,
                defaults={'precio_clp': precio, 'duracion_dias': dias,
                          'descripcion': descripcion},
            )
        self.stdout.write(self.style.SUCCESS(f'Planes: {Plan.objects.count()}'))

    def crear_clases(self, profes):
        for estilo, nivel, dias, inicio, fin, sala, cupo, idx in CLASES:
            Clase.objects.get_or_create(
                nombre=estilo, nivel=nivel, dias_semana=dias, hora_inicio=inicio,
                defaults={'hora_fin': fin, 'sala': sala, 'cupo_maximo': cupo,
                          'profesora': profes[idx], 'activa': True},
            )
        self.stdout.write(self.style.SUCCESS(f'Clases: {Clase.objects.count()}'))

    # ------------------------------------------------------------------
    def crear_alumnos(self):
        """Genera alumnos repartidos en los cuatro estados de pago posibles."""
        random.seed(7)  # Mismos datos en cada corrida: facilita comparar.
        hoy = timezone.localdate()
        clases = list(Clase.objects.filter(activa=True))
        planes = list(Plan.objects.filter(activo=True, duracion_dias__gt=1))

        if not clases or not planes:
            self.stdout.write(self.style.WARNING('Faltan clases o planes.'))
            return

        creados = 0
        for indice, nombre in enumerate(NOMBRES_DEMO):
            rut = rut_demo(indice)
            if Alumno.todos.filter(rut=rut).exists():
                continue

            alumno = Alumno.objects.create(
                nombre_completo=nombre,
                rut=rut,
                fecha_nacimiento=hoy - timedelta(days=random.randint(2500, 14000)),
                genero=random.choice(['M', 'F', 'N']),
                telefono=f'+56 9 {random.randint(3000, 9999)} {random.randint(1000, 9999)}',
                email=f'{nombre.split()[0].lower()}{indice}@ejemplo.cl',
                direccion='Puerto Montt',
                contacto_emergencia=f'Familiar de {nombre.split()[0]}',
                telefono_emergencia=f'+56 9 {random.randint(3000, 9999)} {random.randint(1000, 9999)}',
                relacion_emergencia=random.choice(['MADRE', 'PADRE', 'PAREJA', 'OTRO']),
                fecha_ingreso=hoy - timedelta(days=random.randint(5, 400)),
                estado='SUSPENDIDO' if indice == 11 else 'ACTIVO',
            )

            for clase in random.sample(clases, random.randint(1, 2)):
                Inscripcion.objects.get_or_create(alumno=alumno, clase=clase)

            # Cuatro grupos: al día, por vencer, vencido y sin plan.
            grupo = indice % 4
            if grupo == 3:
                creados += 1
                continue

            plan = random.choice(planes)
            if grupo == 0:      # al día
                inicio = hoy - timedelta(days=random.randint(1, 8))
            elif grupo == 1:    # vence dentro de la semana
                inicio = hoy - timedelta(days=plan.duracion_dias - random.randint(1, 6))
            else:               # vencido
                inicio = hoy - timedelta(days=plan.duracion_dias + random.randint(3, 30))

            suscripcion = Suscripcion.objects.create(
                alumno=alumno, plan=plan, fecha_inicio=inicio
            )
            if suscripcion.fecha_vencimiento < hoy:
                suscripcion.estado = Suscripcion.Estado.VENCIDA
                suscripcion.save(update_fields=['estado'])

            Pago.objects.create(
                alumno=alumno, suscripcion=suscripcion,
                concepto=Pago.Concepto.MENSUALIDAD,
                monto_clp=plan.precio_clp,
                metodo=random.choice(['EFECTIVO', 'TRANSFERENCIA']),
                fecha_pago=inicio,
                estado=Pago.Estado.PAGADO,
            )

            # Un poco de historial para que los gráficos no salgan planos.
            for atras in (1, 2, 3):
                Pago.objects.create(
                    alumno=alumno,
                    concepto=Pago.Concepto.MENSUALIDAD,
                    monto_clp=plan.precio_clp,
                    metodo=random.choice(['EFECTIVO', 'TRANSFERENCIA']),
                    fecha_pago=inicio - timedelta(days=30 * atras),
                    estado=Pago.Estado.PAGADO,
                )

            if indice == 0:
                Pago.objects.create(
                    alumno=alumno, concepto=Pago.Concepto.MATRICULA,
                    monto_clp=15000, metodo='EFECTIVO',
                    fecha_pago=alumno.fecha_ingreso, estado=Pago.Estado.PAGADO,
                )

            creados += 1

        self.crear_asistencia()
        self.stdout.write(self.style.SUCCESS(f'Alumnos de prueba: {creados}'))

    def crear_asistencia(self):
        """Marca asistencia de las últimas cuatro semanas."""
        hoy = timezone.localdate()
        creadas = 0
        for clase in Clase.objects.filter(activa=True):
            inscritos = list(clase.inscripciones.all())
            if not inscritos:
                continue
            for semana in range(4):
                fecha = hoy - timedelta(days=7 * semana + 1)
                for inscripcion in inscritos:
                    estado = random.choices(
                        ['PRESENTE', 'AUSENTE', 'JUSTIFICADO'],
                        weights=[78, 15, 7],
                    )[0]
                    _, creado = RegistroAsistencia.objects.get_or_create(
                        clase=clase, alumno=inscripcion.alumno, fecha=fecha,
                        defaults={'estado': estado},
                    )
                    creadas += int(creado)
        self.stdout.write(self.style.SUCCESS(f'Marcas de asistencia: {creadas}'))

    # ------------------------------------------------------------------
    def borrar_demo(self):
        """Borra de verdad (no lógico) solo los alumnos del rango de prueba."""
        demo = Alumno.todos.filter(rut__startswith=PREFIJO_DEMO)
        cantidad = demo.count()
        demo.delete()
        self.stdout.write(self.style.SUCCESS(
            f'Alumnos de prueba borrados: {cantidad}. '
            'Planes, clases y profesoras quedaron intactos.'
        ))
