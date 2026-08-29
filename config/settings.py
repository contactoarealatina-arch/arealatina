"""
Configuracion de Django para el proyecto Area Latina Estudio.
"""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Variables de entorno (.env)
# ---------------------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
)
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
]

THIRD_PARTY_APPS = [
    'django_apscheduler',
    'axes',            # freno a la fuerza bruta en el login
    'storages',        # fotos en almacenamiento de objetos (R2)
]

LOCAL_APPS = [
    'apps.usuarios',
    'apps.web',
    'apps.gestion',
    'apps.asistencia',
    'apps.profesoras',
    'apps.portal',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'csp.middleware.CSPMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

# Axes primero: intercepta el intento antes de que Django valide la clave.
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'apps.web.context_processors.academia',
                'apps.gestion.context_processors.panel',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ---------------------------------------------------------------------------
# Base de datos - PostgreSQL
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
        # En produccion la base viaja por internet: TLS obligatorio.
        # En local Postgres suele no tener certificado, por eso se relaja.
        'OPTIONS': {'sslmode': env('DB_SSLMODE', default='prefer')},
        'CONN_MAX_AGE': 60,
    }
}

# ---------------------------------------------------------------------------
# Usuario personalizado
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'usuarios.CustomUser'

LOGIN_URL = 'usuarios:login'
LOGIN_REDIRECT_URL = 'gestion:dashboard'
LOGOUT_REDIRECT_URL = 'web:index'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internacionalizacion
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos estaticos y media
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
# En base de datos y no en memoria: el freno a los intentos de login tiene
# que valer para todos los procesos del servidor, no solo para uno.
# Requiere haber corrido: manage.py createcachetable
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_arealatina',
    }
}

# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False   # el JS necesita leerla para las peticiones
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
# SECURE_BROWSER_XSS_FILTER queda fuera a proposito: la cabecera
# X-XSS-Protection esta obsoleta y los navegadores actuales la ignoran o
# la desaconsejan. Quien protege de XSS hoy es la CSP de mas abajo.
SESSION_COOKIE_AGE = 60 * 60 * 8          # 8 horas de jornada
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

if not DEBUG:
    # Con HTTPS en el hosting. Si el dominio aun no tiene certificado,
    # deja SECURE_SSL_REDIRECT en False o el sitio queda inaccesible.
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    CSRF_TRUSTED_ORIGINS = env.list(
        'CSRF_TRUSTED_ORIGINS',
        default=['https://arealatinaestudio.cl', 'https://www.arealatinaestudio.cl'],
    )

# ---------------------------------------------------------------------------
# django-axes: freno a la fuerza bruta
# ---------------------------------------------------------------------------
# Reemplaza al freno artesanal que habia antes. Se prefiere axes porque
# guarda los intentos en base de datos (auditables, sobreviven al reinicio)
# y es codigo revisado por mucha gente, cosa que importa cuando hay que
# defender el sistema ante un tercero.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCK_OUT_AT_FAILURE = True
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = 'seguridad/bloqueado.html'
# Bloquea la combinacion IP + usuario: asi un atacante no deja fuera a un
# alumno legitimo simplemente fallando su usuario desde otra parte.
AXES_LOCKOUT_PARAMETERS = [['ip_address', 'username']]
AXES_IPWARE_PROXY_COUNT = 1 if not DEBUG else None
AXES_IPWARE_META_PRECEDENCE_ORDER = ['HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR']
AXES_VERBOSE = True

# ---------------------------------------------------------------------------
# Content Security Policy
# ---------------------------------------------------------------------------
# Es la defensa real contra XSS: aunque alguien logre inyectar un <script>,
# el navegador se niega a ejecutarlo si no viene de un origen permitido.
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", 'https://cdn.jsdelivr.net')
# Cada carga genera un nonce distinto y solo los <script> que lo llevan
# se ejecutan. Asi los scripts propios en linea funcionan sin abrir la
# puerta con 'unsafe-inline': un script inyectado no puede adivinarlo.
CSP_INCLUDE_NONCE_IN = ['script-src']
# Los navegadores piden los .map de las librerias cuando estan abiertas
# las herramientas de desarrollo. Sin esto la consola se llena de errores
# que no son problemas reales.
CSP_CONNECT_SRC = ("'self'", 'https://cdn.jsdelivr.net')
CSP_STYLE_SRC = ("'self'", 'https://cdn.jsdelivr.net',
                 'https://fonts.googleapis.com', "'unsafe-inline'")
CSP_FONT_SRC = ("'self'", 'https://fonts.gstatic.com', 'https://cdn.jsdelivr.net')
CSP_IMG_SRC = ("'self'", 'data:', 'https:')
CSP_FRAME_SRC = ("'self'", 'https://www.google.com')   # el mapa de contacto
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)
CSP_OBJECT_SRC = ("'none'",)
# 'unsafe-inline' en estilos es una concesion consciente: hay estilos en
# linea en las plantillas de correo y en algunas vistas. En scripts NO se
# permite, que es donde de verdad importa.

# ---------------------------------------------------------------------------
# Cifrado de campos sensibles
# ---------------------------------------------------------------------------
# Solo se cifran campos que nunca se buscan ni se filtran. Ver comentario
# en apps/gestion/models.py sobre por que RUT, email y telefono quedan sin
# cifrar a nivel de campo.
FIELD_ENCRYPTION_KEY = env('FIELD_ENCRYPTION_KEY', default='')

