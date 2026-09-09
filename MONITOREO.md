# Analítica y alertas

Qué mide el sistema, qué avisa y qué falta configurar a mano.

---

## 1. Google Analytics

Código de medición: `G-LXN4MY2SB5` (variable `GA_MEASUREMENT_ID`).

**Solo mide el sitio público.** El panel de gestión, el portal de alumnos
y el de profesoras quedan fuera: ahí no hay marketing que analizar y sí
datos de personas identificables, que es justo lo que no corresponde
mandarle a un tercero.

### El consentimiento

La medición **no arranca sola**. El sitio le prometía al visitante, en el
aviso de cookies y en la política de privacidad, que no usaba rastreo.
Instalar Analytics sin más habría convertido esas dos frases en mentira,
y la Ley 21.719 pide consentimiento informado, no un acuse de recibo.

Entonces el aviso ahora tiene dos botones:

| El visitante elige | Qué pasa |
|---|---|
| **Aceptar** | Se carga Analytics |
| **Solo lo necesario** | No se carga nada de Google |

Quien ya había apretado "Entendido" en el aviso viejo cuenta como "solo
lo necesario": nunca aceptó medición y no corresponde dársela por hecha.

La política de privacidad quedó actualizada con esto.

### Eventos que se miden

Además de las visitas automáticas:

| Evento | Cuándo se dispara |
|---|---|
| `formulario_contacto_enviado` | Al volver de un envío exitoso, no al apretar Enviar |
| `click_boton_inscripcion` | "Únete ahora" (lleva `lugar`: barra, cierre, mi espacio) |
| `click_resena_google` | Botón de reseña del pie |
| `ver_detalle_clase` | Abrir Baile Urbano o Bienestar (lleva `categoria`) |

Para agregar un evento nuevo no hay que tocar JavaScript: basta el
atributo en el HTML.

```html
<a href="..." data-evento="mi_evento" data-evento-datos='{"lugar": "x"}'>
```

### En desarrollo no mide

`GA_EN_DESARROLLO=False` por defecto: en la máquina de Diego no se envía
nada, para que las pruebas no ensucien los números reales.

---

## 2. Alertas de negocio

Panel: **/gestion/alertas-negocio/** · en el menú, "Negocio".

Van aparte del panel de Alertas de siempre a propósito. Aquel es una
lista de tareas que alguien cierra una por una ("a Camila se le vence el
plan"); este es una lectura de cómo va el estudio ("las inscripciones
bajaron 45%"). Juntas, lo segundo se perdería entre veinte vencimientos.

| Regla | Cuándo avisa | Cada cuánto |
|---|---|---|
| Meta mensual alcanzada | Los ingresos del mes pasan la meta | Una vez por mes |
| Caída de inscripciones | Baja más de 40% vs. las 4 semanas previas | Una por semana |
| Ausente prolongado | Plan al día y 14+ días sin venir | Una por alumno al mes |
| Pago atrasado crítico | Plan vencido hace 15+ días, sin renovar | Una por alumno al mes |
| Alumno nuevo | Al inscribirlo | En el momento |

**La meta mensual hay que configurarla**: en `ConfiguracionAlertas`,
campo `meta_mensual_clp`. Mientras esté en 0 esa alerta no se genera —
es preferible que no avise a que avise contra un número inventado.

### Resumen semanal

Los lunes a las 09:00 llega un correo con los ingresos de la semana
contra la anterior, los alumnos nuevos, las alertas generadas y las
clases con más y menos asistencia. Se apaga con
`ConfiguracionAlertas.enviar_resumen_semanal`.

---

## 3. Estado del sistema

Panel: **/gestion/sistema/alertas/** · en el menú, "Sistema". **Solo
superadmin.**

Una sola línea de tiempo con lo técnico: seguridad, errores del servidor
y movimientos raros de tráfico. Están juntos porque para quien revisa un
incidente son lo mismo —cosas que ocurrieron, en orden— y separarlos
obligaría a cruzar horas entre dos pantallas.

### Errores 500

Con `DEBUG=False`, Django manda un correo con el detalle completo cada
vez que una vista revienta. Va a las direcciones de `ADMINS`, desde
`SERVER_EMAIL`, por el mismo Brevo que ya está configurado.

### Tráfico inusual

El sistema lleva su propio conteo de páginas vistas del sitio público
(sin contar al equipo, que mirando su propio sitio no es tráfico). Todas
las noches a las 23:45 lo compara con el promedio de la semana:

- **Pico sobre 300%** — o se viralizó algo, o alguien está raspando el sitio
- **Caída bajo 50%** — puede ser señal de que el sitio tiene un problema

No avisa si hay menos de 3 días de historia o menos de 10 visitas de
promedio: con números tan chicos, pasar de 2 a 8 visitas es un 400% y no
significa nada.

Ese conteo **no reemplaza a Analytics**, que sigue siendo la fuente buena
para analizar. Existe para que el sistema pueda avisar solo, sin depender
de la API de Google, que es una pieza más que se puede caer.

---

## 4. Dashboard

En **/gestion/** hay una sección "Estado general" con tres columnas:
Negocio (últimas alertas), Tráfico (acceso directo a Analytics y avisos
de tráfico raro) y Seguridad (últimos movimientos de acceso, solo para
el superadmin).

---

## 5. Pendiente: monitoreo externo (para Diego)

Esto **no es código**, es configuración en un sitio web. El sistema no
puede avisar que se cayó si el que se cayó es el sistema: hace falta algo
afuera que lo vigile.

1. Crear cuenta gratis en <https://uptimerobot.com> (50 monitores gratis)
2. **Add New Monitor** → tipo **HTTPS**
3. URL: `https://arealatinaestudio.cl`
4. Intervalo: **5 minutos**
5. En **Alert Contacts**, agregar el correo del administrador

Detalle importante: mientras `SITIO_PRIVADO=True`, el sitio responde
**503** a quien no tenga sesión, y UptimeRobot lo va a leer como caído.
Hasta que abran al público, apunta el monitor a
`https://arealatinaestudio.cl/cuentas/login/`, que responde 200 en los
dos modos.

---

## 6. Los trabajos automáticos

```
00:01  planes_vencidos
08:00  recordatorio_profesoras
09:00  alertas_manana
09:05  alertas_negocio          <- nuevo
10:00  pedir_resenas
18:00  recordatorio_clases
23:45  revisar_trafico          <- nuevo
lunes  resumen_semanal (09:00)  <- nuevo
día 1  informe_mensual
```

Cualquiera se puede correr a mano:

```bash
python manage.py correr_trabajo alertas_negocio
```

En Railway necesitan un servicio aparte con `python manage.py
correr_scheduler`. Sin eso el sistema funciona igual, pero estas
revisiones no salen solas: hay que apretar "Revisar ahora" en cada panel.
