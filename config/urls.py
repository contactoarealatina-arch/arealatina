"""URLs raiz del proyecto Area Latina Estudio."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from apps.web.sitemaps import SITEMAPS

urlpatterns = [
    path('admin/', admin.site.urls),

    # Buscadores
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS},
         name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(
        template_name='robots.txt', content_type='text/plain'), name='robots'),

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
