"""URLs raiz del proyecto Area Latina Estudio."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.web.urls')),
    path('cuentas/', include('apps.usuarios.urls')),
    path('gestion/', include('apps.gestion.urls')),
    path('asistencia/', include('apps.asistencia.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = 'Area Latina Estudio'
admin.site.site_title = 'Administracion | Area Latina'
admin.site.index_title = 'Panel de gestion'
