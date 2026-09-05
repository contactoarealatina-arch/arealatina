"""Vistas del sitio público de Área Latina Estudio.

Los textos visibles van con tildes y eñes correctas: son los que lee el
visitante. Los comentarios y nombres de variables van sin tildes.

El sitio son tres páginas: inicio, clases y contacto. Antes eran siete y
el mensaje se diluía. Ahora el estudio cuenta dos cosas, Baile Urbano y
Bienestar, y todo lo demás (quiénes somos, las fotos, los testimonios)
vive dentro del inicio.
"""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.gestion.models import Categoria, Clase, Evento, Foto, Plan, Testimonio

from .forms import ContactoForm

# ---------------------------------------------------------------------------
# Textos institucionales
# ---------------------------------------------------------------------------

BENEFICIOS = [
    {
        'icono': 'bi-person-workspace',
        'titulo': 'Formación con acompañamiento',
        'texto': 'No entregamos una coreografía y listo. Se corrige técnica y '
                 'cada persona sabe en qué está trabajando.',
    },
    {
        'icono': 'bi-calendar-week',
        'titulo': 'Horarios que se acomodan',
        'texto': 'Mañana, tarde y noche, de lunes a sábado. Si cambia tu semana, '
                 'cambias de horario según el cupo.',
    },
    {
        'icono': 'bi-people',
        'titulo': 'Comunidad que motiva',
        'texto': 'Acá nadie mira mal a quien recién empieza. Se entrena, se ríe y '
                 'se hacen amigos en la misma sala.',
    },
]

# OJO: cifras de referencia. Reemplazar por las reales antes de publicar.
ESTADISTICAS = [
    {'valor': 8, 'sufijo': '+', 'etiqueta': 'Años enseñando'},
    {'valor': 500, 'sufijo': '+', 'etiqueta': 'Alumnos'},
    {'valor': 2, 'sufijo': '', 'etiqueta': 'Pilares'},
    {'valor': 4, 'sufijo': '', 'etiqueta': 'Profesores'},
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
        'p': '¿Puedo combinar baile con bienestar?',
        'r': 'Sí, y es lo que recomendamos. El plan de dos cursos existe justamente '
             'para eso: una disciplina de baile y una de acondicionamiento.',
    },
    {
        'p': '¿Puedo tomar una clase de prueba?',
        'r': 'Sí. Escríbenos y coordinamos una clase suelta para que conozcas al grupo '
             'antes de tomar un plan.',
    },
    {
        'p': '¿Cómo se pagan las clases?',
        'r': 'En efectivo en el estudio o por transferencia. Los planes son mensuales '
             'y también existe la opción de clase suelta.',
    },
]

# ---------------------------------------------------------------------------
# Vista previa al compartir el enlace
# ---------------------------------------------------------------------------
# Título y bajada que salen en WhatsApp e Instagram cuando alguien pega la
# URL. Van juntos en una tabla para que se lean de corrido.
OG = {
    'inicio': ('Área Latina Estudio · Cultura en movimiento',
               'Baile urbano y bienestar en Puerto Montt. Salsa, bachata, '
               'reggaetón, pilates, barre y más, para todos los niveles.'),
    'clases': ('Clases y planes · Área Latina Estudio',
               'Nuestras dos áreas: Baile Urbano y Bienestar. Mira los horarios, '
               'los niveles y los planes de cada una.'),
    'contacto': ('Contacto · Área Latina Estudio',
                 'Guillermo Gallardo 310, Puerto Montt. Escríbenos y coordinamos '
                 'tu primera clase.'),
    'mi-espacio': ('Mi espacio · Área Latina Estudio',
                   'Si ya eres alumno o profesor de Área Latina, entra a tu '
                   'espacio: tus clases, tu plan y tus pagos en un solo lugar.'),
}

# Lo que hoy se puede hacer en el portal, verificado contra apps/portal y
# apps/profesoras. No se promete nada que no exista.
PORTAL_ALUMNO = [
    {'icono': 'bi-calendar3', 'texto': 'Ver tus clases y horarios'},
    {'icono': 'bi-check2-square', 'texto': 'Confirmar tu asistencia'},
    {'icono': 'bi-credit-card', 'texto': 'Revisar tu plan y cuánto te queda'},
    {'icono': 'bi-cash-coin', 'texto': 'Ver el historial de tus pagos'},
    {'icono': 'bi-arrow-repeat', 'texto': 'Pedir la renovación de tu plan'},
    {'icono': 'bi-person-gear', 'texto': 'Cambiar tus datos y tu contraseña'},
]

