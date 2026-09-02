"""Vistas del sitio público de Área Latina Estudio.

Los textos visibles van con tildes y eñes correctas: son los que lee el
visitante. Los comentarios y nombres de variables van sin tildes.

El sitio dejó de ser el folleto de una academia de baile: ahora tiene que
mostrar cinco áreas (danza, wellness, kids & teens, escena y compañías),
y esas áreas viven en la base de datos, no en listas dentro de este
archivo. Lo que sigue acá abajo son solo los textos institucionales que
nadie va a editar desde el panel.
"""
from datetime import time

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.gestion.models import Categoria, Clase, DiaSemana, Evento, Plan, Testimonio

from .forms import ContactoForm

# ---------------------------------------------------------------------------
# Textos institucionales
# ---------------------------------------------------------------------------

BENEFICIOS = [
    {
        'icono': 'bi-person-workspace',
        'titulo': 'Formación con acompañamiento',
        'texto': 'No entregamos una coreografía y listo. Se corrige técnica, se '
                 'avanza por nivel y cada persona sabe en qué está trabajando.',
    },
    {
        'icono': 'bi-calendar-week',
        'titulo': 'Horarios que se acomodan',
        'texto': 'Mañana, tarde y noche, de lunes a sábado. Si cambia tu semana, '
                 'cambias de horario según el cupo disponible.',
    },
    {
        'icono': 'bi-people',
        'titulo': 'Comunidad que motiva',
        'texto': 'Acá nadie mira mal a quien recién empieza. Se entrena, se ríe y '
                 'se hacen amigos en la misma sala.',
    },
    {
        'icono': 'bi-phone',
        'titulo': 'Todo desde tu celular',
        'texto': 'Reserva, plan y pagos en un solo lugar. Sin tener que preguntar '
                 'cada cosa por WhatsApp.',
    },
]

# Los cuatro pasos de la lámina 03 del brief.
COMO_EMPEZAR = [
    {
        'icono': 'bi-search',
        'titulo': 'Descubre',
        'texto': 'Explora las clases, los planes y los beneficios.',
    },
    {
        'icono': 'bi-clipboard-check',
        'titulo': 'Elige',
        'texto': 'Elige la opción que mejor se adapta a ti.',
    },
    {
        'icono': 'bi-person-plus',
        'titulo': 'Inscríbete',
        'texto': 'Completa tu inscripción de forma rápida y segura.',
    },
    {
        'icono': 'bi-phone',
        'titulo': 'Reserva en la app',
        'texto': 'Reserva tus clases y entrena cuando quieras.',
    },
]

EQUIPO = [
    {
        'nombre': '[Pendiente: nombre real]',
        'especialidad': 'Salsa y Bachata',
        'bio': 'Bailarina y coreógrafa con años de experiencia en ritmos caribeños.',
    },
    {
        'nombre': '[Pendiente: nombre real]',
        'especialidad': 'Reggaetón y Urbano',
        'bio': 'Especialista en estilos urbanos y coreografías de alto impacto.',
    },
    {
        'nombre': '[Pendiente: nombre real]',
        'especialidad': 'Tango',
        'bio': 'Formado en tango de salón, enseña técnica, postura y conexión en pareja.',
    },
]

# OJO: cifras de referencia. Reemplazar por las reales antes de publicar.
ESTADISTICAS = [
    {'valor': 8, 'sufijo': '+', 'etiqueta': 'Años enseñando'},
    {'valor': 500, 'sufijo': '+', 'etiqueta': 'Alumnos'},
    {'valor': 5, 'sufijo': '', 'etiqueta': 'Áreas'},
    {'valor': 4, 'sufijo': '', 'etiqueta': 'Profesores'},
]

VALORES = [
    {
        'icono': 'bi-compass',
        'titulo': 'Movimiento',
        'texto': 'El cuerpo se entrena bailando, estirando y fortaleciendo. '
                 'Las tres cosas caben en el mismo estudio.',
    },
    {
        'icono': 'bi-mortarboard',
        'titulo': 'Formación',
        'texto': 'Hay una ruta: se parte desde cero, se sube de nivel y se puede '
                 'llegar al escenario o a una compañía.',
    },
    {
        'icono': 'bi-heart',
        'titulo': 'Comunidad',
        'texto': 'La sala es de todos. Se comparte, se apoya y se celebra el '
                 'avance del que está al lado.',
    },
]

