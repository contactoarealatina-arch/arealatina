from django.contrib import admin

from .models import RegistroAsistencia


@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'clase', 'alumno', 'estado', 'observacion')
    list_filter = ('estado', 'fecha', 'clase__nombre', 'clase__nivel')
    search_fields = ('alumno__nombre_completo', 'alumno__rut')
    date_hierarchy = 'fecha'
    autocomplete_fields = ('clase', 'alumno')
    list_editable = ('estado',)
