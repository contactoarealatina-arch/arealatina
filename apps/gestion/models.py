"""Modelos de gestión académica: clases, planes, alumnos, suscripciones y pagos."""
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField

from apps.usuarios.models import TimeStampedModel

from .validadores import validar_foto


class DiaSemana(models.TextChoices):
    """Los días se guardan como códigos separados por coma: 'LU,MI'."""

    LU = 'LU', 'Lunes'
    MA = 'MA', 'Martes'
    MI = 'MI', 'Miércoles'
    JU = 'JU', 'Jueves'
    VI = 'VI', 'Viernes'
    SA = 'SA', 'Sábado'
    DO = 'DO', 'Domingo'


class Clase(TimeStampedModel):
    """Una clase regular del estudio, con su horario y profesora a cargo."""

    class Estilo(models.TextChoices):
        SALSA = 'SALSA', 'Salsa'
        BACHATA = 'BACHATA', 'Bachata'
        REGGAETON = 'REGGAETON', 'Reggaetón'
        URBANO = 'URBANO', 'Urbano'
        TANGO = 'TANGO', 'Tango'
        KIDS = 'KIDS', 'Kids Dance'

    class Nivel(models.TextChoices):
        TODOS = 'TODOS', 'Todos los niveles'
        INICIAL = 'INICIAL', 'Principiante'
        INTERMEDIO = 'INTERMEDIO', 'Intermedio'
        AVANZADO = 'AVANZADO', 'Avanzado'

    EMOJIS = {
        'SALSA': '\U0001F483',
        'BACHATA': '\U0001F339',
        'REGGAETON': '\U0001F525',
        'URBANO': '\U0001F3A4',
        'TANGO': '\U0001F3B6',
        'KIDS': '\U0001F476',
    }

    nombre = models.CharField('Estilo', max_length=15, choices=Estilo.choices)
    descripcion = models.TextField('Descripción', blank=True)
    nivel = models.CharField(
        'Nivel',
        max_length=12,
        choices=Nivel.choices,
        default=Nivel.TODOS,
    )
    dias_semana = models.CharField(
        'Días de la semana',
        max_length=30,
        help_text='Códigos separados por coma. Ej: LU,MI',
    )
    hora_inicio = models.TimeField('Hora de inicio')
    hora_fin = models.TimeField('Hora de término')
    sala = models.CharField('Sala', max_length=50, default='Sala 1')
    cupo_maximo = models.PositiveSmallIntegerField('Cupo máximo', default=20)
    precio_clase_suelta = models.PositiveIntegerField(
        'Precio clase suelta (CLP)',
        null=True,
        blank=True,
        help_text='Opcional. Para cobrar esta clase por separado.',
    )
    activa = models.BooleanField('Activa', default=True)

    profesora = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clases_dictadas',
        verbose_name='Profesor/a',
        limit_choices_to={'rol': 'PROFESOR'},
    )

    class Meta:
        verbose_name = 'Clase'
        verbose_name_plural = 'Clases'
        ordering = ['nombre', 'hora_inicio']

    def __str__(self):
        return f'{self.get_nombre_display()} · {self.get_nivel_display()} ({self.dias_display})'

    def get_absolute_url(self):
        return reverse('gestion:clase_detalle', args=[self.pk])

    # ------------------------------------------------------------------
    # Días
    # ------------------------------------------------------------------
    @property
    def dias_lista(self):
        """Códigos de día, en el orden de la semana."""
        guardados = {d for d in self.dias_semana.split(',') if d}
        return [c for c, _ in DiaSemana.choices if c in guardados]

    @property
    def dias_display(self):
        """'Lunes y Miércoles' / 'Lunes, Miércoles y Viernes'."""
        etiquetas = dict(DiaSemana.choices)
        nombres = [etiquetas[c] for c in self.dias_lista]
        if not nombres:
            return 'Sin días asignados'
        if len(nombres) == 1:
            return nombres[0]
        return ', '.join(nombres[:-1]) + ' y ' + nombres[-1]

    @property
    def dias_corto(self):
        """'L · M · V' para las tarjetas compactas."""
        return ' · '.join(c[0] for c in self.dias_lista)

    # ------------------------------------------------------------------
    # Horario y cupo
    # ------------------------------------------------------------------
    @property
    def horario(self):
        return f'{self.hora_inicio:%H:%M} - {self.hora_fin:%H:%M}'

    @property
    def inscritos(self):
        return self.inscripciones.filter(alumno__eliminado=False).count()

    @property
    def cupos_disponibles(self):
        return max(self.cupo_maximo - self.inscritos, 0)

    @property
    def tasa_llenado(self):
        if not self.cupo_maximo:
            return 0
        return round(self.inscritos / self.cupo_maximo * 100)

    @property
    def emoji(self):
        return self.EMOJIS.get(self.nombre, '\U0001F3B5')


