"""Elimina alumnos ficticios y bloquea accesos demo con clave conocida."""
from django.contrib.auth.hashers import check_password, make_password
from django.db import migrations


RUTS_DEMO = (
    '90.000.000-6', '90.000.001-4', '90.000.002-2', '90.000.003-0',
    '90.000.004-9', '90.000.005-7', '90.000.006-5', '90.000.007-3',
    '90.000.008-1', '90.000.009-K', '90.000.010-3', '90.000.011-1',
)
USUARIOS_PROFESOR_DEMO = ('camila', 'daniela', 'matias')
CLAVE_DEMO_CONOCIDA = 'arealatina2025'


def limpiar_demo(apps, schema_editor):
    Alumno = apps.get_model('gestion', 'Alumno')
    Usuario = apps.get_model('usuarios', 'CustomUser')

    # Coincidencia exacta con los doce RUT generados por datos_demo. No se usa
    # un prefijo amplio para no arriesgar un registro agregado manualmente.
    alumnos = Alumno.objects.filter(rut__in=RUTS_DEMO)
    usuarios_alumno = list(
        alumnos.exclude(usuario_id=None).values_list('usuario_id', flat=True)
    )

    # Las relaciones ficticias (pagos, asistencia, inscripciones, alertas y
    # suscripciones) usan CASCADE y desaparecen junto con estos alumnos.
    alumnos.delete()

    # Solo se eliminan accesos no privilegiados vinculados a los alumnos demo
    # y creados con el dominio ficticio del generador.
    Usuario.objects.filter(
        pk__in=usuarios_alumno,
        rol='ALUMNO',
        is_staff=False,
        is_superuser=False,
        email__iendswith='@ejemplo.cl',
    ).delete()

    # El generador antiguo dejó una contraseña conocida en el repositorio.
    # Se bloquea únicamente la cuenta que todavía conserve exactamente esa
    # clave; una cuenta cuya clave fue cambiada no se modifica.
    for usuario in Usuario.objects.filter(username__in=USUARIOS_PROFESOR_DEMO):
        if check_password(CLAVE_DEMO_CONOCIDA, usuario.password):
            usuario.password = make_password(None)
            usuario.is_active = False
            usuario.save(update_fields=['password', 'is_active'])


class Migration(migrations.Migration):
    dependencies = [
        ('gestion', '0026_alter_correoenviado_tipo'),
        ('usuarios', '0009_renombrar_katy_a_katherine'),
    ]

    operations = [
        migrations.RunPython(limpiar_demo, migrations.RunPython.noop),
    ]
