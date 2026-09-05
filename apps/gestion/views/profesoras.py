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
            if profesora.correo_de_contacto:
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
        email_anterior = profesora.correo_personal

        form = ProfesoraForm(request.POST, instance=profesora)
        if form.is_valid():
            profesora = form.save()
            registrar(request, AuditLog.Accion.EDITAR, profesora,
                      f'Editó a la profesora {profesora.get_full_name()}')
            messages.success(request, 'Datos actualizados.')

            if 'correo_personal' in form.changed_data and profesora.correo_personal:
                request.session['email_corregido'] = {
                    'profesora': profesora.pk,
                    'anterior': email_anterior or '(estaba vacío)',
                    'nuevo': profesora.correo_personal,
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

    if not profesora.correo_de_contacto:
        messages.error(request, 'La profesora no tiene correo personal registrado.')
        return redirect('gestion:profesora_detalle', pk=pk)

    from apps.portal.cuentas import crear_acceso_profesora

    anterior = request.POST.get('anterior', '')
    token = crear_acceso_profesora(profesora, True)
    enviado, motivo = enviar_bienvenida_profesora(profesora, _url_activacion(token))

    detalle = f'Reenvió el acceso de {profesora.get_full_name()} a {profesora.correo_de_contacto}'
    if anterior:
        detalle = (f'Email corregido de {anterior} a {profesora.correo_de_contacto}, '
                   f'correo reenviado')
    registrar(request, AuditLog.Accion.EDITAR, profesora, detalle)

    if enviado:
        messages.success(
            request,
            f'Correo reenviado a {profesora.correo_de_contacto}. '
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


@gestion_requerida
def profesora_alternar(request, pk):
    """Da de baja o reactiva a una profesora sin borrar su historial.

    Al desactivarla deja de poder entrar al portal en el acto, pero sus
    clases y la asistencia que pasó siguen ahí.
    """
    if request.method != 'POST':
        return redirect('gestion:profesoras')

    profesora = get_object_or_404(User, pk=pk, rol=User.Rol.PROFESOR)
    profesora.is_active = not profesora.is_active
    profesora.save(update_fields=['is_active', 'updated_at'])

    verbo = 'Reactivó' if profesora.is_active else 'Dio de baja'
    registrar(request, AuditLog.Accion.EDITAR, profesora,
              f'{verbo} a {profesora.get_full_name()}')

    if profesora.is_active:
        messages.success(request, f'{profesora.get_full_name()} puede entrar de nuevo.')
    else:
        messages.success(
            request,
            f'{profesora.get_full_name()} quedó dada de baja y ya no puede '
            f'entrar al portal. Sus clases y su historial siguen guardados.',
        )
    return redirect('gestion:profesoras')


@gestion_requerida
def profesora_eliminar(request, pk):
    """Borra a una profesora, solo si no dejó rastro.

    Con clases asignadas o asistencia pasada, borrarla dejaría esas clases
    huérfanas y perdería quién pasó lista. En ese caso se da de baja.
    """
    if request.method != 'POST':
        return redirect('gestion:profesoras')

    profesora = get_object_or_404(User, pk=pk, rol=User.Rol.PROFESOR)

    clases = Clase.objects.filter(profesora=profesora).count()
    marcas = RegistroAsistencia.objects.filter(clase__profesora=profesora).count()

    if clases or marcas:
        messages.error(
            request,
            f'No se puede eliminar a {profesora.get_full_name()}: tiene '
            f'{clases} clase{"s" if clases != 1 else ""} asignada'
            f'{"s" if clases != 1 else ""} y {marcas} '
            f'registro{"s" if marcas != 1 else ""} de asistencia. '
            f'Dale de baja: pierde el acceso al instante y el historial '
            f'se conserva.',
        )
        return redirect('gestion:profesoras')

    nombre = profesora.get_full_name() or profesora.username
    registrar(request, AuditLog.Accion.ELIMINAR, profesora, f'Eliminó a {nombre}')
    profesora.delete()
    messages.success(request, f'{nombre} fue eliminada.')
    return redirect('gestion:profesoras')
