from django.contrib import admin

from .models import MensajeContacto


@admin.register(MensajeContacto)
class MensajeContactoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'email', 'telefono', 'leido', 'created_at')
    list_filter = ('leido', 'created_at')
    search_fields = ('nombre', 'email', 'mensaje')
    readonly_fields = ('nombre', 'email', 'telefono', 'mensaje', 'created_at')
    list_editable = ('leido',)

    def has_add_permission(self, request):
        return False