class Plan(TimeStampedModel):
    """Plan o mensualidad que puede contratar un alumno."""

    nombre = models.CharField('Nombre', max_length=80, unique=True)
    precio_clp = models.PositiveIntegerField('Precio (CLP)')
    duracion_dias = models.PositiveSmallIntegerField('Duración (días)', default=30)
    descripcion = models.TextField('Descripción', blank=True)
    activo = models.BooleanField('Activo', default=True)

    class Meta:
        verbose_name = 'Plan'
        verbose_name_plural = 'Planes'
        ordering = ['precio_clp']

    def __str__(self):
        return f'{self.nombre} · ${self.precio_clp:,.0f}'.replace(',', '.')

    @property
    def suscripciones_vigentes(self):
        return self.suscripciones.filter(
            estado=Suscripcion.Estado.ACTIVA,
            alumno__eliminado=False,
        ).count()


class AlumnoQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(estado=Alumno.Estado.ACTIVO)

    def vigentes(self):
        """Con suscripción activa y no vencida."""
        return self.filter(
            suscripciones__estado=Suscripcion.Estado.ACTIVA,
            suscripciones__fecha_vencimiento__gte=timezone.localdate(),
        ).distinct()


class AlumnoManager(models.Manager.from_queryset(AlumnoQuerySet)):
    """Manager por defecto: oculta los alumnos borrados (borrado lógico)."""

    def get_queryset(self):
        return super().get_queryset().filter(eliminado=False)


