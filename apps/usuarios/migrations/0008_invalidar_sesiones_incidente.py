"""Cierra sesiones, bloquea la cuenta compartida y crea revisores separados."""
from django.contrib.auth.hashers import make_password
from django.db import migrations
from django.db.models import Q


CUENTAS_REVISION = (
    (
        'Sergio',
        'sergio@arealatinaestudio.cl',
        'pbkdf2_sha256$1000000$9aE3deO64prik2m8oDsOJs$58okjd9+6PlqYgzGe6+Jx5sFLpMTW5OLrpD9w7Js15A=',
    ),
    (
        'Katy',
        'katy@arealatinaestudio.cl',
        'pbkdf2_sha256$1000000$NpMdftwlzTi3Qk1qGBp0yI$yQPGFAZ0yv6e+RogAuwvsly9Tu5I2IM0vh9xYiFSVQo=',
    ),
)


def invalidar_sesiones(apps, schema_editor):
    Sesion = apps.get_model('sessions', 'Session')
    Usuario = apps.get_model('usuarios', 'CustomUser')
    Sesion.objects.all().delete()

    # La clave conocida deja de servir. La cuenta se conserva para mantener
    # intacta la auditoría histórica, pero ya no puede autenticarse.
    Usuario.objects.filter(
        Q(username__iexact='admin')
        | Q(username__iexact='arealatina310@gmail.com')
        | Q(email__iexact='arealatina310@gmail.com')
        | Q(correo_institucional__iexact='arealatina310@gmail.com')
    ).update(password=make_password(None))

    # Contraseñas temporales distintas y con cambio obligatorio. En el
    # repositorio solo quedan hashes PBKDF2; nunca las claves en texto claro.
    for nombre, identidad, password_hash in CUENTAS_REVISION:
        usuario = Usuario.objects.filter(
            Q(username__iexact=identidad)
            | Q(correo_institucional__iexact=identidad)
        ).first()
        nueva = usuario is None
        if nueva:
            usuario = Usuario(username=identidad)
        usuario.first_name = nombre
        usuario.email = identidad
        usuario.correo_institucional = identidad
        usuario.rol = 'SUPERADMIN'
        usuario.is_active = True
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.debe_cambiar_clave = True
        usuario.password = password_hash
        if nueva:
            usuario.save()
        else:
            usuario.save(update_fields=[
                'first_name', 'email', 'correo_institucional', 'rol', 'is_active',
                'is_staff', 'is_superuser', 'debe_cambiar_clave', 'password',
            ])


class Migration(migrations.Migration):
    dependencies = [
        ('sessions', '0001_initial'),
        ('usuarios', '0007_dominio_del_estudio'),
    ]

    operations = [
        migrations.RunPython(invalidar_sesiones, migrations.RunPython.noop),
    ]
