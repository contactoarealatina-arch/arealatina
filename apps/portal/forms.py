"""Formularios del portal del alumno."""
from django import forms
from django.contrib.auth import password_validation

from apps.gestion.models import Alumno


class ClaveNuevaForm(forms.Form):
    """Elegir contraseña al activar la cuenta."""

    clave1 = forms.CharField(
        label='Tu nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'p-campo', 'autocomplete': 'new-password',
            'placeholder': 'Mínimo 8 caracteres',
        }),
    )
    clave2 = forms.CharField(
        label='Repítela',
        widget=forms.PasswordInput(attrs={
            'class': 'p-campo', 'autocomplete': 'new-password',
            'placeholder': 'La misma de arriba',
        }),
    )

    def __init__(self, usuario, *args, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean_clave1(self):
        clave = self.cleaned_data['clave1']

        # El RUT es lo primero que probaría alguien que la quiera adivinar.
        ficha = getattr(self.usuario, 'ficha_alumno', None)
        rut = (ficha.rut if ficha else self.usuario.rut) or ''
        rut_limpio = rut.replace('.', '').replace('-', '')
        if rut_limpio and clave.replace('.', '').replace('-', '') == rut_limpio:
            raise forms.ValidationError(
                'No puedes usar tu RUT como contraseña: es demasiado fácil de adivinar.'
            )

        password_validation.validate_password(clave, self.usuario)
        return clave

    def clean(self):
        datos = super().clean()
        if datos.get('clave1') and datos.get('clave2') and datos['clave1'] != datos['clave2']:
            self.add_error('clave2', 'Las dos contraseñas no coinciden.')
        return datos

    def guardar(self):
        self.usuario.set_password(self.cleaned_data['clave1'])
        self.usuario.save(update_fields=['password'])
        return self.usuario


class CambiarClaveForm(ClaveNuevaForm):
    """Igual que la anterior, pero pidiendo la contraseña actual."""

    clave_actual = forms.CharField(
        label='Tu contraseña actual',
        widget=forms.PasswordInput(attrs={
            'class': 'p-campo', 'autocomplete': 'current-password',
        }),
    )

    field_order = ['clave_actual', 'clave1', 'clave2']

    def clean_clave_actual(self):
        actual = self.cleaned_data['clave_actual']
        if not self.usuario.check_password(actual):
            raise forms.ValidationError('Esa no es tu contraseña actual.')
        return actual


class PerfilForm(forms.ModelForm):
    """Lo que el alumno puede cambiar por su cuenta.

    El email queda fuera a propósito: es la llave de su acceso y de los
    correos, así que lo cambia la administración.
    """

    class Meta:
        model = Alumno
        fields = [
            'telefono', 'direccion', 'foto',
            'contacto_emergencia', 'telefono_emergencia', 'relacion_emergencia',
        ]
        widgets = {
            'telefono': forms.TextInput(attrs={
                'class': 'p-campo', 'placeholder': '+56 9 1234 5678',
                'data-telefono': 'true', 'inputmode': 'tel',
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'p-campo', 'placeholder': 'Calle y número',
            }),
            'contacto_emergencia': forms.TextInput(attrs={
                'class': 'p-campo', 'placeholder': 'Nombre de quien avisar',
            }),
            'telefono_emergencia': forms.TextInput(attrs={
                'class': 'p-campo', 'placeholder': '+56 9 1234 5678',
                'data-telefono': 'true', 'inputmode': 'tel',
            }),
            'relacion_emergencia': forms.Select(attrs={'class': 'p-campo'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['direccion'].required = False
        self.fields['telefono'].required = False
