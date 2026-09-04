"""Mapa del sitio para los buscadores.

Se arma desde las URLs reales del proyecto y no desde un XML escrito a
mano: cuando se agrega una página, basta con sumarla a la lista de abajo
y el archivo se regenera solo, sin quedar desfasado.

Son seis URLs porque el sitio son tres páginas más el acceso al portal
y los dos documentos de privacidad. Si el sitio vuelve a crecer, se
agregan acá.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class PaginasSitemap(Sitemap):
    """Las páginas fijas del sitio público."""

    protocol = 'https'
    changefreq = 'weekly'

    # (nombre de la url, prioridad)
    PAGINAS = [
        ('web:index', 1.0),
        ('web:clases', 0.9),
        ('web:contacto', 0.7),
        ('web:mi_espacio', 0.4),
        ('web:privacidad', 0.2),
        ('web:mis_derechos', 0.2),
    ]

    def items(self):
        return self.PAGINAS

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]


SITEMAPS = {'paginas': PaginasSitemap}
