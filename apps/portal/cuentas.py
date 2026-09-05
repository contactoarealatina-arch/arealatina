"""Creación de las cuentas de acceso de alumnos y profesoras.

El alumno entra con su correo. La profesora, con el correo del estudio
(nombre.apellido@arealatina.cl); su correo personal solo sirve para
recibir mensajes, nunca para entrar.

Las dos cuentas nacen con una contraseña temporal que viaja por correo y
que el sistema obliga a cambiar en el primer acceso. Es lo que pidió el
estudio. La alternativa —un enlace de un solo uso— es más segura porque
la clave nunca se escribe en ninguna parte; acá se compensa con dos
cosas: la temporal es aleatoria y no sirve para nada hasta que la persona
elige la suya, porque el sistema no la deja moverse a otra pantalla.
"""
import re
import secrets
import unicodedata

from django.contrib.auth import get_user_model

from apps.gestion.models import TokenActivacion

Usuario = get_user_model()

# Sin caracteres que se confundan al copiarlos de un correo: nada de
# l/1/I ni O/0. Una clave temporal que se transcribe mal es una llamada
# al estudio preguntando por qué no entra.
ALFABETO = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
LARGO_CLAVE = 10


def _sin_tildes(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


def clave_temporal():
    """Una contraseña al azar, legible y de un solo uso en la práctica."""
    return ''.join(secrets.choice(ALFABETO) for _ in range(LARGO_CLAVE))


def sugerir_username(alumno):
    """nombre.apellido, y si ya existe le agrega un número.

    Queda como respaldo: hoy el alumno entra con su correo, pero si algún
    día se registra a alguien sin correo hace falta un identificador.
    """
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
    """Crea el usuario del alumno y devuelve (usuario, clave_temporal).

    El nombre de usuario ES su correo: entra con lo que ya sabe de
    memoria, no con un identificador que hay que enseñarle.

    Devuelve (None, None) si el alumno no tiene correo. Sin correo no hay
    a dónde mandarle la clave, así que la cuenta no serviría de nada.
    """
    if not alumno.email:
        return None, None

    correo = alumno.email.strip().lower()
    clave = clave_temporal()

    if alumno.usuario_id:
        usuario = alumno.usuario
        # Si le corrigieron el correo, su forma de entrar cambia con él.
        usuario.username = correo
        usuario.email = correo
    else:
        usuario = Usuario(
            username=correo,
            email=correo,
            first_name=alumno.primer_nombre,
            last_name=' '.join(alumno.nombre_completo.split()[1:]),
            rol=Usuario.Rol.ALUMNO,
            rut=alumno.rut or None,
        )

    usuario.set_password(clave)
    usuario.debe_cambiar_clave = True
    usuario.save()

    if not alumno.usuario_id:
        alumno.usuario = usuario
        alumno.save(update_fields=['usuario', 'updated_at'])

    # Los enlaces de activación que quedaran sin usar dejan de servir:
    # la forma de entrar ahora es la clave nueva.
    TokenActivacion.objects.filter(usuario=usuario, usado_en__isnull=True).delete()

    return usuario, clave


def crear_acceso_profesora(profesora, con_clave_temporal=True):
    """Le pone clave temporal a la profesora y la devuelve.

    Devuelve None si la administración ya le escribió una contraseña a
    mano: en ese caso no hay nada que generar ni que mandar.
    """
    if not con_clave_temporal:
        return None

    clave = clave_temporal()
    profesora.set_password(clave)
    profesora.debe_cambiar_clave = True
    profesora.save(update_fields=['password', 'debe_cambiar_clave', 'updated_at'])

    TokenActivacion.objects.filter(
        usuario=profesora, usado_en__isnull=True,
    ).delete()

    return clave
