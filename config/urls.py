"""URLs raiz del proyecto Area Latina Estudio."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.shortcuts import render
from django.urls import include, path

from apps.web.sitemaps import SITEMAPS


def robots(request):
    """El robots.txt, leyendo el modo en cada visita.

    Se resuelve aca y no con extra_context porque ese diccionario se
    arma una sola vez al arrancar: si alguien apaga el modo privado, el
    robots seguiria diciendo "no entres" hasta el siguiente reinicio.
    """
    return render(request, 'robots.txt',
                  {'privado': settings.SITIO_PRIVADO},
                  content_type='text/plain')


urlpatterns = [
    path('admin/', admin.site.urls),

    # Buscadores
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS},
         name='django.contrib.sitemaps.views.sitemap'),
    # El robots cambia segun el modo: mientras el sitio sea privado le
    # dice al buscador que no entre a nada. Si se indexara ahora, en
    # Google quedarian guardadas paginas con datos de prueba.
    path('robots.txt', robots, name='robots'),

    path('', include('apps.web.urls')),
    path('cuentas/', include('apps.usuarios.urls')),
    path('gestion/', include('apps.gestion.urls')),
    path('profesoras/', include('apps.profesoras.urls')),
    path('portal/', include('apps.portal.urls')),
    path('asistencia/', include('apps.asistencia.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'Area Latina Estudio'
admin.site.site_title = 'Administracion | Area Latina'
admin.site.index_title = 'Panel de gestion'
