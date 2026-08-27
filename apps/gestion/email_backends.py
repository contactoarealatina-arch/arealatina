"""Backend de correo para desarrollo que no se ahoga con UTF-8.

El backend de consola de Django escribe en `sys.stdout`, que en la consola
de Windows suele venir en cp1252. Cualquier carácter fuera de ese juego
(por ejemplo la estrella ★ del encabezado del correo) hace fallar el envío
con UnicodeEncodeError, aunque el correo en sí esté perfecto.

Aquí se reconfigura el propio `sys.stdout` a UTF-8 en vez de envolverlo en
un TextIOWrapper nuevo: un wrapper cierra el buffer original al recolectarse
y deja la consola inutilizable para el resto del comando.

En producción se usa el backend SMTP normal, que ya trabaja en UTF-8.
"""
import sys

from django.core.mail.backends.console import EmailBackend as BackendConsola


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
