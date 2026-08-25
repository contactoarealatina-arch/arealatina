# Área Latina Estudio

Sistema de gestión + sitio web público para la academia de baile **Área Latina Estudio**
(Puerto Montt, Chile).

- **Backend:** Django 5.1 + Python 3.12
- **Base de datos:** PostgreSQL 18
- **Frontend:** Bootstrap 5 + CSS propio (paleta oficial del logo)

## Puesta en marcha

```bash
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Sitio en <http://localhost:8000> · Administración en <http://localhost:8000/admin/>

## Estructura

```
config/          settings, urls, wsgi, asgi
apps/
  web/           sitio público (home, clases, nosotros, contacto)
  gestion/       alumnos, clases, planes, suscripciones, pagos
  asistencia/    registro de asistencia (módulo profesoras)
  usuarios/      CustomUser con roles ADMIN / PROFESOR / ALUMNO
static/          css, js, img (logos)
templates/       base.html + templates de web y gestión
media/           fotos de alumnos subidas desde el admin
```

## Comandos útiles

```bash
python manage.py datos_demo
```

Carga profesoras, planes y clases de ejemplo (idempotente: se puede correr varias veces).

## Configuración

Las credenciales viven en `.env` (no versionado). `.env.example` muestra las
variables requeridas: `SECRET_KEY`, `DB_*`, `EMAIL_HOST_USER`.

El formulario de contacto guarda el mensaje en base de datos y además intenta
enviarlo por correo a `arealatina310@gmail.com`. Con `DEBUG=True` los correos se
imprimen en consola; para envío real hay que definir `EMAIL_HOST_PASSWORD` con una
contraseña de aplicación de Gmail y poner `DEBUG=False`.

## Paleta

| Variable | Color | Uso |
|---|---|---|
| `--color-bg` | `#0D0D0D` | Fondo base |
| `--color-bg-section` | `#1A1A1A` | Separación de secciones |
| `--color-bg-card` | `#222222` | Fondo de cards |
| `--color-text` | `#FFFFFF` | Texto principal |
| `--color-text-muted` | `#B0B0B0` | Texto secundario |
| `--color-accent` | `#FF5722` | Acento principal |
| `--color-accent-dark` | `#E64A19` | Hover de botones |
| `--color-accent-lite` | `#FF8A65` | Detalles |
| `--color-border` | `#2A2A2A` | Bordes de cards |
