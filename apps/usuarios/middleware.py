"""Obliga a cambiar la contraseña temporal antes de usar el sistema.

Va como middleware y no como decorador en cada vista porque tiene que
valer en las tres puertas —panel, portal de profesoras y portal de
alumnos— y en cualquier URL que alguien escriba a mano. Un decorador que
falte en una sola vista deja la puerta abierta.
"""
from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.utils.cache import patch_cache_control


class NoCachePrivado:
    """Prohíbe guardar respuestas autenticadas o de paneles privados.

    Esto cubre también respuestas de error y redirecciones. Al cerrar sesión,
    el botón Atrás no debe poder reconstruir la ficha de otra persona desde la
    caché del navegador o de un proxy intermedio.
    """

    PREFIJOS_PRIVADOS = ('/admin/', '/gestion/', '/portal/', '/profesoras/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        usuario = getattr(request, 'user', None)
        es_privada = (
            bool(usuario is not None and usuario.is_authenticated)
            or request.path.startswith(self.PREFIJOS_PRIVADOS)
        )
        if es_privada:
            patch_cache_control(
                response,
                private=True,
                no_cache=True,
                no_store=True,
                must_revalidate=True,
                max_age=0,
            )
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response


class CambioDeClaveObligatorio:
    """Redirige a cambiar la clave mientras la temporal siga en pie."""

    # Lo único que puede hacer alguien con clave temporal: cambiarla,
    # salir, o pedir ayuda. Todo lo demás espera.
    PERMITIDAS = {
        'usuarios:logout',
        'usuarios:login',
        'portal:login',
        'portal:cambiar_clave',
        'web:contacto',
        'web:privacidad',
        'web:mis_derechos',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, 'user', None)

        if (usuario is not None
                and usuario.is_authenticated
                and getattr(usuario, 'debe_cambiar_clave', False)
                and not self._esta_permitida(request)):
            return redirect('portal:cambiar_clave')

        return self.get_response(request)

    def _esta_permitida(self, request):
        # Los estáticos quedan fuera. El admin también se bloquea mientras
        # la clave sea temporal; de otro modo un superadministrador podría
        # saltarse el cambio obligatorio entrando directo por /admin/.
        ruta = request.path
        if ruta.startswith(('/static/', '/media/')):
            return True

        try:
            coincidencia = resolve(ruta)
        except Exception:
            return True

        nombre = f'{coincidencia.namespace}:{coincidencia.url_name}' \
            if coincidencia.namespace else (coincidencia.url_name or '')
        return nombre in self.PERMITIDAS
