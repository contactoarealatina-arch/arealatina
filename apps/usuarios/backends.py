"""Entrar con el correo además de con el nombre de usuario.

El estudio quiere que las profesoras entren con su correo del estudio
(camila.soto@arealatina.cl) y no con un nombre de usuario que hay que
recordar aparte. Los alumnos y el equipo siguen entrando como siempre.

Va como backend y no como un cambio en el formulario para que valga en
todas las puertas: el login del sitio, el del portal y el del admin.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class CorreoOUsuarioBackend(ModelBackend):
    """Acepta el correo (o el nombre de usuario, para cuentas antiguas)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        Usuario = get_user_model()
        entrada = (username or kwargs.get(Usuario.USERNAME_FIELD) or '').strip()
        if not entrada or password is None:
            return None

        # Se buscan todas las coincidencias y solo se acepta si hay una.
        # Con dos usuarios que comparten correo no se puede saber cuál es,
        # y elegir "el primero" sería dejar entrar a la persona equivocada.
        # La profesora entra SOLO con el correo del estudio. Su correo
        # personal es para recibir mensajes, no para autenticarse: si
        # sirviera para entrar, darla de baja cambiando el del estudio no
        # cerraria nada.
        es_profesora = Q(rol=Usuario.Rol.PROFESOR)
        candidatos = list(
            Usuario.objects.filter(
                Q(username__iexact=entrada)
                | Q(correo_institucional__iexact=entrada)
                | (Q(email__iexact=entrada) & ~es_profesora)
            )[:2]
        )
        if len(candidatos) != 1:
            # Se calcula el hash igual aunque no haya usuario: si no, el
            # tiempo de respuesta delata qué correos existen.
            Usuario().set_password(password)
            return None

        usuario = candidatos[0]
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
