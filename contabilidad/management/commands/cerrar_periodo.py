"""
Management command para cerrar un periodo contable y generar el asiento de cierre.

Uso:
    python manage.py cerrar_periodo --empresa-id=26 --anio=2025 --mes=1 --user=admin
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import date

from contabilidad.models import Empresa, PeriodoContable
from contabilidad.services import EstadosFinancierosService

User = get_user_model()

class Command(BaseCommand):
    help = 'Cierra un periodo contable y genera el asiento de cierre del ejercicio parcial'

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, required=True)
        parser.add_argument('--anio', type=int, required=True)
        parser.add_argument('--mes', type=int, required=True)
        parser.add_argument('--user', type=str, default='admin')

    def handle(self, *args, **options):
        empresa_id = options['empresa_id']
        anio = options['anio']
        mes = options['mes']
        username = options['user']

        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            raise CommandError(f'Empresa id={empresa_id} no existe')

        try:
            usuario = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'Usuario "{username}" no existe')

        try:
            periodo = PeriodoContable.objects.get(empresa=empresa, anio=anio, mes=mes)
        except PeriodoContable.DoesNotExist:
            raise CommandError(f'Periodo {mes}/{anio} no existe para empresa {empresa_id}')

        # Usar último día real del mes
        from calendar import monthrange
        ultimo_dia = monthrange(anio, mes)[1]
        fecha_cierre = date(anio, mes, ultimo_dia)

        self.stdout.write(self.style.WARNING('Cerrando periodo...'))
        with transaction.atomic():
            # Generar asiento de cierre parcial (hasta fecha_cierre)
            EstadosFinancierosService.asiento_de_cierre(empresa, fecha_cierre, usuario)
            periodo.estado = PeriodoContable.EstadoPeriodo.CERRADO
            periodo.save()
        self.stdout.write(self.style.SUCCESS('✓ Periodo cerrado y asiento de cierre generado'))