class Alumno(TimeStampedModel):
    """Ficha del alumno del estudio."""

    class Estado(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        INACTIVO = 'INACTIVO', 'Inactivo'
        SUSPENDIDO = 'SUSPENDIDO', 'Suspendido'

    class Genero(models.TextChoices):
        MASCULINO = 'M', 'Masculino'
        FEMENINO = 'F', 'Femenino'
        NO_INFORMA = 'N', 'Prefiero no indicar'

    class Relacion(models.TextChoices):
        MADRE = 'MADRE', 'Madre'
        PADRE = 'PADRE', 'Padre'
        PAREJA = 'PAREJA', 'Pareja'
        AMIGO = 'AMIGO', 'Amigo/a'
        OTRO = 'OTRO', 'Otro'

    nombre_completo = models.CharField('Nombre completo', max_length=150)
    rut = models.CharField('RUT', max_length=12, unique=True, help_text='Formato 12.345.678-9')
    fecha_nacimiento = models.DateField('Fecha de nacimiento', null=True, blank=True)
    genero = models.CharField(
        'Género',
        max_length=1,
        choices=Genero.choices,
        default=Genero.NO_INFORMA,
    )

    telefono = models.CharField('Teléfono', max_length=20, blank=True)
    email = models.EmailField('Email', blank=True)
    direccion = EncryptedCharField('Dirección', max_length=200, blank=True, default='')

    # Estos cuatro campos van cifrados en la base de datos. Se eligieron
    # justamente porque NUNCA se buscan ni se filtran.
    #
    # RUT, email y telefono quedan SIN cifrar a proposito: Fernet no es
    # determinista (el mismo valor da un texto distinto cada vez), asi que
    # cifrarlos romperia tres cosas a la vez, y en silencio:
    #   1. unique=True del RUT dejaria de detectar duplicados
    #   2. filter(rut=...) del alta devolveria vacio siempre
    #   3. el buscador del listado (icontains) no encontraria nada
    # Para esos tres la proteccion es: cifrado de disco del proveedor, TLS
    # en transito, control de acceso por rol y registro de quien consulta
    # cada ficha.
    contacto_emergencia = EncryptedCharField('Contacto de emergencia', max_length=150)
    telefono_emergencia = EncryptedCharField('Teléfono de emergencia', max_length=20)
    relacion_emergencia = models.CharField(
        'Relación',
        max_length=10,
        choices=Relacion.choices,
        default=Relacion.OTRO,
    )

    fecha_ingreso = models.DateField('Fecha de ingreso', default=timezone.localdate)
    foto = models.ImageField(
        'Foto', upload_to='alumnos/', null=True, blank=True,
        validators=[validar_foto],
        help_text='JPG, PNG o WebP. Máximo 5 MB.')
    estado = models.CharField(
        'Estado',
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVO,
    )
    observaciones = EncryptedTextField('Observaciones', blank=True, default='')

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ficha_alumno',
        verbose_name='Usuario asociado',
    )

    # Borrado lógico
    eliminado = models.BooleanField('Eliminado', default=False)
    eliminado_en = models.DateTimeField('Eliminado el', null=True, blank=True)

    # Trazabilidad
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='alumnos_creados',
        verbose_name='Creado por',
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='alumnos_actualizados',
        verbose_name='Actualizado por',
    )

    objects = AlumnoManager()
    todos = models.Manager()

    class Meta:
        verbose_name = 'Alumno'
        verbose_name_plural = 'Alumnos'
        ordering = ['nombre_completo']

    def __str__(self):
        return f'{self.nombre_completo} ({self.rut})'

    def get_absolute_url(self):
        return reverse('gestion:alumno_detalle', args=[self.pk])

    def eliminar_logico(self, usuario=None):
        """No borra la fila: la marca. Así el historial de pagos sobrevive."""
        self.eliminado = True
        self.eliminado_en = timezone.now()
        if usuario:
            self.actualizado_por = usuario
        self.save(update_fields=['eliminado', 'eliminado_en', 'actualizado_por', 'updated_at'])

    # ------------------------------------------------------------------
    # Datos derivados
    # ------------------------------------------------------------------
    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = timezone.localdate()
        return hoy.year - self.fecha_nacimiento.year - (
            (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        )

    @property
    def primer_nombre(self):
        """Para saludar en los correos sin sonar a formulario."""
        partes = self.nombre_completo.split()
        return partes[0] if partes else self.nombre_completo

    @property
    def iniciales(self):
        partes = self.nombre_completo.split()
        if not partes:
            return '?'
        return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else '')).upper()

    @property
    def suscripcion_vigente(self):
        return (
            self.suscripciones
            .filter(estado=Suscripcion.Estado.ACTIVA)
            .order_by('-fecha_vencimiento')
            .first()
        )

    @property
    def dias_para_vencer(self):
        sus = self.suscripcion_vigente
        if not sus:
            return None
        return (sus.fecha_vencimiento - timezone.localdate()).days

    @property
    def estado_pago(self):
        """'al_dia' | 'por_vencer' | 'vencido' | 'sin_plan'"""
        dias = self.dias_para_vencer
        if dias is None:
            return 'sin_plan'
        if dias < 0:
            return 'vencido'
        if dias <= ConfiguracionAlertas.dias_anticipacion_actual():
            return 'por_vencer'
        return 'al_dia'

    @property
    def estado_pago_display(self):
        return {
            'al_dia': 'Al día',
            'por_vencer': 'Por vencer',
            'vencido': 'Vencido',
            'sin_plan': 'Sin plan',
        }[self.estado_pago]

    @property
    def al_dia(self):
        return self.estado_pago in ('al_dia', 'por_vencer')

    @property
    def total_pagado(self):
        return self.pagos.filter(estado=Pago.Estado.PAGADO).aggregate(
            t=models.Sum('monto_clp'))['t'] or 0


class Inscripcion(TimeStampedModel):
    """Relaciona a un alumno con una clase a la que asiste."""

    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name='inscripciones',
        verbose_name='Alumno',
    )
    clase = models.ForeignKey(
        Clase,
        on_delete=models.CASCADE,
        related_name='inscripciones',
        verbose_name='Clase',
    )
    fecha_inscripcion = models.DateField('Fecha de inscripción', default=timezone.localdate)

    class Meta:
        verbose_name = 'Inscripción'
        verbose_name_plural = 'Inscripciones'
        ordering = ['-fecha_inscripcion']
        constraints = [
            models.UniqueConstraint(
                fields=['alumno', 'clase'],
                name='inscripcion_unica_alumno_clase',
            )
        ]

    def __str__(self):
        return f'{self.alumno.nombre_completo} en {self.clase}'


