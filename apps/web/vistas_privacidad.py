"""Páginas públicas de protección de datos personales.

La Ley 21.719 exige informar qué datos se tratan y ofrecer una vía para
que cualquier persona ejerza sus derechos. Estas dos vistas son esa vía.
"""
from django import forms
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render

from apps.gestion.models import SolicitudARCO


class SolicitudARCOForm(forms.ModelForm):
    acepta = forms.BooleanField(
        required=True,
        label='Declaro que los datos entregados son míos o tengo autorización '
              'para solicitarlos.',
    )

    class Meta:
        model = SolicitudARCO
        fields = ['nombre', 'email', 'identificador', 'tipo', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Tu nombre completo'}),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 'placeholder': 'correo@ejemplo.cl'}),
            'identificador': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'RUT o el correo con el que estás registrado'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'Cuéntanos qué necesitas...'}),
        }
        labels = {
            'identificador': 'RUT o email con el que estás registrado',
            'descripcion': 'Detalle de tu solicitud',
        }


def politica_privacidad(request):
    return render(request, 'web/privacidad.html', {
        'seccion': 'privacidad',
        'actualizada': '28 de agosto de 2026',
    })


def mis_derechos(request):
    if request.method == 'POST':
        form = SolicitudARCOForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.ip = _ip(request)
            solicitud.save()

            _avisar(solicitud)

            messages.success(
                request,
                f'Recibimos tu solicitud. Tu número de caso es {solicitud.codigo}. '
                'Te escribimos a tu correo con la confirmación y tienes '
                'respuesta dentro de 30 días.'
            )
            return redirect('web:mis_derechos')
        messages.error(request, 'Revisa los datos del formulario.')
    else:
        form = SolicitudARCOForm()

    return render(request, 'web/mis_derechos.html', {
        'seccion': 'derechos',
        'form': form,
        'plazo': SolicitudARCO.DIAS_PLAZO,
    })


def _ip(request):
    reenviada = request.META.get('HTTP_X_FORWARDED_FOR')
    if reenviada:
        return reenviada.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _avisar(solicitud):
    """Confirma al solicitante y avisa al equipo. Si el correo falla, la
    solicitud ya quedó guardada: nunca se pierde."""
    from apps.gestion import correos
    from apps.gestion.models import AuditLog, CorreoEnviado

    try:
        correos._enviar(
            tipo=CorreoEnviado.Tipo.CONTACTO,
            destinatarios=[solicitud.email],
            asunto=f'Recibimos tu solicitud {solicitud.codigo} · Área Latina Estudio',
            plantilla='arco_confirmacion',
            contexto={'solicitud': solicitud},
            referencia=f'ARCO-OK-{solicitud.pk}',
        )
        correos._enviar(
            tipo=CorreoEnviado.Tipo.CONTACTO,
            destinatarios=[settings.ACADEMIA['email']],
            asunto=f'Nueva solicitud de datos personales · {solicitud.codigo}',
            plantilla='arco_aviso_equipo',
            contexto={'solicitud': solicitud},
            referencia=f'ARCO-EQ-{solicitud.pk}',
        )
    except Exception:
        pass

    try:
        AuditLog.objects.create(
            accion='ARCO', modelo='SolicitudARCO', objeto_id=solicitud.pk,
            descripcion=f'{solicitud.get_tipo_display()} de {solicitud.nombre}',
            ip=solicitud.ip,
        )
    except Exception:
        pass
