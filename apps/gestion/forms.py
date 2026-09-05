"""Formularios del módulo de gestión."""
import re

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .validadores import redimensionar_foto
from .models import (
    Alumno,
    Clase,
    ConfiguracionAlertas,
    DiaSemana,
    NotaInterna,
    Pago,
    Plan,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# RUT chileno
# ---------------------------------------------------------------------------
def limpiar_rut(valor):
    return re.sub(r'[^0-9kK]', '', valor or '').upper()


def digito_verificador(cuerpo):
    suma = 0
    multiplo = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1
    resto = 11 - (suma % 11)
    if resto == 11:
        return '0'
    if resto == 10:
        return 'K'
    return str(resto)


def formatear_rut(valor):
    """12345678K -> 12.345.678-K"""
    limpio = limpiar_rut(valor)
    if len(limpio) < 2:
        return limpio
    cuerpo, dv = limpio[:-1], limpio[-1]
    with_dots = f'{int(cuerpo):,}'.replace(',', '.')
    return f'{with_dots}-{dv}'


def validar_rut(valor):
    """Valida y devuelve el RUT normalizado. Lanza ValidationError si no sirve.

    La validación se hace también en el servidor: la del navegador es
    comodidad, no seguridad.
    """
    limpio = limpiar_rut(valor)
    if len(limpio) < 8:
        raise forms.ValidationError('El RUT es demasiado corto.')
    cuerpo, dv = limpio[:-1], limpio[-1]
    if not cuerpo.isdigit():
        raise forms.ValidationError('El RUT solo puede tener números y dígito verificador K.')
    if digito_verificador(cuerpo) != dv:
        raise forms.ValidationError('El dígito verificador no corresponde al RUT.')
    return formatear_rut(limpio)


class MixinWidgets:
    """Aplica las clases del panel a todos los campos de una vez."""

    clases_por_defecto = 'g-input'

    def estilizar(self):
        for nombre, campo in self.fields.items():
            widget = campo.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple,
                                   forms.RadioSelect, forms.FileInput,
                                   forms.ClearableFileInput)):
                continue
            existentes = widget.attrs.get('class', '')
            widget.attrs['class'] = f'{existentes} {self.clases_por_defecto}'.strip()


# ---------------------------------------------------------------------------
# Alumno
# ---------------------------------------------------------------------------
class AlumnoForm(MixinWidgets, forms.ModelForm):
    class Meta:
        model = Alumno
        fields = [
            'nombre_completo', 'rut', 'fecha_nacimiento', 'genero', 'foto', 'estado',
            'telefono', 'email', 'direccion',
            'contacto_emergencia', 'telefono_emergencia', 'relacion_emergencia',
            'observaciones',
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
            'rut': forms.TextInput(attrs={
                'placeholder': '12.345.678-9',
                'data-rut': 'true',
                'data-aviso': '#avisoRut',
                'autocomplete': 'off',
            }),
            'telefono': forms.TextInput(attrs={
                'placeholder': '+56 9 1234 5678', 'data-telefono': 'true',
            }),
            'telefono_emergencia': forms.TextInput(attrs={
                'placeholder': '+56 9 1234 5678', 'data-telefono': 'true',
            }),
            'nombre_completo': forms.TextInput(attrs={'placeholder': 'Nombre y apellidos'}),
            'email': forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.cl'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['direccion'].required = False
        self.fields['email'].required = False
        self.fields['telefono'].required = False
        self.fields['fecha_nacimiento'].required = False
        self.fields['observaciones'].required = False
        self.fields['contacto_emergencia'].required = True
        self.fields['telefono_emergencia'].required = True
        self.estilizar()

    def clean_rut(self):
        rut = validar_rut(self.cleaned_data['rut'])
        existente = Alumno.todos.filter(rut=rut)
        if self.instance.pk:
            existente = existente.exclude(pk=self.instance.pk)
        if existente.exists():
            raise forms.ValidationError('Ya hay un alumno registrado con este RUT.')
        return rut

    def clean_foto(self):
        """Reduce la imagen antes de guardarla y le quita los metadatos.

        El EXIF de una foto de celular puede traer las coordenadas del
        lugar donde se tomó: eso no tiene por qué quedar guardado.
        """
        foto = self.cleaned_data.get('foto')
        if foto and hasattr(foto, 'content_type'):
            return redimensionar_foto(foto)
        return foto

    def clean_fecha_nacimiento(self):
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if fecha and fecha > timezone.localdate():
            raise forms.ValidationError('La fecha de nacimiento no puede estar en el futuro.')
        return fecha


class RadioPlanes(forms.RadioSelect):
    """Radios de plan que llevan su precio en el HTML.

    Sin esto el navegador no sabe cuánto cuesta el plan que se acaba de
    marcar, y el monto habría que pedirlo al servidor o repetirlo a mano
    en la plantilla.
    """

    def create_option(self, name, value, *args, **kwargs):
        opcion = super().create_option(name, value, *args, **kwargs)
        plan = getattr(value, 'instance', None)
        if plan is not None:
            opcion['attrs']['data-precio'] = plan.precio_clp
            opcion['attrs']['data-nombre'] = plan.nombre
        return opcion


class InscripcionPlanForm(forms.Form):
    """Paso 3 del alta: clases y plan contratado."""

    clases = forms.ModelMultipleChoiceField(
        queryset=Clase.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Clases a las que asistirá',
    )
    plan = forms.ModelChoiceField(
        queryset=Plan.objects.none(),
        required=False,
        widget=RadioPlanes,
        label='Plan contratado',
        empty_label=None,
    )
    fecha_inicio = forms.DateField(
        required=False,
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'g-input'}, format='%Y-%m-%d'),
        label='Fecha de inicio del plan',
    )
    pago_matricula = forms.BooleanField(
        required=False,
        label='¿Pagó matrícula?',
        widget=forms.CheckboxInput(attrs={'data-muestra': '#bloqueMatricula'}),
    )
    monto_matricula = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'g-input', 'placeholder': '0'}),
        label='Monto de la matrícula (CLP)',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['clases'].queryset = Clase.objects.filter(activa=True).select_related('profesora')
        self.fields['plan'].queryset = Plan.objects.filter(activo=True)

    def clean(self):
        datos = super().clean()
        if datos.get('plan') and not datos.get('fecha_inicio'):
            self.add_error('fecha_inicio', 'Indica desde cuándo corre el plan.')
        if datos.get('pago_matricula') and not datos.get('monto_matricula'):
            self.add_error('monto_matricula', 'Indica el monto de la matrícula.')
        return datos


