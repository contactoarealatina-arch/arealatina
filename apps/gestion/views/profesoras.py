"""Módulo 9 — Gestión de profesoras."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render

from apps.asistencia.models import RegistroAsistencia

from ..auditoria import registrar
from ..correos import enviar_bienvenida_profesora
from ..forms import ProfesoraForm
from ..models import AuditLog, Clase
from ..permisos import gestion_requerida

User = get_user_model()


def _url_activacion(token):
    from django.conf import settings
    from django.urls import reverse

    if not token:
        return ''
    base = getattr(settings, 'SITIO_URL', 'http://localhost:8000').rstrip('/')
    return base + reverse('portal:activar', args=[token.token])


@gestion_requerida
def profesoras(request):
    equipo = User.objects.filter(rol=User.Rol.PROFESOR).prefetch_related('clases_dictadas')
    return render(request, 'gestion/profesoras/listado.html', {
        'activo': 'profesoras',
        'profesoras': equipo,
        'total': equipo.count(),
    })


@gestion_requerida
def profesora_nueva(request):
    if request.method == 'POST':
        form = ProfesoraForm(request.POST)
        if form.is_valid():
            profesora = form.save()
            registrar(request, AuditLog.Accion.CREAR, profesora,
                      f'Creó a la profesora {profesora.get_full_name()}')

            # Sin contraseña puesta a mano, se le manda un enlace para que
            # la elija ella: así nadie más la conoce.
            from apps.portal.cuentas import crear_acceso_profesora

            sin_clave = not form.cleaned_data.get('password1')
            token = crear_acceso_profesora(profesora, sin_clave)
            enlace = _url_activacion(token)

            aviso = 'Profesora registrada.'
            if profesora.email:
                enviado, motivo = enviar_bienvenida_profesora(profesora, enlace)
                aviso += (' Le mandamos la bienvenida con su acceso.' if enviado
                          else f' No salió el correo ({motivo})')
            else:
                aviso += ' Sin email no se le puede mandar la bienvenida.'
            messages.success(request, aviso)
            return redirect('gestion:profesora_detalle', pk=profesora.pk)
        messages.error(request, 'Revisa los datos.')
    else:
        form = ProfesoraForm()

    return render(request, 'gestion/profesoras/formulario.html', {
        'activo': 'profesoras', 'form': form, 'editando': False,
    })


@gestion_requerida
def profesora_editar(request, pk):
    profesora = get_object_or_404(User, pk=pk, rol=User.Rol.PROFESOR)

    if request.method == 'POST':
        # Antes de guardar: despues form.save() ya piso el valor viejo.
        email_anterior = profesora.email

        form = ProfesoraForm(request.POST, instance=profesora)
        if form.is_valid():
            profesora = form.save()
            registrar(request, AuditLog.Accion.EDITAR, profesora,
                      f'Editó a la profesora {profesora.get_full_name()}')
            messages.success(request, 'Datos actualizados.')

            if 'email' in form.changed_data and profesora.email:
                request.session['email_corregido'] = {
                    'profesora': profesora.pk,
                    'anterior': email_anterior or '(estaba vacío)',
                    'nuevo': profesora.email,
                }

            return redirect('gestion:profesora_detalle', pk=profesora.pk)
        messages.error(request, 'Revisa los datos.')
    else:
        form = ProfesoraForm(instance=profesora)

    return render(request, 'gestion/profesoras/formulario.html', {
        'activo': 'profesoras', 'form': form, 'profesora': profesora, 'editando': True,
    })


@gestion_requerida
def profesora_reenviar_acceso(request, pk):
    """Genera un token nuevo y reenvía la bienvenida a la profesora.

    Mismo caso que en los alumnos: si el email estaba mal escrito, ella
    nunca recibió el enlace y el anterior no le sirve a nadie.
    """
    if request.method != 'POST':
        return redirect('gestion:profesora_detalle', pk=pk)

    profesora = get_object_or_404(User, pk=pk, rol=User.Rol.PROFESOR)

    if not profesora.email:
        messages.error(request, 'La profesora no tiene email registrado.')
        return redirect('gestion:profesora_detalle', pk=pk)

    from apps.portal.cuentas import crear_acceso_profesora

    anterior = request.POST.get('anterior', '')
    token = crear_acceso_profesora(profesora, True)
    enviado, motivo = enviar_bienvenida_profesora(profesora, _url_activacion(token))

    detalle = f'Reenvió el acceso de {profesora.get_full_name()} a {profesora.email}'
    if anterior:
        detalle = (f'Email corregido de {anterior} a {profesora.email}, '
                   f'correo reenviado')
    registrar(request, AuditLog.Accion.EDITAR, profesora, detalle)

    if enviado:
        messages.success(
            request,
            f'Correo reenviado a {profesora.email}. '
            f'El enlace anterior quedó anulado.',
        )
    else:
        messages.error(request, f'No se pudo reenviar: {motivo}')

    return redirect('gestion:profesora_detalle', pk=pk)


@gestion_requerida
def profesora_detalle(request, pk):
    profesora = get_object_or_404(User, pk=pk, rol=User.Rol.PROFESOR)

    # Se saca de la sesion al leerlo: se ofrece una vez, no siempre.
    email_corregido = request.session.pop('email_corregido', None)
    if email_corregido and email_corregido.get('profesora') != profesora.pk:
        email_corregido = None

    clases = Clase.objects.filter(profesora=profesora).prefetch_related('inscripciones')

    # Últimas fechas en que pasó lista, agrupadas por clase y día.
    marcas = (
        RegistroAsistencia.objects.filter(clase__profesora=profesora)
        .select_related('clase')
        .order_by('-fecha')
    )
    vistas = set()
    sesiones = []
    for marca in marcas[:200]:
        llave = (marca.clase_id, marca.fecha)
        if llave in vistas:
            continue
        vistas.add(llave)
        sesiones.append({
            'clase': marca.clase,
            'fecha': marca.fecha,
            'total': RegistroAsistencia.objects.filter(
                clase=marca.clase, fecha=marca.fecha).count(),
        })
        if len(sesiones) >= 15:
            break

    return render(request, 'gestion/profesoras/detalle.html', {
        'activo': 'profesoras',
        'profesora': profesora,
        'email_corregido': email_corregido,
        'clases': clases,
        'sesiones': sesiones,
        'total_marcas': marcas.count(),
    })
