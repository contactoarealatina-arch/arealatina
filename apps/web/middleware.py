"""El sitio arriba, pero todavia no a la vista de todos.

Mientras el estudio prueba el sistema, la direccion ya existe y responde,
pero no corresponde que un vecino que la escriba por casualidad vea una
academia a medio llenar con alumnos de prueba adentro.

Va como middleware y no como una vista de "en construccion" porque tiene
que tapar TODO —las tres puertas, el sitio publico, el sitio de mapas—
con una sola variable. Apagarlo es cambiar SITIO_PRIVADO a False en
Railway: no hay que tocar codigo ni volver a desplegar.
"""
from django.conf import settings
from django.shortcuts import render
from django.urls import resolve


class SitioPrivado:
    """Le muestra el sitio solo a quien tenga cuenta."""

    # Las puertas quedan abiertas: si se cerraran, nadie del estudio
    # podria entrar a probar, que es justo para lo que esta arriba.
    PERMITIDAS = {
        'usuarios:login',
        'usuarios:logout',
        'portal:login',
        'portal:activar',
        'portal:token_expirado',
        'robots',
    }

    # El admin de Django se deja pasar entero: es la salida de emergencia
    # si algo del sitio propio queda trancado.
    PREFIJOS = ('/static/', '/media/', '/admin/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._hay_que_tapar(request):
            # 503 y no 404: le dice al buscador "vuelve despues, esto no
            # es una pagina que no existe". Con 404 podria darla de baja
            # de su indice y despues costaria recuperar la posicion.
            return render(request, 'web/privado.html', status=503)

        return self.get_response(request)

    def _hay_que_tapar(self, request):
        if not getattr(settings, 'SITIO_PRIVADO', False):
            return False

        usuario = getattr(request, 'user', None)
        if usuario is not None and usuario.is_authenticated:
            return False

        if request.path.startswith(self.PREFIJOS):
            return False

        try:
            coincidencia = resolve(request.path)
        except Exception:
            # Una URL que no existe tampoco tiene por que verse.
            return True

        nombre = (f'{coincidencia.namespace}:{coincidencia.url_name}'
                  if coincidencia.namespace else (coincidencia.url_name or ''))
        return nombre not in self.PERMITIDAS