class PagoInicialForm(forms.Form):
    """Paso 4 del alta: primer pago (opcional)."""

    monto_clp = forms.IntegerField(
        required=False, min_value=0,
        # data-monto-auto: el JS escribe acá el precio del plan elegido,
        # pero solo mientras el admin no lo haya tocado a mano.
        widget=forms.NumberInput(attrs={
            'class': 'g-input',
            'placeholder': '0',
            'data-monto-auto': '',
        }),
        label='Monto pagado (CLP)',
    )
    metodo = forms.ChoiceField(
        required=False, choices=Pago.Metodo.choices,
        widget=forms.Select(attrs={'class': 'g-input'}),
        label='Método de pago',
    )
    numero_comprobante = forms.CharField(
        required=False, max_length=50,
        widget=forms.TextInput(attrs={'class': 'g-input', 'placeholder': 'Opcional'}),
        label='N° de comprobante',
    )
    nota_interna = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'g-input', 'rows': 3,
                                     'placeholder': 'Observaciones internas'}),
        label='Observaciones internas',
    )


class NotaInternaForm(forms.ModelForm):
    class Meta:
        model = NotaInterna
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={
                'class': 'g-input', 'rows': 3,
                'placeholder': 'Anota algo sobre este alumno...',
            }),
        }


class RenovarPlanForm(forms.Form):
    plan = forms.ModelChoiceField(
        queryset=Plan.objects.none(),
        widget=forms.Select(attrs={'class': 'g-input'}),
        label='Nuevo plan',
    )
    fecha_inicio = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'g-input'}, format='%Y-%m-%d'),
        label='Desde',
    )
    registrar_pago = forms.BooleanField(
        required=False, initial=True,
        label='Registrar también el pago de este plan',
    )
    metodo = forms.ChoiceField(
        required=False, choices=Pago.Metodo.choices,
        widget=forms.Select(attrs={'class': 'g-input'}),
        label='Método de pago',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plan'].queryset = Plan.objects.filter(activo=True)


# ---------------------------------------------------------------------------
# Clase
# ---------------------------------------------------------------------------
class ClaseForm(MixinWidgets, forms.ModelForm):
    dias = forms.MultipleChoiceField(
        choices=DiaSemana.choices,
        widget=forms.CheckboxSelectMultiple,
        label='Días de la semana',
    )

    class Meta:
        model = Clase
        fields = [
            'nombre', 'categoria', 'descripcion', 'nivel', 'edad_minima',
            'hora_inicio', 'hora_fin', 'sala', 'cupo_maximo',
            'precio_clase_suelta', 'profesora', 'activa',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
            'hora_fin': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['profesora'].queryset = User.objects.filter(rol=User.Rol.PROFESOR)
        self.fields['profesora'].required = False
        self.fields['descripcion'].required = False
        self.fields['precio_clase_suelta'].required = False
        # El area decide en que pagina del sitio sale la clase. Sin ella la
        # clase existe pero no aparece agrupada en /clases/.
        self.fields['categoria'].required = False
        self.fields['edad_minima'].required = False
        if self.instance.pk:
            self.fields['dias'].initial = self.instance.dias_lista
        self.estilizar()

    def clean(self):
        datos = super().clean()
        inicio, fin = datos.get('hora_inicio'), datos.get('hora_fin')
        if inicio and fin and fin <= inicio:
            self.add_error('hora_fin', 'La hora de término debe ser posterior al inicio.')
        return datos

    def save(self, commit=True):
        clase = super().save(commit=False)
        # Se guardan en el orden de la semana, no en el que los marcó el usuario.
        orden = [c for c, _ in DiaSemana.choices]
        elegidos = set(self.cleaned_data['dias'])
        clase.dias_semana = ','.join(c for c in orden if c in elegidos)
        if commit:
            clase.save()
        return clase


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------
class PlanForm(MixinWidgets, forms.ModelForm):
    class Meta:
        model = Plan
        fields = ['nombre', 'precio_clp', 'duracion_dias', 'descripcion', 'activo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Plan 2 veces por semana'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descripcion'].required = False
        self.estilizar()


# ---------------------------------------------------------------------------
# Pago
# ---------------------------------------------------------------------------
class PagoForm(MixinWidgets, forms.ModelForm):
    class Meta:
        model = Pago
        fields = [
            'alumno', 'concepto', 'detalle', 'monto_clp', 'metodo',
            'numero_comprobante', 'fecha_pago', 'estado', 'nota_interna',
        ]
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'nota_interna': forms.Textarea(attrs={'rows': 3}),
            'detalle': forms.TextInput(attrs={'placeholder': 'Solo si el concepto es "Otro"'}),
            'numero_comprobante': forms.TextInput(attrs={'placeholder': 'Opcional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['alumno'].queryset = Alumno.objects.all()
        self.fields['detalle'].required = False
        self.fields['numero_comprobante'].required = False
        self.fields['nota_interna'].required = False
        self.estilizar()

    def clean(self):
        datos = super().clean()
        if datos.get('concepto') == Pago.Concepto.OTRO and not datos.get('detalle'):
            self.add_error('detalle', 'Describe el concepto cuando eliges "Otro".')
        return datos


# ---------------------------------------------------------------------------
# Profesoras
# ---------------------------------------------------------------------------
class ProfesoraForm(MixinWidgets, forms.ModelForm):
    password1 = forms.CharField(
        required=False, label='Contraseña', widget=forms.PasswordInput(attrs={'class': 'g-input'}),
        help_text='Si la dejas en blanco, se le manda un enlace para que la '
                  'elija ella misma. Es lo recomendable.',
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'telefono',
                  'rut', 'especialidad', 'is_active']
        widgets = {
            'rut': forms.TextInput(attrs={
                'placeholder': '12.345.678-9', 'data-rut': 'true', 'autocomplete': 'off',
            }),
            'telefono': forms.TextInput(attrs={
                'placeholder': '+56 9 1234 5678', 'data-telefono': 'true',
            }),
            'especialidad': forms.TextInput(attrs={'placeholder': 'Ej: Salsa y Bachata'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ('email', 'telefono', 'rut', 'especialidad'):
            self.fields[campo].required = False
        self.fields['first_name'].required = True
        self.fields['first_name'].label = 'Nombre'
        self.fields['last_name'].label = 'Apellido'
        self.fields['username'].label = 'Usuario para entrar al sistema'
        self.estilizar()

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if not rut:
            return None  # unique=True con null=True: mejor NULL que cadena vacía.
        rut = validar_rut(rut)
        existente = User.objects.filter(rut=rut)
        if self.instance.pk:
            existente = existente.exclude(pk=self.instance.pk)
        if existente.exists():
            raise forms.ValidationError('Ya hay un usuario con este RUT.')
        return rut

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol = User.Rol.PROFESOR
        clave = self.cleaned_data.get('password1')
        if clave:
            usuario.set_password(clave)
        if commit:
            usuario.save()
        return usuario


# ---------------------------------------------------------------------------
# Configuración de alertas
# ---------------------------------------------------------------------------
class ConfiguracionAlertasForm(MixinWidgets, forms.ModelForm):
    class Meta:
        model = ConfiguracionAlertas
        fields = ['dias_anticipacion', 'emails_destino', 'hora_envio', 'envio_activo',
                  'enviar_bienvenida', 'enviar_recibos', 'enviar_recordatorios']
        widgets = {
            'emails_destino': forms.Textarea(attrs={'rows': 2}),
            'hora_envio': forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.estilizar()
