"""Almacenamiento de archivos subidos.

Las fotos de alumnos son datos personales: no pueden quedar en una URL
pública que cualquiera pueda adivinar o compartir. Este backend guarda en
Cloudflare R2 con el bucket privado y sirve cada foto con una URL firmada
que caduca en una hora.

Si no hay credenciales de R2 configuradas, Django usa el disco local
(ver STORAGES en settings.py). Eso sirve para desarrollo, pero en Railway
el disco se recrea en cada despliegue y las fotos se perderían.
"""
from storages.backends.s3boto3 import S3Boto3Storage


class AlmacenamientoPrivado(S3Boto3Storage):
    """Bucket privado con URLs firmadas de duración limitada."""

    default_acl = None          # R2 no usa ACL; el bucket manda
    file_overwrite = False      # dos fotos con el mismo nombre no se pisan
    querystring_auth = True     # cada URL va firmada
    querystring_expire = 3600   # y vence en una hora
    location = 'media'
