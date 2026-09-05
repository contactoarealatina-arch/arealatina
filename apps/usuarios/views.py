"""Autenticación del sistema.

El freno a la fuerza bruta lo hace django-axes (configurado en settings):
bloquea la combinación IP + usuario tras 5 intentos fallidos, durante 15
minutos, y deja constancia en base de datos. Antes había un freno escrito
a mano; se reemplazó porque axes guarda los intentos de forma auditable y
es código revisado por mucha gente, cosa que importa cuando hay que
demostrar ante un tercero qué medidas se tomaron.

Tener el enlace de acceso a la vista no es una vulnerabilidad: la
dirección de un panel siempre se puede adivinar. Lo que protege de verdad
es que nadie pueda probar miles de contraseñas, y que los mensajes de
error no revelen qué cuentas existen.
"""
import logging

from django.contrib import messages
from django.contrib.auth import logout as cerrar_sesion
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

registro = logging.getLogger('arealatina.seguridad')

# Un único mensaje para todos los fallos. Decir "ese usuario no existe" le
# regala al atacante la mitad del trabajo: le confirma qué cuentas probar.
MENSAJE_GENERICO = 'Correo o contraseña incorrectos. Verifica tus datos.'


@method_decorator(never_cache, name='dispatch')
class LoginSeguro(auth_views.LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def form_invalid(self, form):
        # Se limpian los errores de campo para que el formulario no filtre
        # detalles ("este usuario no existe", "contraseña incorrecta").
        form.errors.clear()
        form.add_error(None, MENSAJE_GENERICO)

        registro.warning(
            'Intento de acceso fallido para "%s" desde %s',
            (self.request.POST.get('username') or '')[:60],
            _ip(self.request),
        )
        return super().form_invalid(form)

    def form_valid(self, form):
        respuesta = super().form_valid(form)

        # Sesión nueva al entrar: evita que una sesión anónima previa
        # quede asociada a la cuenta (fijación de sesión).
        self.request.session.cycle_key()

        registro.info('Acceso correcto de %s desde %s',
                      self.request.user.username, _ip(self.request))
        return respuesta

    def get_success_url(self):
        """Cada rol aterriza en su propio espacio."""
        siguiente = self.get_redirect_url()
        if siguiente:
            return siguiente

        usuario = self.request.user
        if usuario.puede_gestionar:
            return reverse('gestion:dashboard')
        if usuario.es_profesor:
            return reverse('profesoras:panel')
        return reverse('portal:panel')


@never_cache
def salir(request):
    """Cierre de sesión que no deja rastros reutilizables.

    logout() de Django ya borra la sesión del servidor, pero además se
    vacía explícitamente y se marca la respuesta como no cacheable: si no,
    el botón "atrás" del navegador puede mostrar la página anterior desde
    la caché aunque la sesión ya no exista.
    """
    if request.user.is_authenticated:
        registro.info('Cierre de sesión de %s desde %s',
                      request.user.username, _ip(request))
        request.session.flush()
        cerrar_sesion(request)
        messages.success(request, 'Cerraste sesión correctamente.')

    respuesta = redirect('usuarios:login')
    respuesta['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    respuesta['Pragma'] = 'no-cache'
    respuesta['Expires'] = '0'
    return respuesta


def _ip(request):
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR')
    if reenviada:
        return reenviada.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'desconocida')
