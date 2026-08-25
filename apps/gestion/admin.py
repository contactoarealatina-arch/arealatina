from django.contrib import admin

from .models import Alumno, Clase, Inscripcion, Pago, Plan, Suscripcion


class InscripcionInline(admin.TabularInline):
    model = Inscripcion
    extra = 0
    autocomplete_fields = ('clase',)


class SuscripcionInline(admin.TabularInline):
    model = Suscripcion
    extra = 0
    readonly_fields = ('fecha_vencimiento',)


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    fields = ('fecha_pago', 'concepto', 'monto_clp', 'metodo', 'estado', 'pago_matricula')


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nivel', 'dias_semana', 'hora_inicio', 'hora_fin', 'sala',
                    'profesora', 'cupo_maximo', 'activa')
    list_filter = ('nombre', 'nivel', 'activa', 'sala')
    search_fields = ('nombre', 'descripcion', 'sala')
    list_editable = ('activa',)
    autocomplete_fields = ('profesora',)
    fieldsets = (
        ('Identificacion', {'fields': ('nombre', 'nivel', 'descripcion', 'activa')}),
        ('Horario', {'fields': ('dias_semana', 'hora_inicio', 'hora_fin', 'sala')}),
        ('Capacidad y equipo', {'fields': ('cupo_maximo', 'profesora')}),
    )


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_clp', 'duracion_dias', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'descripcion')
    list_editable = ('activo',)


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'rut', 'telefono', 'email', 'estado',
                    'fecha_ingreso', 'al_dia')
    list_filter = ('estado', 'genero', 'fecha_ingreso')
    search_fields = ('nombre_completo', 'rut', 'email', 'telefono')
    date_hierarchy = 'fecha_ingreso'
    inlines = [InscripcionInline, SuscripcionInline, PagoInline]
    autocomplete_fields = ('usuario',)
    fieldsets = (
        ('Datos personales', {
            'fields': ('nombre_completo', 'rut', 'fecha_nacimiento', 'genero', 'foto')
        }),
        ('Contacto', {'fields': ('telefono', 'email', 'direccion')}),
        ('Emergencia', {'fields': ('contacto_emergencia', 'telefono_emergencia')}),
        ('Academia', {
            'fields': ('fecha_ingreso', 'estado', 'usuario', 'observaciones')
        }),
    )

    @admin.display(boolean=True, description='Al dia')
    def al_dia(self, obj):
        return obj.al_dia


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'clase', 'fecha_inscripcion')
    list_filter = ('clase__nombre', 'clase__nivel', 'fecha_inscripcion')
    search_fields = ('alumno__nombre_completo', 'alumno__rut')
    autocomplete_fields = ('alumno', 'clase')


@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'plan', 'fecha_inicio', 'fecha_vencimiento', 'activa', 'vigente')
    list_filter = ('activa', 'plan', 'fecha_inicio')
    search_fields = ('alumno__nombre_completo', 'alumno__rut')
    autocomplete_fields = ('alumno', 'plan')
    readonly_fields = ('fecha_vencimiento',)

    @admin.display(boolean=True, description='Vigente')
    def vigente(self, obj):
        return obj.vigente


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'concepto', 'monto_clp', 'metodo', 'estado',
                    'pago_matricula', 'fecha_pago')
    list_filter = ('estado', 'metodo', 'pago_matricula', 'fecha_pago')
    search_fields = ('alumno__nombre_completo', 'alumno__rut', 'concepto')
    date_hierarchy = 'fecha_pago'
    autocomplete_fields = ('alumno', 'suscripcion')
    list_editable = ('estado',)
