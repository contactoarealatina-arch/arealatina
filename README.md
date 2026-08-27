# Área Latina Estudio

Sitio web público + sistema de gestión para la academia de baile
**Área Latina Estudio** (Guillermo Gallardo 310, Puerto Montt).

- **Backend:** Django 5.1 + Python 3.12
- **Base de datos:** PostgreSQL 18
- **Frontend:** Bootstrap 5 + CSS propio · Chart.js en el panel

## Puesta en marcha

```bash
venv\Scripts\python.exe manage.py migrate
venv\Scripts\python.exe manage.py runserver
```

| URL | Qué es |
|---|---|
| <http://localhost:8000> | Sitio público |
| <http://localhost:8000/gestion/> | Panel de gestión |
| <http://localhost:8000/admin/> | Administrador de Django |

## Estructura

```
config/          settings, urls, wsgi, asgi
apps/
  web/           sitio público (home, clases, nosotros, contacto)
  gestion/       el sistema completo
    views/       un módulo por área (dashboard, alumnos, pagos, ...)
    servicios.py fechas, métricas y generación de alertas
    excel.py     exportaciones con openpyxl
    permisos.py  decoradores de acceso por rol
    auditoria.py registro de acciones
    correos.py   resumen diario por email
  asistencia/    RegistroAsistencia
  usuarios/      CustomUser con roles
static/          css, js, img
templates/       base pública + templates de gestión
media/           fotos de alumnos
```

## Roles

| Rol | Acceso |
|---|---|
| `SUPERADMIN` | Todo, incluida la auditoría |
| `ADMIN` | Gestión completa, sin auditoría |
| `PROFESOR` | Solo pasar lista de **sus propias** clases |
| `ALUMNO` | Reservado para el portal de alumnos (etapa posterior) |

## Módulos del panel

Dashboard con métricas y gráficos · Alumnos (CRUD, alta en 4 pasos, ficha
con historial) · Clases · Planes y suscripciones · Pagos y resumen
financiero · Alertas automáticas · Reportes en Excel · Asistencia ·
Profesoras · Auditoría.

## Comandos

```bash
venv\Scripts\python.exe manage.py datos_demo --con-alumnos
```

Carga profesoras, planes, clases y **12 alumnos de prueba**. Los alumnos de
prueba tienen RUT del rango `90.xxx.xxx`, que no existe en la realidad.
Para borrarlos sin tocar nada más:

```bash
venv\Scripts\python.exe manage.py datos_demo --borrar-demo
```

```bash
venv\Scripts\python.exe manage.py enviar_alertas
```

Genera las alertas del día y manda el resumen por correo. Es lo que debe
quedar en el cron del hosting, una vez al día. Alternativa: dejar corriendo
`manage.py correr_scheduler` como servicio.

## Configuración

Las credenciales viven en `.env` (no versionado); `.env.example` muestra las
variables. Para el envío real de correos hay que completar
`EMAIL_HOST_PASSWORD` con la clave SMTP de Brevo y poner `DEBUG=False`.
Con `DEBUG=True` los correos se imprimen en la consola.

## Paleta

| Variable | Color | Uso |
|---|---|---|
| `--al-black` | `#0D0D0D` | Fondo base, sidebar |
| `--al-dark` | `#1A1A1A` | Fondo del contenido |
| `--al-card` | `#222222` | Tarjetas y tablas |
| `--al-orange` | `#FF5722` | Acento principal |
| `--al-orange-dark` | `#E64A19` | Hover de botones |
| `--al-muted` | `#B0B0B0` | Texto secundario |
| `--al-border` | `#2A2A2A` | Bordes |
