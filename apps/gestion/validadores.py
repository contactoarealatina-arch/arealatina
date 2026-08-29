"""Validación de los archivos que sube el equipo.

Una foto de perfil es la única entrada por la que un usuario puede
depositar un archivo en el servidor. Comprobar solo la extensión no basta:
cualquiera renombra un .exe a .jpg. Acá se abre el archivo con Pillow y se
verifica que de verdad sea una imagen.
"""
import os

from django.core.exceptions import ValidationError
from PIL import Image

EXTENSIONES = {'.jpg', '.jpeg', '.png', '.webp'}
FORMATOS = {'JPEG', 'PNG', 'WEBP'}
TAMANO_MAXIMO = 5 * 1024 * 1024      # 5 MB
LADO_MAXIMO = 800                    # píxeles, para redimensionar


def validar_foto(archivo):
    """Extensión, peso y contenido real. Los tres, en ese orden."""
    extension = os.path.splitext(archivo.name)[1].lower()
    if extension not in EXTENSIONES:
        raise ValidationError(
            'Formato no permitido. Usa una imagen JPG, PNG o WebP.'
        )

    if archivo.size > TAMANO_MAXIMO:
        mb = archivo.size / (1024 * 1024)
        raise ValidationError(
            f'La imagen pesa {mb:.1f} MB y el máximo son 5 MB. '
            'Reduce su tamaño e inténtalo de nuevo.'
        )

    # Lo que importa: que el contenido sea una imagen, no que lo parezca
    # por el nombre. verify() lee la cabecera real del archivo.
    posicion = archivo.tell()
    try:
        archivo.seek(0)
        imagen = Image.open(archivo)
        imagen.verify()
        if imagen.format not in FORMATOS:
            raise ValidationError(
                f'El archivo dice ser {imagen.format} y no es un formato permitido.'
            )
    except ValidationError:
        raise
    except Exception:
        raise ValidationError(
            'El archivo no es una imagen válida o está dañado.'
        )
    finally:
        archivo.seek(posicion)

    return archivo


def redimensionar_foto(archivo, lado=LADO_MAXIMO):
    """Deja la imagen en un tamaño razonable antes de guardarla.

    Una foto de celular moderna pesa varios MB y en la ficha se muestra a
    120 píxeles. Guardarla entera es pagar almacenamiento y ancho de banda
    por nada.
    """
    from io import BytesIO

    from django.core.files.uploadedfile import InMemoryUploadedFile

    try:
        archivo.seek(0)
        imagen = Image.open(archivo)

        # Las fotos de celular traen la orientación en los metadatos EXIF;
        # sin esto salen giradas. De paso, convertir descarta el EXIF, que
        # puede incluir la ubicación donde se tomó la foto.
        from PIL import ImageOps
        imagen = ImageOps.exif_transpose(imagen)

        if imagen.mode not in ('RGB', 'L'):
            imagen = imagen.convert('RGB')

        if max(imagen.size) > lado:
            imagen.thumbnail((lado, lado), Image.LANCZOS)

        buffer = BytesIO()
        imagen.save(buffer, format='JPEG', quality=85, optimize=True)
        buffer.seek(0)

        nombre = os.path.splitext(os.path.basename(archivo.name))[0] + '.jpg'
        return InMemoryUploadedFile(
            buffer, 'ImageField', nombre, 'image/jpeg', buffer.getbuffer().nbytes, None
        )
    except Exception:
        # Si algo sale mal, se guarda el original: ya pasó la validación.
        archivo.seek(0)
        return archivo
