"""
Configuracion de Django para el proyecto Area Latina Estudio.
"""
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
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
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
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
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
}
