"""
Management command para importar Plan de Cuentas desde Excel.

Uso:
    python manage.py importar_plan_cuentas --empresa-id 26 --file plan.xlsx
    python manage.py importar_plan_cuentas --empresa-id 26 --file plan.xlsx --dry-run
    python manage.py importar_plan_cuentas --empresa-id 26 --file plan.xlsx --auto-corregir
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from pathlib import Path

from contabilidad.models import Empresa
from contabilidad.services_excel_import import ExcelImportService


class Command(BaseCommand):
    help = 'Importa un Plan de Cuentas desde un archivo Excel con validación'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            required=True,
            help='ID de la empresa donde importar el plan de cuentas'
        )
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Ruta al archivo Excel (.xlsx)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular importación sin guardar cambios'
        )
        parser.add_argument(
            '--auto-corregir',
            action='store_true',
            help='Aplicar correcciones automáticas sin preguntar'
        )

    def handle(self, *args, **options):
        empresa_id = options['empresa_id']
        ruta_archivo = options['file']
        es_dry_run = options['dry_run']
        auto_corregir = options['auto_corregir']

        # Validar empresa
        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            raise CommandError(f'Empresa con ID {empresa_id} no existe')

        # Validar archivo
        ruta = Path(ruta_archivo)
        if not ruta.exists():
            raise CommandError(f'Archivo no encontrado: {ruta_archivo}')

        if not ruta.suffix.lower() in ['.xlsx', '.xls']:
            raise CommandError(f'El archivo debe ser Excel (.xlsx o .xls)')

        self.stdout.write(self.style.HTTP_INFO('\n' + '=' * 80))
        self.stdout.write(self.style.HTTP_INFO('IMPORTADOR DE PLAN DE CUENTAS'))
        self.stdout.write(self.style.HTTP_INFO('=' * 80))

        self.stdout.write(f'\nEmpresa: {empresa.nombre} (ID: {empresa_id})')
        self.stdout.write(f'Archivo: {ruta_archivo}')
        if es_dry_run:
            self.stdout.write(self.style.WARNING('⚠️  Modo: DRY-RUN (sin guardar cambios)'))

        # Paso 1: Cargar archivo
        self.stdout.write('\n📂 Paso 1: Cargando archivo Excel...')
        servicio = ExcelImportService(str(ruta))
        if not servicio.cargar_archivo():
            for error in servicio.errores:
                self.stdout.write(self.style.ERROR(f'  ✗ {error}'))
            raise CommandError('No se pudo cargar el archivo')

        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Archivo cargado: {len(servicio.datos_crudos)} cuentas encontradas'
        ))

        # Paso 2: Validar y corregir
        self.stdout.write('\n🔍 Paso 2: Validando estructura y contenido...')
        datos_corregidos, errores, advertencias = servicio.validar_y_corregir()

        if errores:
            self.stdout.write(self.style.ERROR('\n❌ ERRORES ENCONTRADOS:'))
            for error in errores:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
            raise CommandError('Corrija los errores antes de continuar')

        if servicio.correcciones:
            self.stdout.write(self.style.WARNING('\n✏️  CORRECCIONES AUTOMÁTICAS:'))
            for corr in servicio.correcciones:
                self.stdout.write(self.style.WARNING(f'  - {corr}'))

            if not auto_corregir:
                respuesta = input('\n¿Aplicar estas correcciones? (s/n): ')
                if respuesta.lower() != 's':
                    raise CommandError('Importación cancelada')

        if advertencias:
            self.stdout.write(self.style.WARNING('\n⚠️  ADVERTENCIAS:'))
            for adv in advertencias:
                self.stdout.write(self.style.WARNING(f'  - {adv}'))

        # Paso 3: Validar jerarquía
        self.stdout.write('\n🏗️  Paso 3: Validando jerarquía de cuentas...')
        errores_jerarquia = servicio.validar_jerarquia(datos_corregidos)

        if errores_jerarquia:
            self.stdout.write(self.style.ERROR('\n❌ ERRORES EN JERARQUÍA:'))
            for error in errores_jerarquia:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
            raise CommandError('Corrija los errores de jerarquía antes de continuar')

        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Jerarquía válida: {len(datos_corregidos)} cuentas con estructura correcta'
        ))

        # Paso 4: Mostrar resumen
        self.stdout.write('\n📊 RESUMEN PRE-IMPORTACIÓN:')
        cuentas_sin_padre = [d for d in datos_corregidos if not d['codigo_padre']]
        cuentas_con_padre = [d for d in datos_corregidos if d['codigo_padre']]

        self.stdout.write(f'  Total cuentas a importar: {len(datos_corregidos)}')
        self.stdout.write(f'    - Cuentas principales: {len(cuentas_sin_padre)}')
        self.stdout.write(f'    - Cuentas subordinadas: {len(cuentas_con_padre)}')

        # Mostrar tipos
        tipos = {}
        for d in datos_corregidos:
            tipos[d['tipo']] = tipos.get(d['tipo'], 0) + 1

        self.stdout.write(f'  Distribución por tipo:')
        for tipo, cantidad in sorted(tipos.items()):
            self.stdout.write(f'    - {tipo}: {cantidad}')

        # Paso 5: Confirmar importación
        if not es_dry_run:
            respuesta = input('\n¿Proceder con la importación? (s/n): ')
            if respuesta.lower() != 's':
                raise CommandError('Importación cancelada')

        # Paso 6: Importar
        self.stdout.write('\n⬆️  Paso 5: Importando a base de datos...')

        if es_dry_run:
            self.stdout.write(self.style.WARNING('(Modo DRY-RUN: No se guardan cambios)'))
            cantidad_importada = len(datos_corregidos)
            errores_import = []
        else:
            with transaction.atomic():
                cantidad_importada, errores_import = servicio.importar(empresa, datos_corregidos)

        if errores_import:
            self.stdout.write(self.style.ERROR('\n❌ ERRORES DURANTE IMPORTACIÓN:'))
            for error in errores_import:
                self.stdout.write(self.style.ERROR(f'  - {error}'))

        # Resultado final
        self.stdout.write('\n' + '=' * 80)
        if cantidad_importada == len(datos_corregidos):
            self.stdout.write(self.style.SUCCESS(
                f'✓ IMPORTACIÓN EXITOSA: {cantidad_importada} cuentas importadas'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'⚠️  IMPORTACIÓN PARCIAL: {cantidad_importada}/{len(datos_corregidos)} cuentas importadas'
            ))

        if es_dry_run:
            self.stdout.write(self.style.WARNING(
                'Nota: Modo DRY-RUN, los cambios no fueron guardados'
            ))

        self.stdout.write('=' * 80 + '\n')