class Suscripcion(TimeStampedModel):
    """Plan contratado por un alumno durante un periodo determinado."""

    class Estado(models.TextChoices):
        ACTIVA = 'ACTIVA', 'Activa'
        VENCIDA = 'VENCIDA', 'Vencida'
        CANCELADA = 'CANCELADA', 'Cancelada'

    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name='suscripciones',
        verbose_name='Alumno',
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name='suscripciones',
        verbose_name='Plan',
    )
    fecha_inicio = models.DateField('Fecha de inicio', default=timezone.localdate)
    fecha_vencimiento = models.DateField(
        'Fecha de vencimiento',
        blank=True,
        help_text='Se calcula automáticamente según la duración del plan.',
    )
    estado = models.CharField(
        'Estado',
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVA,
    )

    class Meta:
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f'{self.alumno.nombre_completo} · {self.plan.nombre} (vence {self.fecha_vencimiento})'

    def save(self, *args, **kwargs):
        if not self.fecha_vencimiento and self.fecha_inicio and self.plan_id:
            self.fecha_vencimiento = self.fecha_inicio + timedelta(days=self.plan.duracion_dias)
        super().save(*args, **kwargs)

    @property
    def activa(self):
        return self.estado == self.Estado.ACTIVA

    @property
    def vigente(self):
        return self.activa and self.fecha_vencimiento >= timezone.localdate()

    @property
    def dias_restantes(self):
        return (self.fecha_vencimiento - timezone.localdate()).days

    @property
    def porcentaje_consumido(self):
        """Para la barra de progreso de la ficha del alumno."""
        total = (self.fecha_vencimiento - self.fecha_inicio).days
        if total <= 0:
            return 100
        transcurrido = (timezone.localdate() - self.fecha_inicio).days
        return max(0, min(round(transcurrido / total * 100), 100))


class Pago(TimeStampedModel):
    """Pago realizado por un alumno (mensualidad, matrícula, clase suelta, etc.)."""

    class Concepto(models.TextChoices):
        MENSUALIDAD = 'MENSUALIDAD', 'Mensualidad'
        MATRICULA = 'MATRICULA', 'Matrícula'
        CLASE_SUELTA = 'CLASE_SUELTA', 'Clase suelta'
        OTRO = 'OTRO', 'Otro'

    class Metodo(models.TextChoices):
        EFECTIVO = 'EFECTIVO', 'Efectivo'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia'

    class Estado(models.TextChoices):
        PAGADO = 'PAGADO', 'Pagado'
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ATRASADO = 'ATRASADO', 'Atrasado'

    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name='pagos',
        verbose_name='Alumno',
    )
    suscripcion = models.ForeignKey(
        Suscripcion,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagos',
        verbose_name='Suscripción',
    )
    concepto = models.CharField(
        'Concepto',
        max_length=15,
        choices=Concepto.choices,
        default=Concepto.MENSUALIDAD,
    )
    detalle = models.CharField(
        'Detalle',
        max_length=150,
        blank=True,
        help_text='Obligatorio cuando el concepto es "Otro".',
    )
    monto_clp = models.PositiveIntegerField('Monto (CLP)')
    metodo = models.CharField(
        'Método de pago',
        max_length=15,
        choices=Metodo.choices,
        default=Metodo.EFECTIVO,
    )
    numero_comprobante = models.CharField('N° de comprobante', max_length=50, blank=True)
    pago_matricula = models.BooleanField('Es pago de matrícula', default=False)
    fecha_pago = models.DateField('Fecha de pago', default=timezone.localdate)
    estado = models.CharField(
        'Estado',
        max_length=10,
        choices=Estado.choices,
        default=Estado.PAGADO,
    )
    nota_interna = models.TextField('Nota interna', blank=True)

    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pagos_registrados',
        verbose_name='Registrado por',
    )

    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-fecha_pago', '-created_at']

    def __str__(self):
        monto = f'{self.monto_clp:,.0f}'.replace(',', '.')
        return f'{self.alumno.nombre_completo} · ${monto} ({self.get_estado_display()})'

    def save(self, *args, **kwargs):
        # Mantiene coherente la casilla de matrícula con el concepto elegido.
        self.pago_matricula = self.concepto == self.Concepto.MATRICULA
        super().save(*args, **kwargs)

    @property
    def concepto_display(self):
        if self.concepto == self.Concepto.OTRO and self.detalle:
            return self.detalle
        return self.get_concepto_display()


class NotaInterna(TimeStampedModel):
    """Comentario del equipo sobre un alumno. No lo ve el alumno."""

    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name='notas',
        verbose_name='Alumno',
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='notas_escritas',
        verbose_name='Autor',
    )
    texto = EncryptedTextField('Nota')

    class Meta:
        verbose_name = 'Nota interna'
        verbose_name_plural = 'Notas internas'
        ordering = ['-created_at']

    def __str__(self):
        return f'Nota sobre {self.alumno.nombre_completo} ({self.created_at:%d/%m/%Y})'


