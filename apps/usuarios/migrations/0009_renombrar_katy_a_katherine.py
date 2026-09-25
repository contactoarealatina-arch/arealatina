"""Cambia la identidad de revisión de Katy a Katherine sin perder permisos."""
from django.contrib.auth.hashers import make_password
from django.db import migrations
from django.db.models import Q


ANTIGUA = 'katy@arealatinaestudio.cl'
NUEVA = 'katherine@arealatinaestudio.cl'


def renombrar_cuenta(apps, schema_editor):
    Usuario = apps.get_model('usuarios', 'CustomUser')

    antigua = Usuario.objects.filter(
        Q(username__iexact=ANTIGUA)
        | Q(email__iexact=ANTIGUA)
        | Q(correo_institucional__iexact=ANTIGUA)
    ).first()
    nueva = Usuario.objects.filter(
        Q(username__iexact=NUEVA)
        | Q(email__iexact=NUEVA)
        | Q(correo_institucional__iexact=NUEVA)
    ).first()

    # Si alguien creó Katherine manualmente antes de desplegar, se conserva
    # esa cuenta y se desactiva la identidad antigua para evitar duplicados.
    if antigua and nueva and antigua.pk != nueva.pk:
        antigua.correo_institucional = None
        antigua.is_active = False
        antigua.is_staff = False
        antigua.is_superuser = False
        antigua.save(update_fields=[
            'correo_institucional', 'is_active', 'is_staff', 'is_superuser',
        ])
        cuenta = nueva
    else:
        cuenta = nueva or antigua

    # La migración 0008 siempre crea la cuenta. Este resguardo permite aplicar
    # la corrección también si alguien la eliminó manualmente entre despliegues.
    if cuenta is None:
        cuenta = Usuario(username=NUEVA)
        cuenta.password = make_password(None)

    cuenta.username = NUEVA
    cuenta.email = NUEVA
    cuenta.correo_institucional = NUEVA
    cuenta.first_name = 'Katherine'
    cuenta.rol = 'SUPERADMIN'
    cuenta.is_active = True
    cuenta.is_staff = True
    cuenta.is_superuser = True
    cuenta.debe_cambiar_clave = True
    cuenta.save()


class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0008_invalidar_sesiones_incidente'),
    ]

    operations = [
        migrations.RunPython(renombrar_cuenta, migrations.RunPython.noop),
    ]
