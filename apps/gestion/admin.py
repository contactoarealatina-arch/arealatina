from django.contrib import admin

from .models import (
    Alerta,
    Alumno,
    AuditLog,
    BrechaSeguridad,
    Categoria,
    RespaldoLog,
    SolicitudARCO,
    Clase,
    ConfiguracionAlertas,
    CorreoEnviado,
    Inscripcion,
    NotaInterna,
    Foto,
    Pago,
    Plan,
    Suscripcion,
    Testimonio,
)


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
    fields = ('fecha_pago', 'concepto', 'monto_clp', 'metodo', 'estado', 'numero_comprobante')


class NotaInternaInline(admin.TabularInline):
    model = NotaInterna
    extra = 0
    fields = ('created_at', 'autor', 'texto')
    readonly_fields = ('created_at',)


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'nivel', 'dias_display', 'horario',
                    'sala', 'profesora', 'inscritos', 'cupo_maximo', 'activa')
    list_filter = ('categoria', 'nombre', 'nivel', 'activa', 'sala')
    search_fields = ('nombre', 'descripcion', 'sala')
    list_editable = ('activa',)
    autocomplete_fields = ('profesora',)
    fieldsets = (
        ('Identificación', {'fields': ('nombre', 'categoria', 'nivel',
                                       'descripcion', 'edad_minima', 'activa')}),
        ('Horario', {'fields': ('dias_semana', 'hora_inicio', 'hora_fin', 'sala')}),
        ('Capacidad y equipo', {'fields': ('cupo_maximo', 'precio_clase_suelta', 'profesora')}),
    )

    @admin.display(description='Días')
    def dias_display(self, obj):
        return obj.dias_display

    @admin.display(description='Inscritos')
    def inscritos(self, obj):
        return obj.inscritos


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_clp', 'duracion_dias', 'suscripciones_vigentes', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'descripcion')
    list_editable = ('activo',)

    @admin.display(description='Alumnos con este plan')
    def suscripciones_vigentes(self, obj):
        return obj.suscripciones_vigentes


@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'rut', 'telefono', 'email', 'estado',
                    'fecha_ingreso', 'al_dia')
    list_filter = ('estado', 'genero', 'eliminado', 'fecha_ingreso')
    search_fields = ('nombre_completo', 'rut', 'email', 'telefono')
    date_hierarchy = 'fecha_ingreso'
    inlines = [InscripcionInline, SuscripcionInline, PagoInline, NotaInternaInline]
    autocomplete_fields = ('usuario',)
    readonly_fields = ('creado_por', 'actualizado_por', 'eliminado_en')
    fieldsets = (
        ('Datos personales', {
            'fields': ('nombre_completo', 'rut', 'fecha_nacimiento', 'genero', 'foto')
        }),
        ('Contacto', {'fields': ('telefono', 'email', 'direccion')}),
        ('Emergencia', {
            'fields': ('contacto_emergencia', 'telefono_emergencia', 'relacion_emergencia')
        }),
        ('Academia', {
            'fields': ('fecha_ingreso', 'estado', 'usuario', 'observaciones')
        }),
        ('Control', {
            'classes': ('collapse',),
            'fields': ('eliminado', 'eliminado_en', 'creado_por', 'actualizado_por'),
        }),
    )

    def get_queryset(self, request):
        # En el admin sí se ven los eliminados, para poder recuperarlos.
        return Alumno.todos.all()

    @admin.display(boolean=True, description='Al día')
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
    list_display = ('alumno', 'plan', 'fecha_inicio', 'fecha_vencimiento', 'estado', 'vigente')
    list_filter = ('estado', 'plan', 'fecha_inicio')
    search_fields = ('alumno__nombre_completo', 'alumno__rut')
    autocomplete_fields = ('alumno', 'plan')
    readonly_fields = ('fecha_vencimiento',)

    @admin.display(boolean=True, description='Vigente')
    def vigente(self, obj):
        return obj.vigente


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'concepto', 'monto_clp', 'metodo', 'estado',
                    'numero_comprobante', 'fecha_pago')
    list_filter = ('estado', 'metodo', 'concepto', 'fecha_pago')
    search_fields = ('alumno__nombre_completo', 'alumno__rut', 'detalle', 'numero_comprobante')
    date_hierarchy = 'fecha_pago'
    autocomplete_fields = ('alumno', 'suscripcion')
    list_editable = ('estado',)
    readonly_fields = ('registrado_por',)


