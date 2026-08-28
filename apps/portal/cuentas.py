"""Creación de las cuentas de acceso de los alumnos.

Un alumno no nace con contraseña: se le crea el usuario sin clave utilizable
y se le manda un enlace de un solo uso para que la elija él. Así nadie más
que él conoce su contraseña, ni siquiera la administración.
"""
import re
import unicodedata

from django.contrib.auth import get_user_model

from apps.gestion.models import TokenActivacion

Usuario = get_user_model()


def _sin_tildes(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


def sugerir_username(alumno):
    """nombre.apellido, y si ya existe le agrega un número."""
    partes = _sin_tildes(alumno.nombre_completo).lower().split()
    if len(partes) >= 2:
        base = f'{partes[0]}.{partes[-1]}'
    elif partes:
        base = partes[0]
    else:
        base = 'alumno'

    base = re.sub(r'[^a-z0-9._]', '', base)[:26] or 'alumno'

    candidato = base
    contador = 2
    while Usuario.objects.filter(username=candidato).exists():
        candidato = f'{base}{contador}'
        contador += 1
    return candidato


def crear_acceso(alumno):
    """Crea (o reutiliza) el usuario del alumno y devuelve (usuario, token).

    Devuelve (None, None) si el alumno no tiene email: sin correo no hay
    forma de mandarle el enlace, así que la cuenta no tendría sentido.
    """
    if not alumno.email:
        return None, None

    if alumno.usuario_id:
        usuario = alumno.usuario
    else:
        usuario = Usuario.objects.create(
            username=sugerir_username(alumno),
            email=alumno.email,
            first_name=alumno.primer_nombre,
            last_name=' '.join(alumno.nombre_completo.split()[1:]),
            rol=Usuario.Rol.ALUMNO,
            rut=alumno.rut or None,
        )
        # Sin contraseña utilizable: solo se puede entrar tras activar.
        usuario.set_unusable_password()
        usuario.save()

        alumno.usuario = usuario
        alumno.save(update_fields=['usuario', 'updated_at'])

    return usuario, TokenActivacion.crear_para(usuario)


def crear_acceso_profesora(profesora, con_token):
    """Token de activación para una profesora recién creada."""
    if not con_token or not profesora.email:
        return None
    profesora.set_unusable_password()
    profesora.save(update_fields=['password'])
    return TokenActivacion.crear_para(profesora)