class Alerta(TimeStampedModel):
    """Aviso generado automáticamente por el cron diario."""

    class Tipo(models.TextChoices):
        VENCIMIENTO_PROXIMO = 'VENCIMIENTO_PROXIMO', 'Plan por vencer'
        PLAN_VENCIDO = 'PLAN_VENCIDO', 'Plan vencido'
        PAGO_PENDIENTE = 'PAGO_PENDIENTE', 'Pago pendiente'
        AUSENCIA_PROLONGADA = 'AUSENCIA', 'Lleva dos semanas sin venir'

    tipo = models.CharField('Tipo', max_length=20, choices=Tipo.choices)
    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name='alertas',
        verbose_name='Alumno',
    )
    suscripcion = models.ForeignKey(
        Suscripcion,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='alertas',
        verbose_name='Suscripción',
    )
    mensaje = models.CharField('Mensaje', max_length=250)
    gestionada = models.BooleanField('Gestionada', default=False)
    gestionada_en = models.DateTimeField('Gestionada el', null=True, blank=True)
    gestionada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='alertas_gestionadas',
        verbose_name='Gestionada por',
    )

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['gestionada', '-created_at']
        constraints = [
            # Una alerta viva por tipo y alumno: el cron no duplica.
            models.UniqueConstraint(
                fields=['tipo', 'alumno'],
                condition=models.Q(gestionada=False),
                name='alerta_unica_activa_por_tipo_alumno',
            )
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} · {self.alumno.nombre_completo}'

    def marcar_gestionada(self, usuario=None):
        self.gestionada = True
        self.gestionada_en = timezone.now()
        self.gestionada_por = usuario
        self.save(update_fields=['gestionada', 'gestionada_en', 'gestionada_por', 'updated_at'])

    @property
    def severidad(self):
        return {
            self.Tipo.VENCIMIENTO_PROXIMO: 'warning',
            self.Tipo.PLAN_VENCIDO: 'danger',
            self.Tipo.PAGO_PENDIENTE: 'orange',
            self.Tipo.AUSENCIA_PROLONGADA: 'warning',
        }[self.tipo]


class ConfiguracionAlertas(TimeStampedModel):
    """Ajustes del cron de alertas. Fila única (pk=1)."""

    dias_anticipacion = models.PositiveSmallIntegerField(
        'Días de anticipación',
        default=7,
        help_text='Con cuántos días de anticipación avisar un vencimiento.',
    )
    emails_destino = models.TextField(
        'Emails que reciben el resumen',
        default='arealatina310@gmail.com',
        help_text='Separados por coma.',
    )
    hora_envio = models.TimeField('Hora de envío', default='09:00')
    envio_activo = models.BooleanField(
        'Enviar resumen diario al equipo', default=True)

    # Correos que le llegan al alumno. Se pueden apagar por separado:
    # el plan gratuito de Brevo tiene tope diario y conviene poder cortar
    # uno sin apagar todo.
    enviar_bienvenida = models.BooleanField(
        'Correo de bienvenida al inscribir', default=True)
    enviar_recibos = models.BooleanField(
        'Comprobante al registrar un pago', default=True)
    enviar_recordatorios = models.BooleanField(
        'Aviso al alumno antes de que venza su plan', default=True)

    class Meta:
        verbose_name = 'Configuración de alertas'
        verbose_name_plural = 'Configuración de alertas'

    def __str__(self):
        return f'Alertas: {self.dias_anticipacion} días de anticipación'

    def save(self, *args, **kwargs):
        self.pk = 1  # Siempre la misma fila.
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls):
        config, _ = cls.objects.get_or_create(pk=1)
        return config

    @classmethod
    def dias_anticipacion_actual(cls):
        """Sin tocar la BD si ya existe: se usa mucho en propiedades."""
        try:
            return cls.objects.values_list('dias_anticipacion', flat=True).first() or 7
        except Exception:
            return 7

    @property
    def lista_emails(self):
        return [e.strip() for e in self.emails_destino.split(',') if e.strip()]


