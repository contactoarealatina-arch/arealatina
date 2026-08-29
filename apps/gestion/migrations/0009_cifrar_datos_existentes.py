"""Cifra los valores que ya estaban guardados en texto plano.

La migración anterior cambió el tipo de columna, pero el contenido siguió
tal cual: texto legible. Si no se re-escribe, al leerlo la aplicación
intentaría descifrar algo que nunca se cifró y fallaría.

El truco es leer con SQL crudo (así se saltan los campos y llega el texto
tal como está en la tabla) y volver a escribir con el ORM, que sí cifra.
"""
from django.db import migrations

CAMPOS_ALUMNO = ['contacto_emergencia', 'telefono_emergencia', 'direccion', 'observaciones']


def _parece_cifrado(valor):
    """Los valores de Fernet empiezan por 'gAAAAA'. Evita cifrar dos veces
    si la migración se corre sobre datos ya convertidos."""
    return isinstance(valor, str) and valor.startswith('gAAAAA')


def cifrar(apps, schema_editor):
    conexion = schema_editor.connection
    Alumno = apps.get_model('gestion', 'Alumno')
    NotaInterna = apps.get_model('gestion', 'NotaInterna')

    with conexion.cursor() as cursor:
        cursor.execute(
            'SELECT id, {} FROM gestion_alumno'.format(', '.join(CAMPOS_ALUMNO))
        )
        filas = cursor.fetchall()

    convertidos = 0
    for fila in filas:
        pk, valores = fila[0], fila[1:]
        cambios = {
            campo: (valor or '')
            for campo, valor in zip(CAMPOS_ALUMNO, valores)
            if not _parece_cifrado(valor)
        }
        if cambios:
            Alumno.objects.filter(pk=pk).update(**cambios)
            convertidos += 1

    with conexion.cursor() as cursor:
        cursor.execute('SELECT id, texto FROM gestion_notainterna')
        notas = cursor.fetchall()

    for pk, texto in notas:
        if not _parece_cifrado(texto):
            NotaInterna.objects.filter(pk=pk).update(texto=texto or '')

    print(f'  Alumnos cifrados: {convertidos} · Notas cifradas: {len(notas)}')


def descifrar(apps, schema_editor):
    """Vuelta atrás: deja los valores legibles otra vez.

    Se lee con el ORM (que descifra) y se escribe con SQL crudo, para que
    el texto quede plano en la tabla.
    """
    conexion = schema_editor.connection
    Alumno = apps.get_model('gestion', 'Alumno')
    NotaInterna = apps.get_model('gestion', 'NotaInterna')

    for alumno in Alumno.objects.all():
        with conexion.cursor() as cursor:
            cursor.execute(
                'UPDATE gestion_alumno SET {} WHERE id = %s'.format(
                    ', '.join(f'{c} = %s' for c in CAMPOS_ALUMNO)
                ),
                [getattr(alumno, c) or '' for c in CAMPOS_ALUMNO] + [alumno.pk],
            )

    for nota in NotaInterna.objects.all():
        with conexion.cursor() as cursor:
            cursor.execute('UPDATE gestion_notainterna SET texto = %s WHERE id = %s',
                           [nota.texto or '', nota.pk])


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0008_respaldolog_alter_alumno_contacto_emergencia_and_more'),
    ]

    operations = [
        migrations.RunPython(cifrar, descifrar),
    ]
