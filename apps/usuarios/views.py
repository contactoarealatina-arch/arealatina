"""Autenticación con freno a los intentos de fuerza bruta.

Tener el link de acceso a la vista no es una vulnerabilidad: la dirección
de un panel siempre se puede adivinar (/admin, /login, /gestion). Lo que
protege de verdad es que alguien no pueda probar miles de contraseñas.

Esta vista bloquea temporalmente después de varios intentos fallidos,
contando por IP y por nombre de usuario a la vez:

- Por usuario: frena a quien ataca una cuenta concreta desde muchas IP.
- Por IP: frena a quien prueba muchos usuarios desde un solo lugar.

El mensaje de error nunca dice si el usuario existe o no. Decirlo le
regala al atacante la mitad del trabajo.
"""
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.core.cache import cache
from django.shortcuts import render
from django.utils import timezone

MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 15 * 60


def _ip(request):
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR')
    if reenviada:
        return reenviada.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'desconocida')


def _claves(request):
    usuario = (request.POST.get('username') or '').strip().lower()[:80]
    return [f'login:ip:{_ip(request)}'] + ([f'login:usr:{usuario}'] if usuario else [])


class LoginSeguro(auth_views.LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def post(self, request, *args, **kwargs):
        bloqueo = self._bloqueo_restante(request)
        if bloqueo:
            minutos = max(1, round(bloqueo / 60))
            return render(request, self.template_name, {
                'form': self.get_form(),
                'bloqueado': True,
                'minutos': minutos,
            }, status=429)
        return super().post(request, *args, **kwargs)

    # ------------------------------------------------------------------
    def _bloqueo_restante(self, request):
        """Segundos que faltan para poder reintentar. 0 si no está bloqueado."""
        for clave in _claves(request):
            datos = cache.get(clave)
            if datos and datos['intentos'] >= MAX_INTENTOS:
                restante = (datos['hasta'] - timezone.now()).total_seconds()
                if restante > 0:
                    return restante
                cache.delete(clave)
        return 0

    def form_invalid(self, form):
        for clave in _claves(self.request):
            datos = cache.get(clave) or {'intentos': 0, 'hasta': None}
            datos['intentos'] += 1
            datos['hasta'] = timezone.now() + timezone.timedelta(seconds=BLOQUEO_SEGUNDOS)
            cache.set(clave, datos, BLOQUEO_SEGUNDOS)

        restantes = MAX_INTENTOS - (cache.get(_claves(self.request)[0]) or {}).get('intentos', 0)
        if 0 < restantes <= 2:
            messages.warning(
                self.request,
                f'Te quedan {restantes} intento{"s" if restantes != 1 else ""} '
                'antes de que se bloquee el acceso por 15 minutos.'
            )
        return super().form_invalid(form)

    def form_valid(self, form):
        # Entró bien: se limpia el contador.
        for clave in _claves(self.request):
            cache.delete(clave)

        respuesta = super().form_valid(form)

        # Queda registrado quién entró y desde dónde.
        from apps.gestion.auditoria import registrar
        from apps.gestion.models import AuditLog
        registrar(self.request, AuditLog.Accion.LOGIN, self.request.user,
                  f'Inició sesión {self.request.user.username}',
                  modelo='CustomUser')

        return respuesta

    def get_success_url(self):
        """Cada rol aterriza en su propio espacio."""
        from django.urls import reverse

        # Si venía de una página protegida, se respeta ese destino.
        siguiente = self.get_redirect_url()
        if siguiente:
            return siguiente

        usuario = self.request.user

        if usuario.puede_gestionar:
            return reverse('gestion:dashboard')
        if usuario.es_profesor:
            return reverse('profesoras:panel')
        return reverse('portal:panel')