@admin.register(NotaInterna)
class NotaInternaAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'autor', 'created_at')
    # 'texto' va cifrado en la base: no se puede buscar por contenido.
    search_fields = ('alumno__nombre_completo',)
    autocomplete_fields = ('alumno',)
    readonly_fields = ('autor',)


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'alumno', 'mensaje', 'gestionada', 'created_at')
    list_filter = ('tipo', 'gestionada', 'created_at')
    search_fields = ('alumno__nombre_completo', 'mensaje')
    autocomplete_fields = ('alumno',)
    readonly_fields = ('gestionada_en', 'gestionada_por')


@admin.register(CorreoEnviado)
class CorreoEnviadoAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'tipo', 'destinatario', 'asunto', 'enviado')
    list_filter = ('tipo', 'enviado', 'created_at')
    search_fields = ('destinatario', 'asunto', 'error')
    date_hierarchy = 'created_at'
    readonly_fields = ('tipo', 'destinatario', 'asunto', 'alumno',
                       'referencia', 'enviado', 'error', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ConfiguracionAlertas)
class ConfiguracionAlertasAdmin(admin.ModelAdmin):
    list_display = ('dias_anticipacion', 'hora_envio', 'envio_activo',
                    'enviar_bienvenida', 'enviar_recibos', 'enviar_recordatorios')

    def has_add_permission(self, request):
        # Fila única: se edita, no se crea.
        return not ConfiguracionAlertas.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'usuario', 'accion', 'modelo', 'objeto_id', 'descripcion', 'ip')
    list_filter = ('accion', 'modelo', 'timestamp')
    search_fields = ('descripcion', 'usuario__username', 'usuario__first_name')
    date_hierarchy = 'timestamp'
    readonly_fields = ('usuario', 'accion', 'modelo', 'objeto_id', 'descripcion', 'ip', 'timestamp')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # El log no se borra: es la bitácora del sistema.
        return False


@admin.register(SolicitudARCO)
class SolicitudARCOAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'tipo', 'estado', 'created_at', 'dias_restantes')
    list_filter = ('estado', 'tipo', 'created_at')
    search_fields = ('codigo', 'nombre', 'email', 'identificador')
    date_hierarchy = 'created_at'
    readonly_fields = ('codigo', 'nombre', 'email', 'identificador', 'tipo',
                       'descripcion', 'ip', 'created_at')
    fieldsets = (
        ('Solicitud', {'fields': ('codigo', 'nombre', 'email', 'identificador',
                                  'tipo', 'descripcion', 'ip', 'created_at')}),
        ('Gestión', {'fields': ('estado', 'respuesta', 'atendida_por', 'cerrada_en')}),
    )

    def has_add_permission(self, request):
        # Las solicitudes entran por el formulario público.
        return False

    @admin.display(description='Días restantes')
    def dias_restantes(self, obj):
        dias = obj.dias_restantes
        return '—' if dias is None else f'{dias} días'


@admin.register(BrechaSeguridad)
class BrechaSeguridadAdmin(admin.ModelAdmin):
    list_display = ('fecha_deteccion', 'gravedad', 'estado', 'personas_afectadas',
                    'horas_restantes_display')
    list_filter = ('estado', 'gravedad', 'fecha_deteccion')
    search_fields = ('descripcion', 'datos_afectados')
    date_hierarchy = 'fecha_deteccion'

    @admin.display(description='Plazo de 72 h')
    def horas_restantes_display(self, obj):
        if obj.notificada_autoridad_en:
            return 'Notificada'
        return f'{obj.horas_restantes:.0f} h restantes'


@admin.register(RespaldoLog)
class RespaldoLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'archivo', 'tamano_legible', 'estado', 'destino')
    list_filter = ('estado', 'created_at')
    readonly_fields = ('archivo', 'destino', 'tamano_bytes', 'estado',
                       'detalle', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'slug', 'icono', 'orden', 'cuantas_clases', 'activa')
    list_editable = ('orden', 'activa')
    prepopulated_fields = {'slug': ('nombre',)}
    search_fields = ('nombre', 'bajada', 'descripcion')

    @admin.display(description='Clases activas')
    def cuantas_clases(self, obj):
        return obj.clases_activas.count()


@admin.register(Testimonio)
class TestimonioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'detalle', 'orden', 'publicado')
    list_editable = ('orden', 'publicado')
    list_filter = ('publicado',)
    search_fields = ('nombre', 'detalle', 'texto')


@admin.register(Foto)
class FotoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'orden', 'publicada', 'created_at')
    list_editable = ('orden', 'publicada')
    list_filter = ('publicada',)
    search_fields = ('titulo',)