# Lo que ofrece la app, tal como está en la lámina 07 del brief.
APP_FUNCIONES = [
    {'icono': 'bi-calendar3', 'texto': 'Ver horarios'},
    {'icono': 'bi-clock', 'texto': 'Reservar clases'},
    {'icono': 'bi-credit-card', 'texto': 'Administrar su plan'},
    {'icono': 'bi-cash-coin', 'texto': 'Revisar pagos'},
    {'icono': 'bi-bell', 'texto': 'Recibir novedades'},
    {'icono': 'bi-gift', 'texto': 'Acceder a beneficios'},
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
        'p': '¿Puedo combinar danza con wellness?',
        'r': 'Sí, y es lo que recomendamos. El plan de dos cursos existe justamente '
             'para eso: una disciplina de baile y una de acondicionamiento.',
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
        'r': 'Kids & Teens recibe desde los 4 años. Para adultos no hay edad máxima: '
             'tenemos alumnos de todas las edades.',
    },
    {
        'p': '¿Cómo se pagan las clases?',
        'r': 'En efectivo en el estudio o por transferencia. Los planes son mensuales '
             'y también existe la opción de clase suelta.',
    },
]

# Galería: deja las fotos en static/img/galeria/ y agrégalas acá.
# Mientras la lista esté vacía, la sección NO se muestra en el sitio.
GALERIA = []


# ---------------------------------------------------------------------------
# Ayudantes
# ---------------------------------------------------------------------------

# Tramos horarios del buscador. La hora de inicio decide el tramo.
TRAMOS = {
    'manana': ('Mañana', time(0, 0), time(11, 59)),
    'tarde': ('Tarde', time(12, 0), time(17, 59)),
    'noche': ('Noche', time(18, 0), time(23, 59)),
}

# Tramos de edad. Las clases sin edad mínima se entienden como de adultos,
# que es como funciona el estudio hoy.
EDADES = {
    'kids': ('Niños/as (4 a 12)', 4, 12),
    'teens': ('Adolescentes (13 a 17)', 13, 17),
    'adultos': ('Adultos (18+)', 18, 120),
}


def _areas():
    return Categoria.objects.filter(activa=True)


def _clases_publicas():
    return (
        Clase.objects.filter(activa=True)
        .select_related('profesora', 'categoria')
        .order_by('hora_inicio', 'nombre')
    )


def _disciplinas_con_clases():
    """Solo las disciplinas que hoy tienen clase activa.

    Ofrecer un filtro que no devuelve nada es peor que no ofrecerlo.
    """
    usadas = set(_clases_publicas().values_list('nombre', flat=True))
    return [(c, n) for c, n in Clase.Estilo.choices if c in usadas]


def _buscar_clases(request):
    """Aplica los filtros del buscador de horarios. Devuelve (clases, filtros)."""
    dia = request.GET.get('dia', '')
    disciplina = request.GET.get('disciplina', '')
    nivel = request.GET.get('nivel', '')
    edad = request.GET.get('edad', '')
    tramo = request.GET.get('horario', '')
    area = request.GET.get('area', '')

    qs = _clases_publicas()

    if dia in dict(DiaSemana.choices):
        # Los dias se guardan como 'LU,MI': hay que buscar el codigo suelto.
        qs = qs.filter(dias_semana__contains=dia)
    if disciplina in dict(Clase.Estilo.choices):
        qs = qs.filter(nombre=disciplina)
    if nivel in dict(Clase.Nivel.choices):
        qs = qs.filter(nivel=nivel)
    if area:
        qs = qs.filter(categoria__slug=area)
    if tramo in TRAMOS:
        _, desde, hasta = TRAMOS[tramo]
        qs = qs.filter(hora_inicio__gte=desde, hora_inicio__lte=hasta)
    if edad in EDADES:
        _, desde, hasta = EDADES[edad]
        if edad == 'adultos':
            # Sin edad minima declarada = clase de adultos.
            qs = qs.filter(Q(edad_minima__isnull=True) | Q(edad_minima__gte=desde))
        else:
            qs = qs.filter(edad_minima__gte=desde, edad_minima__lte=hasta)

    filtros = {
        'dia': dia,
        'disciplina': disciplina,
        'nivel': nivel,
        'edad': edad,
        'horario': tramo,
        'area': area,
        'hay_filtro': any([dia, disciplina, nivel, edad, tramo, area]),
    }
    opciones = {
        'dias': DiaSemana.choices,
        'disciplinas': _disciplinas_con_clases(),
        'niveles': Clase.Nivel.choices,
        'edades': [(k, v[0]) for k, v in EDADES.items()],
        'tramos': [(k, v[0]) for k, v in TRAMOS.items()],
        'areas': _areas(),
    }
    return qs.distinct(), filtros, opciones


