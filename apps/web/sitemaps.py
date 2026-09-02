"""Mapa del sitio para los buscadores.

Se arma desde las URLs reales del proyecto y no desde un XML escrito a
mano: cuando se agrega una página, basta con sumarla a la lista de abajo
y el archivo se regenera solo, sin quedar desfasado.

Los eventos no van acá: todavía no tienen página propia y todos
apuntarían a /en-escena/ o /comunidad/, es decir, URLs repetidas. Cuando
exista el detalle de cada evento, se agrega un Sitemap para ellos.
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
        ('web:planes', 0.9),
        ('web:wellness', 0.8),
        ('web:en_escena', 0.7),
        ('web:comunidad', 0.7),
        ('web:nosotros', 0.6),
        ('web:contacto', 0.6),
        ('web:mi_espacio', 0.5),
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
