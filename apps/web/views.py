"""Vistas del sitio publico de Area Latina Estudio."""
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect, render

from apps.gestion.models import Clase

from .forms import ContactoForm

ESTILOS_HOME = [
    {
        'emoji': '\U0001F483',
        'nombre': 'Salsa',
        'slug': 'SALSA',
        'texto': 'Ritmo caribeno, giros y mucha energia. Aprende desde los pasos '
                 'basicos hasta figuras en pareja.',
    },
    {
        'emoji': '\U0001F339',
        'nombre': 'Bachata',
        'slug': 'BACHATA',
        'texto': 'Sensualidad y conexion. El baile mas romantico del Caribe, '
                 'paso a paso y sin apuro.',
    },
    {
        'emoji': '\U0001F525',
        'nombre': 'Reggaeton',
        'slug': 'REGGAETON',
        'texto': 'Actitud, fuerza y coreografias urbanas al ritmo de lo que suena hoy.',
    },
    {
        'emoji': '\U0001F3A4',
        'nombre': 'Urbano',
        'slug': 'URBANO',
        'texto': 'Hip hop, dancehall y estilo libre para soltar el cuerpo y crear '
                 'tu propio sello.',
    },
    {
        'emoji': '\U0001F3B6',
        'nombre': 'Tango',
        'slug': 'TANGO',
        'texto': 'Elegancia, postura y abrazo. Una tradicion que se baila con el alma.',
    },
    {
        'emoji': '\U0001F476',
        'nombre': 'Kids Dance',
        'slug': 'KIDS',
        'texto': 'Clases ludicas para ninos y ninas: coordinacion, ritmo y mucha '
                 'diversion en grupo.',
    },
]

BENEFICIOS = [
    {
        'icono': 'bi-award',
        'titulo': 'Profesores con experiencia',
        'texto': 'Nuestro equipo lleva anos sobre el escenario y en la sala de clases. '
                 'Te acompanamos desde tu primer paso.',
    },
    {
        'icono': 'bi-people',
        'titulo': 'Ambiente familiar',
        'texto': 'Aca nadie mira mal a quien recien empieza. Se baila, se rie y se hacen '
                 'amigos en cada clase.',
    },
    {
        'icono': 'bi-heart',
        'titulo': 'Todas las edades',
        'texto': 'Desde Kids Dance hasta grupos de adultos. Siempre hay un horario y un '
                 'nivel que te acomoda.',
    },
]

EQUIPO = [
    {
        'nombre': 'Profesora 1',
        'especialidad': 'Salsa y Bachata',
        'bio': 'Bailarina y coreografa con anos de experiencia en ritmos caribenos.',
    },
    {
        'nombre': 'Profesora 2',
        'especialidad': 'Reggaeton y Urbano',
        'bio': 'Especialista en estilos urbanos y coreografias de alto impacto.',
    },
    {
        'nombre': 'Profesor 3',
        'especialidad': 'Tango',
        'bio': 'Formado en tango de salon, ensena tecnica, postura y conexion en pareja.',
    },
]


def index(request):
    return render(request, 'web/index.html', {
        'seccion': 'inicio',
        'estilos': ESTILOS_HOME,
        'beneficios': BENEFICIOS,
    })


def clases(request):
    estilo = request.GET.get('estilo', '')
    qs = Clase.objects.filter(activa=True).select_related('profesora')
    if estilo:
        qs = qs.filter(nombre=estilo)
    return render(request, 'web/clases.html', {
        'seccion': 'clases',
        'clases': qs,
        'estilos': Clase.Estilo.choices,
        'estilo_activo': estilo,
    })


def nosotros(request):
    return render(request, 'web/nosotros.html', {
        'seccion': 'nosotros',
        'equipo': EQUIPO,
        'beneficios': BENEFICIOS,
    })


def contacto(request):
    if request.method == 'POST':
        form = ContactoForm(request.POST)
        if form.is_valid():
            mensaje = form.save()
            _notificar_por_email(mensaje)
            messages.success(
                request,
                'Gracias por escribirnos. Te responderemos a la brevedad.',
            )
            return redirect('web:contacto')
        messages.error(request, 'Revisa los datos del formulario, hay campos con errores.')
    else:
        form = ContactoForm()
    return render(request, 'web/contacto.html', {'seccion': 'contacto', 'form': form})


def _notificar_por_email(mensaje):
    """Envia el mensaje al correo de la academia. No interrumpe si el envio falla."""
    cuerpo = (
        f'Nombre: {mensaje.nombre}\n'
        f'Email: {mensaje.email}\n'
        f'Telefono: {mensaje.telefono or "No indicado"}\n\n'
        f'{mensaje.mensaje}'
    )
    send_mail(
        subject=f'Nuevo mensaje web de {mensaje.nombre}',
        message=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ACADEMIA['email']],
        fail_silently=True,
    )