def _planes_del_sitio():
    """Los mensuales para el comparador; la clase suelta va aparte."""
    activos = Plan.objects.filter(activo=True)
    return (
        activos.filter(duracion_dias__gte=28),
        activos.filter(duracion_dias__lt=28).first(),
    )


# ---------------------------------------------------------------------------
# Vista previa al compartir el enlace
# ---------------------------------------------------------------------------
# Título y bajada que salen en WhatsApp e Instagram cuando alguien pega la
# URL. Van juntos en una tabla para que se lean de corrido y no se
# desperdiguen por el archivo.
OG = {
    'inicio': ('Área Latina Estudio · Cultura en movimiento',
               'Danza, bienestar, formación, escena y comunidad en Puerto Montt. '
               'Un espacio para aprender, crear, moverte y conectar.'),
    'clases': ('Clases y disciplinas · Área Latina Estudio',
               'Salsa, bachata, reggaetón, urbano, heels, tango, Kids & Teens y '
               'wellness. Explora por área, nivel y objetivo.'),
    'planes': ('Horarios y planes · Área Latina Estudio',
               'Busca tu clase por día, disciplina, nivel, edad y horario, y '
               'compara los planes. Sin preguntar nada por WhatsApp.'),
    'wellness': ('Wellness · Área Latina Estudio',
                 'Pilates Mat, Barre, Flexibilidad y Reformer en Puerto Montt. '
                 'Bienestar integral para mente, cuerpo y hábitos.'),
    'en-escena': ('En Escena · Área Latina Estudio',
                  'Muestras, competencias y compañías. Procesos formativos que '
                  'terminan arriba del escenario.'),
    'comunidad': ('Comunidad · Área Latina Estudio',
                  'Talleres, juntas y experiencias especiales. Conecta, comparte '
                  'y crece junto a otros.'),
    'nosotros': ('Nosotros · Área Latina Estudio',
                 'Un ecosistema de movimiento, bienestar, formación y comunidad '
                 'en Puerto Montt. Conoce la historia, el equipo y la visión.'),
    'mi-app': ('Mi App · Área Latina Estudio',
               'La web explica, la app acompaña. Reserva clases, administra tu '
               'plan y revisa tus pagos desde el celular.'),
    'contacto': ('Contacto · Área Latina Estudio',
                 'Guillermo Gallardo 310, Puerto Montt. Escríbenos y coordinamos '
                 'tu primera clase.'),
}


def _con_og(seccion, contexto):
    """Agrega el título y la bajada para compartir el enlace."""
    titulo, bajada = OG.get(seccion, (None, None))
    contexto['seccion'] = seccion
    if titulo:
        contexto['og_titulo'] = titulo
        contexto['og_descripcion'] = bajada
    return contexto


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------

def index(request):
    hoy = timezone.localdate()
    mensuales, _ = _planes_del_sitio()

    return render(request, 'web/index.html', _con_og('inicio', {
        'areas': _areas(),
        'beneficios': BENEFICIOS,
        'como_empezar': COMO_EMPEZAR,
        'estadisticas': ESTADISTICAS,
        'galeria': [g for g in GALERIA if g.get('imagen')],
        'testimonios': Testimonio.objects.filter(publicado=True)[:3],
        'preguntas': PREGUNTAS,
        'planes': mensuales,
        'proximo_evento': (
            Evento.objects.filter(publicado=True, fecha__gte=hoy)
            .order_by('fecha')
            .first()
        ),
        'clases_destacadas': _clases_publicas()[:4],
        'total_clases': _clases_publicas().count(),
    }))


