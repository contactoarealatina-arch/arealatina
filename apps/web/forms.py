"""Formularios del sitio publico."""
from django import forms

from .models import MensajeContacto


class ContactoForm(forms.ModelForm):
    class Meta:
        model = MensajeContacto
        fields = ['nombre', 'email', 'telefono', 'mensaje']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tu nombre',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'tucorreo@ejemplo.com',
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+56 9 1234 5678',
            }),
            'mensaje': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Cuentanos que clase te interesa...',
            }),
        }