class AuditLog(models.Model):
    """Registro de acciones importantes. Solo lo consulta el superadmin."""

    class Accion(models.TextChoices):
        CREAR = 'CREAR', 'Creó'
        EDITAR = 'EDITAR', 'Editó'
        ELIMINAR = 'ELIMINAR', 'Eliminó'
        PAGO = 'PAGO', 'Registró pago'
        RENOVAR = 'RENOVAR', 'Renovó plan'
        ASISTENCIA = 'ASISTENCIA', 'Registró asistencia'
        LOGIN = 'LOGIN', 'Inició sesión'
        LOGOUT = 'LOGOUT', 'Cerró sesión'
        LOGIN_FALLIDO = 'LOGIN_FALLIDO', 'Intento fallido'
        VER_FICHA = 'VER_FICHA', 'Consultó una ficha'
        EXPORTAR = 'EXPORTAR', 'Descargó un reporte'
        ARCO = 'ARCO', 'Solicitud de datos personales'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='acciones',
        verbose_name='Usuario',
    )
    accion = models.CharField('Acción', max_length=15, choices=Accion.choices)
    modelo = models.CharField('Modelo', max_length=50, blank=True)
    objeto_id = models.PositiveIntegerField('ID del objeto', null=True, blank=True)
    descripcion = models.CharField('Descripción', max_length=250, blank=True)
    ip = models.GenericIPAddressField('IP', null=True, blank=True)
    user_agent = models.CharField('Navegador', max_length=250, blank=True)
    sospechoso = models.BooleanField('Marcado como sospechoso', default=False)
    timestamp = models.DateTimeField('Fecha y hora', auto_now_add=True)

    class Meta:
        verbose_name = 'Registro de auditoría'
        verbose_name_plural = 'Registros de auditoría'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['modelo', 'objeto_id']),
            models.Index(fields=['accion', '-timestamp']),
            models.Index(fields=['ip', '-timestamp']),
        ]

    def __str__(self):
        quien = self.usuario.get_full_name() if self.usuario else 'Sistema'
        return f'{quien} {self.get_accion_display().lower()} {self.modelo} #{self.objeto_id}'


class CorreoEnviado(models.Model):
    """Bitácora de correos. Sirve para dos cosas concretas:

    - No mandarle dos veces el mismo aviso al mismo alumno.
    - Saber por qué no llegó un correo cuando alguien reclama.
    """

    class Tipo(models.TextChoices):
        BIENVENIDA = 'BIENVENIDA', 'Bienvenida'
        RECIBO = 'RECIBO', 'Comprobante de pago'
        RECORDATORIO = 'RECORDATORIO', 'Aviso de vencimiento'
        RESUMEN = 'RESUMEN', 'Resumen para el equipo'
        CONTACTO = 'CONTACTO', 'Mensaje del formulario web'
        RECORDATORIO_CLASE = 'REC_CLASE', 'Recordatorio de clase al alumno'
        CONFIRMACION = 'CONFIRMACION', 'Confirmacion de asistencia'
        BIENV_PROFE = 'BIENV_PROFE', 'Bienvenida a profesora'
        REC_PROFE = 'REC_PROFE', 'Recordatorio de clases a profesora'
        CUMPLEANOS = 'CUMPLEANOS', 'Saludo de cumpleanos'
        AUSENCIA = 'AUSENCIA', 'Aviso de ausencia prolongada'
        INFORME = 'INFORME', 'Informe mensual'

    tipo = models.CharField('Tipo', max_length=15, choices=Tipo.choices)
    destinatario = models.EmailField('Destinatario')
    asunto = models.CharField('Asunto', max_length=250)
    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='correos',
        verbose_name='Alumno',
    )
    referencia = models.CharField(
        'Referencia',
        max_length=60,
        blank=True,
        help_text='Identifica el envío para no repetirlo. Ej: RECORDATORIO-12-2026-08-30',
    )
    enviado = models.BooleanField('Enviado', default=False)
    error = models.TextField('Error', blank=True)
    created_at = models.DateTimeField('Fecha', auto_now_add=True)

    class Meta:
        verbose_name = 'Correo enviado'
        verbose_name_plural = 'Correos enviados'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tipo', 'referencia']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        estado = 'OK' if self.enviado else 'FALLÓ'
        return f'[{estado}] {self.get_tipo_display()} → {self.destinatario}'


class ConfirmacionAsistencia(models.Model):
    """El alumno avisa desde su portal que va a venir a una clase.

    Es distinto de RegistroAsistencia: esto es una intención previa, lo otro
    es lo que realmente pasó y lo marca la profesora. Sirve para que ella
    sepa cuánta gente esperar.
    """

    alumno = models.ForeignKey(
        Alumno,
        on_delete=models.CASCADE,
        related_name='confirmaciones',
        verbose_name='Alumno',
    )
    clase = models.ForeignKey(
        Clase,
        on_delete=models.CASCADE,
        related_name='confirmaciones',
        verbose_name='Clase',
    )
    fecha = models.DateField('Fecha de la clase')
    confirmado_en = models.DateTimeField('Confirmado el', auto_now_add=True)

    class Meta:
        verbose_name = 'Confirmación de asistencia'
        verbose_name_plural = 'Confirmaciones de asistencia'
        ordering = ['-fecha', '-confirmado_en']
        constraints = [
            models.UniqueConstraint(
                fields=['alumno', 'clase', 'fecha'],
                name='confirmacion_unica_alumno_clase_fecha',
            )
        ]
        indexes = [models.Index(fields=['clase', 'fecha'])]

    def __str__(self):
        return f'{self.alumno.nombre_completo} confirmó {self.clase} el {self.fecha:%d/%m/%Y}'