def clases(request):
    """Todas las disciplinas, agrupadas por área."""
    area_pedida = request.GET.get('area', '')
    disciplina = request.GET.get('estilo', '') or request.GET.get('disciplina', '')

    qs = _clases_publicas()
    if disciplina:
        qs = qs.filter(nombre=disciplina)

    areas = _areas()
    if area_pedida:
        areas = areas.filter(slug=area_pedida)

    # Agrupa en Python: son pocas clases y evita una consulta por area.
    por_area = []
    for area in areas:
        del_area = [c for c in qs if c.categoria_id == area.id]
        if del_area:
            por_area.append({'area': area, 'clases': del_area})

    sin_area = [c for c in qs if c.categoria_id is None]

    return render(request, 'web/clases.html', _con_og('clases', {
        'por_area': por_area,
        'sin_area': sin_area,
        'todas': qs,
        'areas': _areas(),
        'disciplinas': _disciplinas_con_clases(),
        'area_activa': area_pedida,
        'disciplina_activa': disciplina,
    }))


def planes(request):
    """Horarios y planes en la misma página, como en la lámina 06."""
    encontradas, filtros, opciones = _buscar_clases(request)
    mensuales, suelta = _planes_del_sitio()

    return render(request, 'web/planes.html', _con_og('planes', {
        'clases': encontradas,
        'filtros': filtros,
        'opciones': opciones,
        'planes': mensuales,
        'plan_suelto': suelta,
        'preguntas': PREGUNTAS[:4],
    }))


def wellness(request):
    """El área de bienestar: pilates, barre, flexibilidad y reformer."""
    area = get_object_or_404(Categoria, slug='wellness')
    return render(request, 'web/wellness.html', _con_og('wellness', {
        'area': area,
        'clases': area.clases.filter(activa=True).select_related('profesora'),
        'planes': _planes_del_sitio()[0],
    }))


def en_escena(request):
    """Muestras y competencias: lo formativo que termina en escenario."""
    hoy = timezone.localdate()
    eventos = Evento.objects.filter(
        publicado=True,
        tipo__in=Evento.TIPOS_ESCENA,
    )
    companias = Categoria.objects.filter(slug='companias', activa=True).first()

    return render(request, 'web/en_escena.html', _con_og('en-escena', {
        'proximos': eventos.filter(fecha__gte=hoy).order_by('fecha'),
        'pasados': eventos.filter(fecha__lt=hoy).order_by('-fecha')[:6],
        'companias': companias,
        'clases_companias': (
            companias.clases.filter(activa=True) if companias else []
        ),
    }))


def comunidad(request):
    """Talleres, juntas y todo lo que pasa fuera de la clase regular."""
    hoy = timezone.localdate()
    eventos = Evento.objects.filter(publicado=True).exclude(
        tipo__in=Evento.TIPOS_ESCENA,
    )
    return render(request, 'web/comunidad.html', _con_og('comunidad', {
        'proximos': eventos.filter(fecha__gte=hoy).order_by('fecha'),
        'pasados': eventos.filter(fecha__lt=hoy).order_by('-fecha')[:6],
        'testimonios': Testimonio.objects.filter(publicado=True),
        'valores': VALORES,
    }))


def nosotros(request):
    kids = Categoria.objects.filter(slug='kids-teens', activa=True).first()
    return render(request, 'web/nosotros.html', _con_og('nosotros', {
        'equipo': EQUIPO,
        'beneficios': BENEFICIOS,
        'valores': VALORES,
        'estadisticas': ESTADISTICAS,
        'areas': _areas(),
        'kids': kids,
        'clases_kids': kids.clases.filter(activa=True) if kids else [],
    }))


def mi_app(request):
    return render(request, 'web/mi_app.html', _con_og('mi-app', {
        'funciones': APP_FUNCIONES,
    }))


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
    return render(request, 'web/contacto.html',
                  _con_og('contacto', {'form': form}))


def _notificar_por_email(mensaje):
    """Avisa al equipo del mensaje nuevo. Si falla, el mensaje ya está guardado."""
    from apps.gestion.correos import enviar_mensaje_contacto

    try:
        enviar_mensaje_contacto(mensaje)
    except Exception:
        pass