# ---------------------------------------------------------------------------
# Almacenamiento de archivos
# ---------------------------------------------------------------------------
# Las fotos de alumnos van a Cloudflare R2 cuando hay credenciales. En el
# disco de Railway se borrarian en cada despliegue.
USAR_R2 = bool(env('R2_ACCESS_KEY_ID', default=''))

if USAR_R2:
    STORAGES['default'] = {
        'BACKEND': 'apps.gestion.almacenamiento.AlmacenamientoPrivado',
    }
    AWS_ACCESS_KEY_ID = env('R2_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('R2_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = env('R2_BUCKET')
    AWS_S3_ENDPOINT_URL = env('R2_ENDPOINT')
    AWS_S3_REGION_NAME = 'auto'
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_DEFAULT_ACL = None          # el bucket es privado
    AWS_QUERYSTRING_AUTH = True     # URLs firmadas, no publicas
    AWS_QUERYSTRING_EXPIRE = 3600   # cada URL vive una hora

# ---------------------------------------------------------------------------
# Registro de eventos de seguridad
# ---------------------------------------------------------------------------
CARPETA_LOGS = BASE_DIR / 'logs'
CARPETA_LOGS.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'seguridad': {
            'format': '{asctime} {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'archivo_seguridad': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': CARPETA_LOGS / 'seguridad.log',
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'seguridad',
            'encoding': 'utf-8',
        },
        'consola': {
            'class': 'logging.StreamHandler',
            'formatter': 'seguridad',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['archivo_seguridad', 'consola'],
            'level': 'WARNING',
            'propagate': False,
        },
        'axes': {
            'handlers': ['archivo_seguridad'],
            'level': 'WARNING',
            'propagate': False,
        },
        'arealatina.seguridad': {
            'handlers': ['archivo_seguridad', 'consola'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Direccion publica del sitio, para los enlaces de los correos.
SITIO_URL = env('SITIO_URL', default='http://localhost:8000')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = (
    # En desarrollo el correo sale por consola. Se usa un backend propio
    # porque el de Django escribe en cp1252 en Windows y falla con UTF-8.
    'apps.gestion.email_backends.EmailBackend' if DEBUG
    else 'django.core.mail.backends.smtp.EmailBackend'
)
# Brevo (ex Sendinblue) como relay SMTP. Todo viene del .env para no
# dejar credenciales en el repositorio.
EMAIL_HOST = env('EMAIL_HOST', default='smtp-relay.brevo.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
# Usuario del relay de Brevo (b31a8d001@smtp-brevo.com), NO el correo
# de la academia: son cosas distintas y confundirlas rebota el envío.
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
# Tiene que ser un remitente VERIFICADO en Brevo o el envío se rechaza.
DEFAULT_FROM_EMAIL = env(
    'DEFAULT_FROM_EMAIL',
    default='Area Latina Estudio <contacto.arealatina@gmail.com>',
)

# Dominio para los enlaces de los correos: en un correo una ruta relativa
# no lleva a ninguna parte.
SITIO_URL = env('SITIO_URL', default='http://localhost:8000')

# ---------------------------------------------------------------------------
# APScheduler
# ---------------------------------------------------------------------------
APSCHEDULER_DATETIME_FORMAT = 'd/m/Y H:i:s'
APSCHEDULER_RUN_NOW_TIMEOUT = 25

# ---------------------------------------------------------------------------
# Datos de la academia (disponibles en todos los templates)
# ---------------------------------------------------------------------------
ACADEMIA = {
    'nombre': 'Area Latina Estudio',
    'email': env('CONTACTO_EMAIL', default='contacto.arealatina@gmail.com'),
    'telefono': '+56 9 0000 0000',
    'telefono_link': '+56900000000',
    'direccion': 'Guillermo Gallardo 310, Puerto Montt',
    'direccion_completa': 'Guillermo Gallardo 310, 5400000 Puerto Montt, Los Lagos',
    'direccion_maps': 'Guillermo Gallardo 310, Puerto Montt, Los Lagos, Chile',
    # Redes: deja en blanco las que todavia no existen y no se muestran en el sitio.
    'instagram': 'https://www.instagram.com/arealatina.oficial/',
    'facebook': 'https://www.facebook.com/latinasouthpm/',
    'tiktok': '',
    'whatsapp': '',
    # Solo digitos con codigo de pais, para los enlaces wa.me
    'whatsapp_numero': env('WHATSAPP_NUMERO', default=''),

    # Enlace corto de resenas de Google Business Profile.
    # Se saca de business.google.com -> "Pedir resenas", y queda con la
    # forma https://g.page/r/CODIGO/review
    # Mientras este vacio, ningun boton de resena aparece en el sitio: es
    # preferible eso a mandar a la gente a un enlace roto.
    'google_resenas': env('GOOGLE_REVIEW_LINK', default=''),
    # Lo que se muestra junto a las estrellas. Se actualiza a mano cada
    # cierto tiempo: la API de Google para leer el rating requiere
    # verificacion del negocio y una clave, y no vale la pena por un dato
    # que cambia una vez al mes.
    'google_rating': env('GOOGLE_RATING', default='5,0'),
    'google_total_resenas': env.int('GOOGLE_TOTAL_RESENAS', default=0),
}