class TokenActivacion(models.Model):
    """Enlace de un solo uso para que el alumno elija su contraseña.

    Se prefiere esto a mandarle una contraseña inicial predecible: el RUT
    circula demasiado en Chile como para servir de clave, aunque se cambie
    después.
    """

    HORAS_VALIDEZ = 48

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tokens_activacion',
        verbose_name='Usuario',
    )
    token = models.CharField('Token', max_length=64, unique=True, db_index=True)
    creado_en = models.DateTimeField('Creado el', auto_now_add=True)
    usado_en = models.DateTimeField('Usado el', null=True, blank=True)

    class Meta:
        verbose_name = 'Token de activación'
        verbose_name_plural = 'Tokens de activación'
        ordering = ['-creado_en']

    def __str__(self):
        estado = 'usado' if self.usado_en else ('vencido' if self.vencido else 'vigente')
        return f'Token de {self.usuario} ({estado})'

    @classmethod
    def crear_para(cls, usuario):
        """Un token nuevo invalida los anteriores del mismo usuario."""
        import secrets

        cls.objects.filter(usuario=usuario, usado_en__isnull=True).delete()
        return cls.objects.create(usuario=usuario, token=secrets.token_urlsafe(32))

    @property
    def vencido(self):
        limite = self.creado_en + timedelta(hours=self.HORAS_VALIDEZ)
        return timezone.now() > limite

    @property
    def valido(self):
        return self.usado_en is None and not self.vencido

    def marcar_usado(self):
        self.usado_en = timezone.now()
        self.save(update_fields=['usado_en'])


