"""Backends de correo de Area Latina.

Produccion usa la API HTTPS de Brevo porque Railway bloquea las conexiones
SMTP en los planes Free, Trial y Hobby. Desarrollo conserva el backend de
consola tolerante a UTF-8 que ya existia.

El backend de consola de Django escribe en `sys.stdout`, que en la consola
de Windows suele venir en cp1252. Cualquier carácter fuera de ese juego
(por ejemplo la estrella ★ del encabezado del correo) hace fallar el envío
con UnicodeEncodeError, aunque el correo en sí esté perfecto.

Aquí se reconfigura el propio `sys.stdout` a UTF-8 en vez de envolverlo en
un TextIOWrapper nuevo: un wrapper cierra el buffer original al recolectarse
y deja la consola inutilizable para el resto del comando.

El backend de API tambien trabaja en UTF-8 y conserva la interfaz de correo
de Django, asi que el resto del proyecto no depende del transporte elegido.
"""
import base64
import sys
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.backends.console import EmailBackend as BackendConsola


URL_BREVO = 'https://api.brevo.com/v3/smtp/email'


class BrevoAPIBackend(BaseEmailBackend):
    """Envia los mensajes de Django mediante la API transaccional de Brevo."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        api_key = getattr(settings, 'BREVO_API_KEY', '')
        if not api_key:
            if self.fail_silently:
                return 0
            raise ValueError('Falta BREVO_API_KEY: Brevo no puede enviar correos.')

        enviados = 0
        for mensaje in email_messages:
            try:
                self._enviar(api_key, mensaje)
            except Exception:
                if not self.fail_silently:
                    raise
            else:
                enviados += 1
        return enviados

    def _enviar(self, api_key, mensaje):
        respuesta = requests.post(
            URL_BREVO,
            headers={
                'accept': 'application/json',
                'api-key': api_key,
                'content-type': 'application/json',
            },
            json=self._payload(mensaje),
            timeout=30,
        )
        if respuesta.status_code < 200 or respuesta.status_code >= 300:
            detalle = respuesta.text[:1000]
            raise RuntimeError(
                f'Brevo rechazo el correo (HTTP {respuesta.status_code}): {detalle}'
            )

    def _payload(self, mensaje):
        nombre_remitente, correo_remitente = parseaddr(
            mensaje.from_email or settings.DEFAULT_FROM_EMAIL
        )
        if not correo_remitente:
            raise ValueError('El remitente del correo no es valido.')

        payload = {
            'sender': self._direccion(correo_remitente, nombre_remitente),
            'to': [self._direccion(direccion) for direccion in mensaje.to],
            'subject': mensaje.subject,
            'textContent': mensaje.body or '',
        }

        if mensaje.cc:
            payload['cc'] = [self._direccion(direccion) for direccion in mensaje.cc]
        if mensaje.bcc:
            payload['bcc'] = [self._direccion(direccion) for direccion in mensaje.bcc]
        if mensaje.reply_to:
            nombre, correo = parseaddr(mensaje.reply_to[0])
            payload['replyTo'] = self._direccion(correo, nombre)

        for alternativa in getattr(mensaje, 'alternatives', []):
            if hasattr(alternativa, 'content'):
                contenido = alternativa.content
                mimetype = alternativa.mimetype
            else:
                contenido, mimetype = alternativa
            if mimetype == 'text/html':
                payload['htmlContent'] = contenido
                break

        adjuntos = []
        for adjunto in getattr(mensaje, 'attachments', []):
            if hasattr(adjunto, 'filename'):
                nombre = adjunto.filename
                contenido = adjunto.content
            elif isinstance(adjunto, (tuple, list)):
                nombre, contenido = adjunto[:2]
            else:
                # Los MIMEBase especiales no se usan hoy en el proyecto.
                continue
            if not nombre or contenido is None:
                continue
            if isinstance(contenido, str):
                contenido = contenido.encode('utf-8')
            adjuntos.append({
                'name': nombre,
                'content': base64.b64encode(contenido).decode('ascii'),
            })
        if adjuntos:
            payload['attachment'] = adjuntos

        return payload

    @staticmethod
    def _direccion(direccion, nombre=''):
        if not nombre:
            nombre, direccion_parseada = parseaddr(direccion)
            direccion = direccion_parseada or direccion
        resultado = {'email': direccion}
        if nombre:
            resultado['name'] = nombre
        return resultado


class EmailBackend(BackendConsola):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        codificacion = (getattr(self.stream, 'encoding', '') or '').lower()
        if codificacion.replace('-', '') == 'utf8':
            return

        # reconfigure() existe desde Python 3.7 y no reemplaza el stream,
        # solo cambia cómo codifica.
        reconfigurar = getattr(self.stream, 'reconfigure', None)
        if reconfigurar is not None:
            try:
                reconfigurar(encoding='utf-8', errors='replace')
                return
            except (ValueError, OSError):
                pass

        # Último recurso: que los caracteres raros no rompan el envío.
        self.stream = _SalidaTolerante(self.stream)


class _SalidaTolerante:
    """Reemplaza lo que la consola no sabe representar, en vez de fallar."""

    def __init__(self, destino):
        self._destino = destino

    def write(self, texto):
        codificacion = getattr(self._destino, 'encoding', None) or 'ascii'
        seguro = texto.encode(codificacion, errors='replace').decode(codificacion)
        return self._destino.write(seguro)

    def flush(self):
        return self._destino.flush()

    def __getattr__(self, nombre):
        return getattr(self._destino, nombre)
