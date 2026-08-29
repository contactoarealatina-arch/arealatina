from django.apps import AppConfig


class GestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.gestion'
    verbose_name = 'Gestion academica'

    def ready(self):
        # Las señales se conectan al importar el módulo.
        from . import signals  # noqa: F401
