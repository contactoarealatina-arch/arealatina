"""Vistas del sitio publico de Area Latina Estudio."""
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import redirect, render

from apps.gestion.models import Clase, Plan

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


# OJO: cifras de referencia. Reemplazar por las reales de la academia.
ESTADISTICAS = [
    {'valor': 8, 'sufijo': '+', 'etiqueta': 'Anos ensenando'},
    {'valor': 500, 'sufijo': '+', 'etiqueta': 'Alumnos que han pasado'},
    {'valor': 6, 'sufijo': '', 'etiqueta': 'Estilos distintos'},
    {'valor': 4, 'sufijo': '', 'etiqueta': 'Profesores en sala'},
]

# OJO: testimonios de referencia. Reemplazar por opiniones reales.
TESTIMONIOS = [
    {
        'texto': 'Llegue sin saber mover un pie y a los dos meses ya estaba bailando '
                 'en la fiesta de fin de ano. El ambiente hace toda la diferencia.',
        'nombre': 'Nombre Apellido',
        'detalle': 'Alumna de Bachata',
    },
    {
        'texto': 'Mi hija entro a Kids Dance con seis anos. Se suelta, hace amigas y '
                 'llega feliz a la casa. Para mi eso vale mas que cualquier cosa.',
        'nombre': 'Nombre Apellido',
        'detalle': 'Apoderado Kids Dance',
    },
    {
        'texto': 'Habia probado otras academias y siempre me senti el mas nuevo. Aca '
                 'te acompanan de verdad hasta que te sale.',
        'nombre': 'Nombre Apellido',
        'detalle': 'Alumno de Salsa',
    },
]

# Galeria: cuando haya fotos reales, dejarlas en static/img/galeria/ y poner
# aqui la ruta en 'imagen' (ej: 'img/galeria/clase-salsa.jpg'). Mientras
# 'imagen' este vacio se muestra un mosaico de color con el emoji del estilo.
GALERIA = [
    {'imagen': '', 'emoji': '\U0001F483', 'titulo': 'Clase de salsa', 'alto': True},
    {'imagen': '', 'emoji': '\U0001F339', 'titulo': 'Bachata en pareja', 'alto': False},
    {'imagen': '', 'emoji': '\U0001F525', 'titulo': 'Grupo de reggaeton', 'alto': False},
    {'imagen': '', 'emoji': '\U0001F3A4', 'titulo': 'Taller urbano', 'alto': False},
    {'imagen': '', 'emoji': '\U0001F476', 'titulo': 'Kids Dance', 'alto': False},
    {'imagen': '', 'emoji': '\U0001F3B6', 'titulo': 'Muestra de fin de ano', 'alto': True},
]

PREGUNTAS = [
    {
        'p': 'Nunca he bailado, sirve igual?',
        'r': 'Si. La mayoria llega sin experiencia. Los grupos iniciales parten desde '
             'el paso basico y nadie te va a apurar.',
    },
    {
        'p': 'Necesito venir en pareja?',
        'r': 'No. Se puede venir solo o sola. En las clases de pareja vamos rotando, '
             'asi que siempre hay con quien bailar.',
    },
    {
        'p': 'Que ropa tengo que usar?',
        'r': 'Ropa comoda con la que puedas moverte y zapatillas limpias de suela lisa. '
             'Para tango y salsa avanzada conviene zapato de baile, pero no es obligatorio.',
    },
    {
        'p': 'Puedo tomar una clase de prueba?',
        'r': 'Si. Escribenos y coordinamos una clase suelta para que conozcas al grupo '
             'antes de tomar un plan.',
    },
    {
        'p': 'Desde que edad reciben ninos?',
        'r': 'Kids Dance recibe desde los 5 anos. Para adultos no hay edad maxima: '
             'tenemos alumnos de todas las edades.',
    },
    {
        'p': 'Como se pagan las clases?',
        'r': 'En efectivo en el estudio o por transferencia. Los planes son mensuales '
             'y tambien existe la opcion de clase suelta.',
    },
]


def index(request):
    return render(request, 'web/index.html', {
        'seccion': 'inicio',
        'estilos': ESTILOS_HOME,
        'beneficios': BENEFICIOS,
        'estadisticas': ESTADISTICAS,
        'galeria': GALERIA,
        'testimonios': TESTIMONIOS,
        'preguntas': PREGUNTAS,
        'planes': Plan.objects.filter(activo=True),
        'clases_destacadas': (
            Clase.objects.filter(activa=True)
            .select_related('profesora')
            .order_by('nombre', 'hora_inicio')[:3]
        ),
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
