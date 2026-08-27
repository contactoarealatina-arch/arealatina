"""Vistas del sitio publico de Area Latina Estudio.

Los textos visibles van con tildes y enes correctas: son los que lee el
visitante. Los comentarios y nombres de variables van sin tildes.
"""
from django.contrib import messages
from django.shortcuts import redirect, render

from apps.gestion.models import Clase, Plan

from .forms import ContactoForm

ESTILOS_HOME = [
    {
        'emoji': '\U0001F483',
        'nombre': 'Salsa',
        'slug': 'SALSA',
        'texto': 'Ritmo caribeño, giros y mucha energía. Aprende desde los pasos '
                 'básicos hasta figuras en pareja.',
    },
    {
        'emoji': '\U0001F339',
        'nombre': 'Bachata',
        'slug': 'BACHATA',
        'texto': 'Sensualidad y conexión. El baile más romántico del Caribe, '
                 'paso a paso y sin apuro.',
    },
    {
        'emoji': '\U0001F525',
        'nombre': 'Reggaetón',
        'slug': 'REGGAETON',
        'texto': 'Actitud, fuerza y coreografías urbanas al ritmo de lo que suena hoy.',
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
        'texto': 'Elegancia, postura y abrazo. Una tradición que se baila con el alma.',
    },
    {
        'emoji': '\U0001F476',
        'nombre': 'Kids Dance',
        'slug': 'KIDS',
        'texto': 'Clases lúdicas para niños y niñas: coordinación, ritmo y mucha '
                 'diversión en grupo.',
    },
]

BENEFICIOS = [
    {
        'icono': 'bi-award',
        'titulo': 'Profesores con experiencia',
        'texto': 'Nuestro equipo lleva años sobre el escenario y en la sala de clases. '
                 'Te acompañamos desde tu primer paso.',
    },
    {
        'icono': 'bi-people',
        'titulo': 'Ambiente familiar',
        'texto': 'Acá nadie mira mal a quien recién empieza. Se baila, se ríe y se hacen '
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
        'nombre': 'Nombre Apellido',
        'especialidad': 'Salsa y Bachata',
        'bio': 'Bailarina y coreógrafa con años de experiencia en ritmos caribeños.',
    },
    {
        'nombre': 'Nombre Apellido',
        'especialidad': 'Reggaetón y Urbano',
        'bio': 'Especialista en estilos urbanos y coreografías de alto impacto.',
    },
    {
        'nombre': 'Nombre Apellido',
        'especialidad': 'Tango',
        'bio': 'Formado en tango de salón, enseña técnica, postura y conexión en pareja.',
    },
]

# OJO: cifras de referencia inventadas. Reemplazar por las reales antes de
# publicar el sitio.
ESTADISTICAS = [
    {'valor': 8, 'sufijo': '+', 'etiqueta': 'Años enseñando'},
    {'valor': 500, 'sufijo': '+', 'etiqueta': 'Alumnos'},
    {'valor': 6, 'sufijo': '', 'etiqueta': 'Estilos'},
    {'valor': 4, 'sufijo': '', 'etiqueta': 'Profesores'},
]

# OJO: testimonios ficticios. No pueden salir publicados asi: hay que
# reemplazarlos por opiniones reales o quitar la seccion.
TESTIMONIOS = [
    {
        'texto': 'Llegué sin saber mover un pie y a los dos meses ya estaba bailando '
                 'en la fiesta de fin de año. El ambiente hace toda la diferencia.',
        'nombre': 'Nombre Apellido',
        'detalle': 'Alumna de Bachata',
    },
    {
        'texto': 'Mi hija entró a Kids Dance con seis años. Se suelta, hace amigas y '
                 'llega feliz a la casa. Para mí eso vale más que cualquier cosa.',
        'nombre': 'Nombre Apellido',
        'detalle': 'Apoderado Kids Dance',
    },
    {
        'texto': 'Había probado otras academias y siempre me sentí el más nuevo. Acá '
                 'te acompañan de verdad hasta que te sale.',
        'nombre': 'Nombre Apellido',
        'detalle': 'Alumno de Salsa',
    },
]

# Galería: deja las fotos en static/img/galeria/ y agrégalas acá.
# Mientras la lista esté vacía, la sección NO se muestra en el sitio.
# Un mosaico de emojis gigantes se ve peor que no tener la sección.
GALERIA = [
    # {'imagen': 'img/galeria/clase-salsa.jpg',  'titulo': 'Clase de salsa'},
    # {'imagen': 'img/galeria/bachata.jpg',      'titulo': 'Bachata en pareja'},
    # {'imagen': 'img/galeria/reggaeton.jpg',    'titulo': 'Grupo de reggaetón'},
    # {'imagen': 'img/galeria/urbano.jpg',       'titulo': 'Taller urbano'},
    # {'imagen': 'img/galeria/kids.jpg',         'titulo': 'Kids Dance'},
    # {'imagen': 'img/galeria/muestra.jpg',      'titulo': 'Muestra de fin de año'},
]

PREGUNTAS = [
    {
        'p': '¿Nunca he bailado, sirve igual?',
        'r': 'Sí. La mayoría llega sin experiencia. Los grupos iniciales parten desde '
             'el paso básico y nadie te va a apurar.',
    },
    {
        'p': '¿Necesito venir en pareja?',
        'r': 'No. Se puede venir solo o sola. En las clases de pareja vamos rotando, '
             'así que siempre hay con quien bailar.',
    },
    {
        'p': '¿Qué ropa tengo que usar?',
        'r': 'Ropa cómoda con la que puedas moverte y zapatillas limpias de suela lisa. '
             'Para tango y salsa avanzada conviene zapato de baile, pero no es obligatorio.',
    },
    {
        'p': '¿Puedo tomar una clase de prueba?',
        'r': 'Sí. Escríbenos y coordinamos una clase suelta para que conozcas al grupo '
             'antes de tomar un plan.',
    },
    {
        'p': '¿Desde qué edad reciben niños?',
        'r': 'Kids Dance recibe desde los 5 años. Para adultos no hay edad máxima: '
             'tenemos alumnos de todas las edades.',
    },
    {
        'p': '¿Cómo se pagan las clases?',
        'r': 'En efectivo en el estudio o por transferencia. Los planes son mensuales '
             'y también existe la opción de clase suelta.',
    },
]


def index(request):
    return render(request, 'web/index.html', {
        'seccion': 'inicio',
        'estilos': ESTILOS_HOME,
        'beneficios': BENEFICIOS,
        'estadisticas': ESTADISTICAS,
        'galeria': [g for g in GALERIA if g.get('imagen')],
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
    """Avisa al equipo del mensaje nuevo. Si falla, el mensaje ya está guardado."""
    from apps.gestion.correos import enviar_mensaje_contacto

    try:
        enviar_mensaje_contacto(mensaje)
    except Exception:
        pass