class SolicitudARCO(models.Model):
    """Solicitud de una persona sobre sus datos personales.

    La Ley 21.719 reconoce los derechos de Acceso, Rectificacion,
    Cancelacion, Oposicion y Portabilidad, y da un plazo para responder.
    Este modelo deja constancia de que la solicitud llego y de cuando.
    """

    DIAS_PLAZO = 30

    class Tipo(models.TextChoices):
        ACCESO = 'ACCESO', 'Acceso a mis datos'
        RECTIFICACION = 'RECTIFICACION', 'Rectificación de datos'
        CANCELACION = 'CANCELACION', 'Cancelación (eliminación)'
        OPOSICION = 'OPOSICION', 'Oposición al tratamiento'
        PORTABILIDAD = 'PORTABILIDAD', 'Portabilidad de datos'

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        EN_PROCESO = 'EN_PROCESO', 'En proceso'
        COMPLETADA = 'COMPLETADA', 'Completada'
        RECHAZADA = 'RECHAZADA', 'Rechazada'

    codigo = models.CharField('Número de caso', max_length=20, unique=True, editable=False)
    nombre = models.CharField('Nombre completo', max_length=150)
    email = models.EmailField('Email de contacto')
    identificador = models.CharField(
        'RUT o email registrado', max_length=60, blank=True,
        help_text='Para poder encontrar sus datos en el sistema.')
    tipo = models.CharField('Tipo de solicitud', max_length=15, choices=Tipo.choices)
    descripcion = models.TextField('Detalle de la solicitud')

    estado = models.CharField('Estado', max_length=12, choices=Estado.choices,
                              default=Estado.PENDIENTE)
    respuesta = models.TextField('Respuesta entregada', blank=True)
    atendida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='solicitudes_arco', verbose_name='Atendida por')
    cerrada_en = models.DateTimeField('Cerrada el', null=True, blank=True)

    ip = models.GenericIPAddressField('IP de origen', null=True, blank=True)
    created_at = models.DateTimeField('Recibida el', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizada el', auto_now=True)

    class Meta:
        verbose_name = 'Solicitud ARCO'
        verbose_name_plural = 'Solicitudes ARCO'
        ordering = ['estado', 'created_at']

    def __str__(self):
        return f'{self.codigo} · {self.get_tipo_display()} · {self.nombre}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            import secrets
            marca = timezone.localdate().strftime('%Y%m')
            self.codigo = f'ARCO-{marca}-{secrets.token_hex(3).upper()}'
        super().save(*args, **kwargs)

    @property
    def fecha_limite(self):
        return (self.created_at + timedelta(days=self.DIAS_PLAZO)).date()

    @property
    def dias_restantes(self):
        if self.estado in (self.Estado.COMPLETADA, self.Estado.RECHAZADA):
            return None
        return (self.fecha_limite - timezone.localdate()).days

    @property
    def urgente(self):
        dias = self.dias_restantes
        return dias is not None and dias <= 7


class BrechaSeguridad(models.Model):
    """Registro de un incidente de seguridad.

    La Ley 21.719 obliga a notificar las brechas a la autoridad dentro de
    un plazo corto. Este modelo existe para que, si pasa, haya un lugar
    donde anotar la hora exacta de deteccion y las acciones tomadas, en
    vez de reconstruirlo despues de memoria.
    """

    HORAS_PLAZO = 72

    class Estado(models.TextChoices):
        DETECTADA = 'DETECTADA', 'Detectada'
        EN_INVESTIGACION = 'INVESTIGACION', 'En investigación'
        NOTIFICADA = 'NOTIFICADA', 'Notificada a la autoridad'
        CERRADA = 'CERRADA', 'Cerrada'

    class Gravedad(models.TextChoices):
        BAJA = 'BAJA', 'Baja'
        MEDIA = 'MEDIA', 'Media'
        ALTA = 'ALTA', 'Alta'
        CRITICA = 'CRITICA', 'Crítica'

    fecha_deteccion = models.DateTimeField('Detectada el', default=timezone.now)
    descripcion = models.TextField('Qué pasó')
    datos_afectados = models.TextField(
        'Datos afectados',
        help_text='Qué información quedó expuesta y de cuántas personas.')
    personas_afectadas = models.PositiveIntegerField('Personas afectadas', default=0)
    gravedad = models.CharField('Gravedad', max_length=8, choices=Gravedad.choices,
                                default=Gravedad.MEDIA)
    acciones_tomadas = models.TextField('Acciones tomadas', blank=True)

    estado = models.CharField('Estado', max_length=14, choices=Estado.choices,
                              default=Estado.DETECTADA)
    notificada_autoridad_en = models.DateTimeField(
        'Notificada a la autoridad el', null=True, blank=True)
    notificados_afectados = models.BooleanField(
        'Se avisó a las personas afectadas', default=False)

    registrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='brechas_registradas', verbose_name='Registrada por')
    created_at = models.DateTimeField('Registrada el', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizada el', auto_now=True)

    class Meta:
        verbose_name = 'Brecha de seguridad'
        verbose_name_plural = 'Brechas de seguridad'
        ordering = ['-fecha_deteccion']

    def __str__(self):
        return f'{self.get_gravedad_display()} · {self.fecha_deteccion:%d/%m/%Y %H:%M}'

    @property
    def horas_transcurridas(self):
        return (timezone.now() - self.fecha_deteccion).total_seconds() / 3600

    @property
    def horas_restantes(self):
        return max(self.HORAS_PLAZO - self.horas_transcurridas, 0)

    @property
    def semaforo(self):
        """verde / amarillo / rojo segun lo que queda del plazo de 72 horas."""
        if self.notificada_autoridad_en:
            return 'verde'
        restantes = self.horas_restantes
        if restantes <= 24:
            return 'rojo'
        if restantes <= 48:
            return 'amarillo'
        return 'verde'


class RespaldoLog(models.Model):
    """Constancia de cada respaldo de la base de datos."""

    class Estado(models.TextChoices):
        OK = 'OK', 'Correcto'
        ERROR = 'ERROR', 'Con error'

    archivo = models.CharField('Archivo', max_length=200)
    destino = models.CharField('Destino', max_length=250, blank=True)
    tamano_bytes = models.BigIntegerField('Tamaño (bytes)', default=0)
    estado = models.CharField('Estado', max_length=6, choices=Estado.choices,
                              default=Estado.OK)
    detalle = models.TextField('Detalle', blank=True)
    created_at = models.DateTimeField('Fecha', auto_now_add=True)

    class Meta:
        verbose_name = 'Respaldo'
        verbose_name_plural = 'Respaldos'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.archivo} ({self.tamano_legible})'

    @property
    def tamano_legible(self):
        tam = float(self.tamano_bytes)
        for unidad in ('B', 'KB', 'MB', 'GB'):
            if tam < 1024:
                return f'{tam:.1f} {unidad}'
            tam /= 1024
        return f'{tam:.1f} TB'
