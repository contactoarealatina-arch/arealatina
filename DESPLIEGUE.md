# Subir el sistema a Railway

Guia para dejar el sistema andando en internet, visible solo para el
equipo del estudio mientras se prueba.

---

## 1. Lo que hace falta tener a mano

| Cosa | Para que | Quien la consigue |
|---|---|---|
| Cuenta en railway.com | Donde vive el sistema | Diego |
| Dominio en nic.cl | La direccion final | El estudio (lo paga) |
| Cuenta Cloudflare + bucket R2 | Guardar fotos y boletas | Diego |
| Clave SMTP de Brevo | Que salgan los correos | Ya existe |
| Clave nueva de administrador | Reemplazar la de prueba | El estudio la elige |

---

## 2. Pasos en Railway

1. **New Project → Deploy from GitHub repo** y elegir este repositorio.
2. Dentro del proyecto: **New → Database → Add PostgreSQL**.
3. En el servicio de la aplicacion, pestaña **Variables**, pegar las de
   la seccion 3.
4. Pestaña **Settings → Networking → Generate Domain**. Queda una
   direccion tipo `arealatina-production.up.railway.app` para probar
   antes de que llegue el dominio propio.
5. Esperar el primer despliegue. En **Deploy Logs** tienen que salir
   las migraciones y despues `Arriba`.

> Las variables van **antes** del primer despliegue. Si el proyecto
> arranca sin `SECRET_KEY`, la construccion falla.

---

## 3. Variables

`DATABASE_URL` se conecta con **Variable reference** al servicio
Postgres (el boton que dice `Add a Reference`), no se copia a mano: si
Railway rota la clave de la base, la referencia se actualiza sola.

```
SECRET_KEY=              (generar una nueva, ver abajo)
DEBUG=False
SITIO_PRIVADO=True

DATABASE_URL=${{Postgres.DATABASE_URL}}
DB_SSLMODE=require

ALLOWED_HOSTS=arealatinaestudio.cl,www.arealatinaestudio.cl
CSRF_TRUSTED_ORIGINS=https://arealatinaestudio.cl,https://www.arealatinaestudio.cl

EMAIL_BACKEND=smtp
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_HOST_USER=b31a8d001@smtp-brevo.com
EMAIL_HOST_PASSWORD=       (la clave SMTP de Brevo)
DEFAULT_FROM_EMAIL=Area Latina Estudio <contacto@arealatinaestudio.cl>
CONTACTO_EMAIL=contacto.arealatina@gmail.com

SITIO_URL=https://arealatinaestudio.cl
DOMINIO_PROFESORAS=arealatinaestudio.cl

FIELD_ENCRYPTION_KEY=      (ver abajo; si se pierde, los datos cifrados no vuelven)

R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=arealatina
R2_ENDPOINT=https://IDCUENTA.r2.cloudflarestorage.com

WHATSAPP_NUMERO=
GOOGLE_REVIEW_LINK=

GA_MEASUREMENT_ID=G-LXN4MY2SB5
ADMINS=Equipo:contacto.arealatina@gmail.com
SERVER_EMAIL=sistema@arealatinaestudio.cl
```

Las dos claves se generan asi, y se guardan en un lugar seguro:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

El dominio que genera Railway se agrega solo a `ALLOWED_HOSTS`: el
sistema lee la variable `RAILWAY_PUBLIC_DOMAIN` que pone la plataforma.

---

## 4. Despues del primer despliegue

En Railway, servicio de la aplicacion, pestaña de la terminal:

```bash
python manage.py createsuperuser
```

Ese es el unico usuario que va a existir en el servidor: la base de
Railway parte vacia, los alumnos de prueba del computador de Diego no
viajan.

---

## 5. El dominio

El dominio es **arealatinaestudio.cl**, inscrito en nic.cl a nombre de
Area Latina SpA, con vencimiento el 11/08/2027. El sitio y los correos
con que entran las profesoras usan ese mismo dominio.

Para apuntarlo a Railway:

1. En Railway: **Settings → Networking → Custom Domain** y escribir
   `arealatinaestudio.cl`. Railway entrega un destino tipo
   `algo.up.railway.app`.
