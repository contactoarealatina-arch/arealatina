"""Retención de datos personales.

Uso:
    python manage.py limpiar_datos --simular   (muestra qué haría, sin tocar)
    python manage.py limpiar_datos

La Ley 21.719 pide no guardar datos personales más allá de lo necesario.
Este comando aplica los plazos que declara la política de privacidad:

  · Alumnos inactivos por más de 3 años  -> se anonimizan
  · Correos enviados de más de 1 año     -> se borran
  · Auditoría de más de 2 años           -> se borra
  · Intentos de login de más de 90 días  -> se borran

Anonimizar no es borrar la fila: se conserva el registro contable (pagos,
asistencia) pero deja de estar asociado a una persona identificable.
Borrar la fila entera se llevaría por delante la contabilidad.

Va pensado para correr el día 1 de cada mes.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

ANIOS_INACTIVO = 3
DIAS_CORREOS = 365
DIAS_AUDITORIA = 730
DIAS_INTENTOS = 90


class Command(BaseCommand):
    help = 'Aplica los plazos de retención de datos personales.'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true',
                            help='Muestra qué se haría, sin modificar nada.')

    def handle(self, *args, **opciones):
        simular = opciones['simular']
        if simular:
            self.stdout.write(self.style.WARNING('MODO SIMULACIÓN: no se modifica nada.\n'))

        hoy = timezone.localdate()
        ahora = timezone.now()

        total = 0
        total += self._anonimizar(hoy, simular)
        total += self._borrar_correos(ahora, simular)
        total += self._borrar_auditoria(ahora, simular)
        total += self._borrar_intentos(ahora, simular)

        self.stdout.write('')
        if simular:
            self.stdout.write(self.style.WARNING(
                f'Se habrían tocado {total} registros. Corre sin --simular para aplicarlo.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Listo. {total} registros procesados.'))

    # ------------------------------------------------------------------
    def _anonimizar(self, hoy, simular):
        """Deja al alumno sin datos que permitan identificarlo."""
        from apps.gestion.models import Alumno

        limite = hoy - timedelta(days=365 * ANIOS_INACTIVO)
        candidatos = Alumno.todos.filter(
            estado=Alumno.Estado.INACTIVO,
            updated_at__date__lt=limite,
        ).exclude(nombre_completo__startswith='Alumno anonimizado')

        cantidad = candidatos.count()
        self.stdout.write(f'Alumnos inactivos hace más de {ANIOS_INACTIVO} años: {cantidad}')

        if simular or not cantidad:
            for alumno in candidatos[:5]:
                self.stdout.write(f'    · {alumno.nombre_completo} ({alumno.rut})')
            return cantidad

        with transaction.atomic():
            for alumno in candidatos:
                if alumno.foto:
                    try:
                        alumno.foto.delete(save=False)
                    except Exception:
                        pass

                alumno.nombre_completo = f'Alumno anonimizado #{alumno.pk}'
                # El RUT se reemplaza por uno imposible, manteniendo la
                # unicidad que la base exige.
                alumno.rut = f'ANON-{alumno.pk}'
                alumno.email = ''
                alumno.telefono = ''
                alumno.direccion = ''
                alumno.fecha_nacimiento = None
                alumno.contacto_emergencia = ''
                alumno.telefono_emergencia = ''
                alumno.observaciones = ''
                alumno.foto = None
                alumno.save()

                alumno.notas.all().delete()
                if alumno.usuario:
                    alumno.usuario.is_active = False
                    alumno.usuario.save(update_fields=['is_active'])

        self.stdout.write(self.style.SUCCESS(f'    {cantidad} alumnos anonimizados'))
        return cantidad

    def _borrar_correos(self, ahora, simular):
        from apps.gestion.models import CorreoEnviado

        viejos = CorreoEnviado.objects.filter(
            created_at__lt=ahora - timedelta(days=DIAS_CORREOS))
        cantidad = viejos.count()
        self.stdout.write(f'Correos de más de {DIAS_CORREOS} días: {cantidad}')
        if not simular and cantidad:
            viejos.delete()
        return cantidad

    def _borrar_auditoria(self, ahora, simular):
        from apps.gestion.models import AuditLog

        viejos = AuditLog.objects.filter(
            timestamp__lt=ahora - timedelta(days=DIAS_AUDITORIA))
        cantidad = viejos.count()
        self.stdout.write(f'Auditoría de más de {DIAS_AUDITORIA} días: {cantidad}')
        if not simular and cantidad:
            viejos.delete()
        return cantidad

    def _borrar_intentos(self, ahora, simular):
        try:
            from axes.models import AccessAttempt, AccessLog
        except ImportError:
            return 0

        limite = ahora - timedelta(days=DIAS_INTENTOS)
        intentos = AccessAttempt.objects.filter(attempt_time__lt=limite)
        accesos = AccessLog.objects.filter(attempt_time__lt=limite)
        cantidad = intentos.count() + accesos.count()
        self.stdout.write(f'Registros de login de más de {DIAS_INTENTOS} días: {cantidad}')
        if not simular and cantidad:
            intentos.delete()
            accesos.delete()
        return cantidad