PORTAL_PROFESOR = [
    {'icono': 'bi-calendar-week', 'texto': 'Ver tus clases del día'},
    {'icono': 'bi-clipboard-check', 'texto': 'Pasar lista desde el celular'},
    {'icono': 'bi-people', 'texto': 'Revisar quién está inscrito'},
    {'icono': 'bi-clock-history', 'texto': 'Consultar el historial de asistencia'},
    {'icono': 'bi-file-earmark-spreadsheet', 'texto': 'Exportar el historial a Excel'},
]


# ---------------------------------------------------------------------------
# Ayudantes
# ---------------------------------------------------------------------------

def _con_og(seccion, contexto):
    """Agrega el título y la bajada para compartir el enlace."""
    titulo, bajada = OG.get(seccion, (None, None))
    contexto['seccion'] = seccion
    if titulo:
        contexto['og_titulo'] = titulo
        contexto['og_descripcion'] = bajada
    return contexto


def _pilares():
    """Los dos pilares con sus clases y sus planes ya resueltos.

    Se arma en Python y no en la plantilla porque la página de clases los
    recorre dos veces (la tarjeta grande y el detalle desplegado) y
    repetir la consulta por cada pasada no tiene sentido.
    """
    planes = list(Plan.objects.filter(activo=True, duracion_dias__gte=28))
    suelta = Plan.objects.filter(activo=True, duracion_dias__lt=28).first()

    resultado = []
    for pilar in Categoria.objects.filter(activa=True):
        clases = list(
            pilar.clases.filter(activa=True)
            .select_related('profesora')
            .order_by('hora_inicio', 'nombre')
        )
        if not clases:
            continue
        resultado.append({
            'pilar': pilar,
            'clases': clases,
            # Los planes valen para cualquier disciplina, así que los dos
            # pilares muestran los mismos. No hay precios por pilar.
            'planes': planes,
            'suelta': suelta,
            'disciplinas': sorted({c.nombre for c in clases}),
        })
    return resultado


# ---------------------------------------------------------------------------
# Páginas
# ---------------------------------------------------------------------------

def index(request):
    """Inicio: hero, los dos pilares, quiénes somos, fotos y testimonios.

    Absorbió lo que antes eran /nosotros/ y /comunidad/. La idea es que
    quien entra entienda todo bajando una sola vez, sin navegar.
    """
    return render(request, 'web/index.html', _con_og('inicio', {
        'pilares': _pilares(),
        'beneficios': BENEFICIOS,
        'estadisticas': ESTADISTICAS,
        'fotos': Foto.objects.filter(publicada=True),
        # Solo lo que todavia no pasa. Una fecha vencida en portada es
        # peor que no tener agenda, y nadie se acuerda de borrarla.
        'eventos': Evento.objects.filter(
            publicado=True,
            fecha__gte=timezone.localdate(),
        )[:3],
        'testimonios': Testimonio.objects.filter(publicado=True)[:3],
        'preguntas': PREGUNTAS,
    }))


def clases(request):
    """Los dos pilares. Cada uno despliega sus clases y sus planes."""
    return render(request, 'web/clases.html', _con_og('clases', {
        'pilares': _pilares(),
        'sin_pilar': (
            Clase.objects.filter(activa=True, categoria__isnull=True)
            .select_related('profesora')
            .order_by('hora_inicio', 'nombre')
        ),
    }))


def mi_espacio(request):
    """Qué hay detrás del login, antes de entrar.

    No es una página de "próximamente": todo lo que se lista acá ya
    funciona. La app móvil se menciona en una línea y sin prometer
    funciones, porque todavía no existe.
    """
    return render(request, 'web/mi_espacio.html', _con_og('mi-espacio', {
        'alumno': PORTAL_ALUMNO,
        'profesor': PORTAL_PROFESOR,
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
    return render(request, 'web/contacto.html', _con_og('contacto', {'form': form}))


def _notificar_por_email(mensaje):
    """Avisa al equipo del mensaje nuevo. Si falla, el mensaje ya está guardado."""
    from apps.gestion.correos import enviar_mensaje_contacto

    try:
        enviar_mensaje_contacto(mensaje)
    except Exception:
        pass