2. En nic.cl: **Mis dominios → arealatinaestudio.cl → Cambiar DNS**.
3. Crear el registro que Railway pide. El certificado HTTPS lo emite
   Railway solo, en unos minutos.

Los dominios .cl no aceptan un CNAME en la raiz. Si Railway pide un
CNAME para `arealatinaestudio.cl` pelado, la salida es delegar el DNS a
Cloudflare (que si lo resuelve, con su "CNAME flattening"): en nic.cl se
cambian los servidores de nombres por los dos que entrega Cloudflare, y
el registro se crea alla. Con `www.arealatinaestudio.cl` el CNAME
funciona directo en nic.cl, sin mover nada.

---

## 5b. Cloudflare R2 (las fotos y las boletas)

El disco de Railway se borra entero en cada despliegue. Sin R2, la foto
de un alumno y la boleta de un pago desaparecen la proxima vez que se
sube un cambio. Esto va **antes** de que alguien cargue el primer
archivo de verdad.

1. En Cloudflare, menu izquierdo: **R2 Object Storage**. La primera vez
   pide activarlo (pide una tarjeta, pero el plan gratis cubre 10 GB y
   el estudio va a usar unos pocos cientos de MB).
2. **Create bucket**, nombre `arealatina`, ubicacion automatica.
   Dejarlo **privado**: las fotos de alumnos no pueden quedar abiertas
   en internet, y el sistema arma enlaces firmados que vencen en una
   hora.
3. En R2, **Manage API Tokens → Create API Token**:
   - Permiso: **Object Read & Write**
   - Alcance: solo el bucket `arealatina`
   - Guardar el **Access Key ID** y el **Secret Access Key**: el secreto
     se muestra una sola vez.
4. Esas dos claves van directo a las variables de Railway
   (`R2_ACCESS_KEY_ID` y `R2_SECRET_ACCESS_KEY`). No se guardan en el
   repositorio ni se mandan por chat.
5. `R2_ENDPOINT` es `https://IDCUENTA.r2.cloudflarestorage.com`, donde
   IDCUENTA es el codigo largo que sale en la direccion del panel de
   Cloudflare.

Con `R2_ACCESS_KEY_ID` vacio el sistema sigue usando el disco local, asi
que en el computador de desarrollo no hay que configurar nada.


## 6. Encender y apagar

No hace falta bajar el servidor para que la gente no lo vea.

| Quiero | Hago |
|---|---|
| Que nadie lo vea, pero el equipo entre a probar | `SITIO_PRIVADO=True` |
| Abrirlo al publico | `SITIO_PRIVADO=False` |

Con `SITIO_PRIVADO=True`, quien llegue de afuera ve una pantalla de
"estamos preparando el sitio" con un boton para entrar, y el
`robots.txt` le dice a Google que no indexe nada. Quien tiene cuenta y
sesion iniciada ve el sitio completo, igual que siempre.

Cambiar la variable reinicia el servicio: son unos 40 segundos.

Si de verdad quieren bajarlo del todo: **Settings → Remove Deployment**.
La base de datos no se toca, los datos quedan.

---

## 7. Antes de abrirlo al publico

- [ ] Cambiar la clave del administrador (la de prueba es adivinable)
- [ ] Configurar R2 **antes** de que alguien suba la primera foto o
      boleta de verdad: sin R2, cada despliegue borra los archivos
- [ ] Borrar los datos de demostracion (`manage.py limpiar_datos`)
- [ ] Terminos y condiciones con texto legal real (hoy esta inactivo)
- [ ] Fotos, textos e historia que tiene que mandar el estudio
- [ ] Verificar el dominio en Brevo, o los correos se van a spam
- [ ] Configurar la meta mensual de ingresos (sin eso, esa alerta no avisa)
- [ ] Monitoreo externo con UptimeRobot — ver [MONITOREO.md](MONITOREO.md)

### Tareas automaticas

Las alertas y recordatorios necesitan un proceso aparte. En Railway:
**New → Empty Service**, mismo repositorio, y como comando de arranque:

```
python manage.py correr_scheduler
```

Sin eso el sistema funciona igual, pero los avisos automaticos no salen.
