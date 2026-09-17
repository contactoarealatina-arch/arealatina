"""Mantiene el sitio fuera de la vista publica mientras se revisa."""
from django.conf import settings
from django.shortcuts import render
from django.urls import resolve


class SitioPrivado:
    """Deja pasar a usuarios autenticados o navegadores con PIN valido."""

    SESION_REVISION = 'sitio_revision_autorizada'

    # Las puertas quedan abiertas: si se cerraran, nadie del estudio
    # podria entrar a probar, que es justo para lo que esta arriba.
    PERMITIDAS = {
        'usuarios:login',
        'usuarios:logout',
        'portal:login',
        'portal:activar',
        'portal:token_expirado',
        'web:revision',
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
            return render(
                request,
                'web/privado.html',
                {'next': request.get_full_path()},
                status=503,
            )

        return self.get_response(request)

    def _hay_que_tapar(self, request):
        if not getattr(settings, 'SITIO_PRIVADO', False):
            return False

        usuario = getattr(request, 'user', None)
        if usuario is not None and usuario.is_authenticated:
            return False

        # El PIN no inicia una cuenta ni abre los paneles: solo permite que
        # este navegador recorra la web para revisarla antes de publicarla.
        if request.session.get(self.SESION_REVISION, False):
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


class ContadorVisitas:
    """Cuenta visitas al sitio público, una fila por día.

    Google Analytics es la fuente buena para analizar tráfico; esto es
    otra cosa. Existe para que el sistema pueda avisar solo cuando algo
    se sale de lo normal sin depender de la API de Google, que es una
    pieza más que se puede caer, y sin depender tampoco de que el
    visitante haya aceptado la medición: acá no se guarda nada de la
    persona, solo cuántas páginas se pidieron ese día.
    """

    SESION_REVISION = SitioPrivado.SESION_REVISION

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        respuesta = self.get_response(request)

        try:
            if self._hay_que_contar(request, respuesta):
                self._sumar(request)
        except Exception:
            # Contar visitas jamás puede voltear una página. Si la tabla
            # no existe todavía o la base va lenta, se pierde el conteo
            # de esa visita y no pasa nada más.
            pass

        return respuesta

    def _hay_que_contar(self, request, respuesta):
        if request.method != 'GET' or respuesta.status_code != 200:
            return False

        # El equipo entrando a mirar su propio sitio no es tráfico.
        usuario = getattr(request, 'user', None)
        if usuario is not None and usuario.is_authenticated:
            return False

        # El PIN no inicia una cuenta ni abre los paneles: solo permite que
        # este navegador recorra la web para revisarla antes de publicarla.
        if request.session.get(self.SESION_REVISION, False):
            return False

        coincidencia = getattr(request, 'resolver_match', None)
        return bool(coincidencia) and coincidencia.namespace == 'web'

    def _sumar(self, request):
        from django.db.models import F
        from django.utils import timezone

        from apps.gestion.models import EstadisticaDiaria

        hoy = timezone.localdate()
        fila, creada = EstadisticaDiaria.objects.get_or_create(fecha=hoy)

        # F() y no fila.visitas += 1: dos visitas al mismo tiempo leerían
        # el mismo número y una pisaría a la otra. Con F() la suma la
        # hace la base de datos.
        campos = {'visitas_estimadas': F('visitas_estimadas') + 1}

        coincidencia = request.resolver_match
        if coincidencia.url_name == 'contacto' and request.GET.get('enviado'):
            campos['formularios_contacto_enviados'] = (
                F('formularios_contacto_enviados') + 1)

        EstadisticaDiaria.objects.filter(pk=fila.pk).update(**campos)
