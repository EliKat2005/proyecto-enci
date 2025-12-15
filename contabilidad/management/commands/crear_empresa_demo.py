"""
Management command para crear una empresa de demostración con datos de prueba.

Crea:
- Empresa "Comercial Demo S.A."
- Plan de cuentas completo
- Periodos contables para 2025
- Asientos contables de ejemplo (compras, ventas, gastos)
- Datos suficientes para generar todos los reportes

Uso:
    python manage.py crear_empresa_demo --user=admin
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal
from datetime import date

from contabilidad.models import (
    Empresa, EmpresaPlanCuenta, TipoCuenta, NaturalezaCuenta,
    PeriodoContable, EmpresaAsiento, EstadoAsiento
)
from contabilidad.services import AsientoService

User = get_user_model()


class Command(BaseCommand):
    help = 'Crea una empresa de demostración con datos de prueba completos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Username del propietario de la empresa demo',
            default='admin'
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Eliminar empresa demo existente antes de crear'
        )

    def handle(self, *args, **options):
        username = options['user']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'Usuario "{username}" no existe')

        # Verificar si ya existe
        if options['delete']:
            Empresa.objects.filter(nombre='Comercial Demo S.A.').delete()
            self.stdout.write(self.style.SUCCESS('✓ Empresa demo anterior eliminada'))

        if Empresa.objects.filter(nombre='Comercial Demo S.A.').exists():
            raise CommandError(
                'La empresa "Comercial Demo S.A." ya existe. '
                'Use --delete para eliminarla primero.'
            )

        self.stdout.write(self.style.WARNING('Creando empresa de demostración...'))
        
        with transaction.atomic():
            # 1. Crear empresa
            empresa = self._crear_empresa(user)
            self.stdout.write(self.style.SUCCESS(f'✓ Empresa creada: {empresa.nombre}'))
            
            # 2. Crear plan de cuentas
            cuentas = self._crear_plan_cuentas(empresa)
            self.stdout.write(self.style.SUCCESS(f'✓ Plan de cuentas: {len(cuentas)} cuentas'))
            
            # 3. Crear periodos contables
            periodos = self._crear_periodos(empresa)
            self.stdout.write(self.style.SUCCESS(f'✓ Periodos contables: {len(periodos)} periodos'))
            
            # 4. Crear asientos de ejemplo
            asientos = self._crear_asientos_demo(empresa, cuentas, user)
            self.stdout.write(self.style.SUCCESS(f'✓ Asientos creados: {len(asientos)} asientos'))
            
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('✓ EMPRESA DEMO CREADA EXITOSAMENTE'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(f'\nEmpresa ID: {empresa.id}')
        self.stdout.write(f'URL: /contabilidad/{empresa.id}/')
        self.stdout.write(f'\nPrueba los siguientes reportes:')
        self.stdout.write(f'  - Plan de Cuentas: /contabilidad/{empresa.id}/plan/')
        self.stdout.write(f'  - Libro Diario: /contabilidad/{empresa.id}/diario/')
        self.stdout.write(f'  - Libro Mayor: /contabilidad/{empresa.id}/mayor/')
        self.stdout.write(f'  - Balance: /contabilidad/{empresa.id}/balance/')
        self.stdout.write(f'  - Estados: /contabilidad/{empresa.id}/estados/')

    def _crear_empresa(self, user):
        """Crea la empresa de demostración."""
        return Empresa.objects.create(
            nombre='Comercial Demo S.A.',
            descripcion='Empresa de demostración con datos de prueba completos para validar el sistema contable.',
            owner=user,
            is_template=False,
            visible_to_supervisor=True
        )

    def _crear_plan_cuentas(self, empresa):
        """Crea un plan de cuentas completo."""
        cuentas_map = {}
        
        # ACTIVOS
        cuentas_map['activo'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='1', descripcion='ACTIVO',
            tipo=TipoCuenta.ACTIVO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=False, estado_situacion=True
        )
        
        cuentas_map['activo_corriente'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='1.1', descripcion='ACTIVO CORRIENTE',
            tipo=TipoCuenta.ACTIVO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=False, estado_situacion=True, padre=cuentas_map['activo']
        )
        
        # Cuentas auxiliares de activo
        cuentas_map['caja'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='1.1.01', descripcion='Caja General',
            tipo=TipoCuenta.ACTIVO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=True, estado_situacion=True, padre=cuentas_map['activo_corriente'],
            activa=True
        )
        
        cuentas_map['banco'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='1.1.02', descripcion='Banco Nacional - Cta. Corriente',
            tipo=TipoCuenta.ACTIVO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=True, estado_situacion=True, padre=cuentas_map['activo_corriente'],
            activa=True
        )
        
        cuentas_map['clientes'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='1.1.03', descripcion='Cuentas por Cobrar - Clientes',
            tipo=TipoCuenta.ACTIVO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=True, estado_situacion=True, padre=cuentas_map['activo_corriente'],
            activa=True
        )
        
        cuentas_map['inventario'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='1.1.04', descripcion='Inventario de Mercaderías',
            tipo=TipoCuenta.ACTIVO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=True, estado_situacion=True, padre=cuentas_map['activo_corriente'],
            activa=True
        )
        
        # PASIVOS
        cuentas_map['pasivo'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='2', descripcion='PASIVO',
            tipo=TipoCuenta.PASIVO, naturaleza=NaturalezaCuenta.ACREEDORA,
            es_auxiliar=False, estado_situacion=True
        )
        
        cuentas_map['pasivo_corriente'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='2.1', descripcion='PASIVO CORRIENTE',
            tipo=TipoCuenta.PASIVO, naturaleza=NaturalezaCuenta.ACREEDORA,
            es_auxiliar=False, estado_situacion=True, padre=cuentas_map['pasivo']
        )
        
        cuentas_map['proveedores'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='2.1.01', descripcion='Cuentas por Pagar - Proveedores',
            tipo=TipoCuenta.PASIVO, naturaleza=NaturalezaCuenta.ACREEDORA,
            es_auxiliar=True, estado_situacion=True, padre=cuentas_map['pasivo_corriente'],
            activa=True
        )
        
        cuentas_map['iva_credito'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='2.1.02', descripcion='IVA por Pagar',
            tipo=TipoCuenta.PASIVO, naturaleza=NaturalezaCuenta.ACREEDORA,
            es_auxiliar=True, estado_situacion=True, padre=cuentas_map['pasivo_corriente'],
            activa=True
        )
        
        # PATRIMONIO
        cuentas_map['patrimonio'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='3', descripcion='PATRIMONIO',
            tipo=TipoCuenta.PATRIMONIO, naturaleza=NaturalezaCuenta.ACREEDORA,
            es_auxiliar=False, estado_situacion=True
        )
        
        cuentas_map['capital'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='3.1', descripcion='Capital Social',
            tipo=TipoCuenta.PATRIMONIO, naturaleza=NaturalezaCuenta.ACREEDORA,
            es_auxiliar=True, estado_situacion=True, padre=cuentas_map['patrimonio'],
            activa=True
        )

        # Resultados del Ejercicio (Patrimonio)
        cuentas_map['resultados'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='3.2', descripcion='Resultados del Ejercicio',
            tipo=TipoCuenta.PATRIMONIO, naturaleza=NaturalezaCuenta.ACREEDORA,
            es_auxiliar=True, estado_situacion=True, padre=cuentas_map['patrimonio'],
            activa=True
        )
        
        # INGRESOS
        cuentas_map['ingresos'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='4', descripcion='INGRESOS',
            tipo=TipoCuenta.INGRESO, naturaleza=NaturalezaCuenta.ACREEDORA,
            es_auxiliar=False, estado_situacion=False
        )
        
        cuentas_map['ventas'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='4.1', descripcion='Ventas de Mercaderías',
            tipo=TipoCuenta.INGRESO, naturaleza=NaturalezaCuenta.ACREEDORA,
            es_auxiliar=True, estado_situacion=False, padre=cuentas_map['ingresos'],
            activa=True
        )
        
        # COSTOS
        cuentas_map['costos'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='5', descripcion='COSTOS',
            tipo=TipoCuenta.COSTO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=False, estado_situacion=False
        )
        
        cuentas_map['costo_ventas'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='5.1', descripcion='Costo de Ventas',
            tipo=TipoCuenta.COSTO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=True, estado_situacion=False, padre=cuentas_map['costos'],
            activa=True
        )
        
        # GASTOS
        cuentas_map['gastos'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='6', descripcion='GASTOS',
            tipo=TipoCuenta.GASTO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=False, estado_situacion=False
        )
        
        cuentas_map['gastos_admin'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='6.1', descripcion='GASTOS ADMINISTRATIVOS',
            tipo=TipoCuenta.GASTO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=False, estado_situacion=False, padre=cuentas_map['gastos']
        )
        
        cuentas_map['sueldos'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='6.1.01', descripcion='Sueldos y Salarios',
            tipo=TipoCuenta.GASTO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=True, estado_situacion=False, padre=cuentas_map['gastos_admin'],
            activa=True
        )
        
        cuentas_map['arriendo'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='6.1.02', descripcion='Arriendo de Local',
            tipo=TipoCuenta.GASTO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=True, estado_situacion=False, padre=cuentas_map['gastos_admin'],
            activa=True
        )
        
        cuentas_map['servicios'] = EmpresaPlanCuenta.objects.create(
            empresa=empresa, codigo='6.1.03', descripcion='Servicios Básicos',
            tipo=TipoCuenta.GASTO, naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=True, estado_situacion=False, padre=cuentas_map['gastos_admin'],
            activa=True
        )
        
        return cuentas_map

    def _crear_periodos(self, empresa):
        """Crea periodos contables para 2025."""
        periodos = []
        for mes in range(1, 13):
            periodo = PeriodoContable.objects.create(
                empresa=empresa,
                anio=2025,
                mes=mes,
                estado=PeriodoContable.EstadoPeriodo.ABIERTO
            )
            periodos.append(periodo)
        return periodos

    def _crear_asientos_demo(self, empresa, cuentas, user):
        """Crea asientos de ejemplo para demostración."""
        asientos = []
        
        # 1. Asiento de Apertura - Capital Inicial
        asiento1 = AsientoService.crear_asiento(
            empresa=empresa,
            fecha=date(2025, 1, 1),
            descripcion='ASIENTO DE APERTURA - Capital inicial',
            lineas=[
                {
                    'cuenta_id': cuentas['banco'].id,
                    'detalle': 'Aporte inicial en banco',
                    'debe': Decimal('50000.00'),
                    'haber': Decimal('0.00')
                },
                {
                    'cuenta_id': cuentas['capital'].id,
                    'detalle': 'Capital social suscrito',
                    'debe': Decimal('0.00'),
                    'haber': Decimal('50000.00')
                }
            ],
            creado_por=user,
            auto_confirmar=True
        )
        asientos.append(asiento1)
        
        # 2. Compra de Inventario
        asiento2 = AsientoService.crear_asiento(
            empresa=empresa,
            fecha=date(2025, 1, 5),
            descripcion='Compra de mercadería según factura #001',
            lineas=[
                {
                    'cuenta_id': cuentas['inventario'].id,
                    'detalle': 'Mercadería según factura #001',
                    'debe': Decimal('8000.00'),
                    'haber': Decimal('0.00')
                },
                {
                    'cuenta_id': cuentas['proveedores'].id,
                    'detalle': 'Por pagar a Proveedor ABC',
                    'debe': Decimal('0.00'),
                    'haber': Decimal('8000.00')
                }
            ],
            creado_por=user,
            auto_confirmar=True
        )
        asientos.append(asiento2)
        
        # 3. Venta de Mercadería (mayor a $1,000 - bancarización)
        asiento3 = AsientoService.crear_asiento(
            empresa=empresa,
            fecha=date(2025, 1, 10),
            descripcion='Venta de mercadería según factura #001',
            lineas=[
                {
                    'cuenta_id': cuentas['banco'].id,
                    'detalle': 'Cobro factura #001 - Cliente XYZ',
                    'debe': Decimal('5000.00'),
                    'haber': Decimal('0.00')
                },
                {
                    'cuenta_id': cuentas['ventas'].id,
                    'detalle': 'Venta según factura #001',
                    'debe': Decimal('0.00'),
                    'haber': Decimal('5000.00')
                }
            ],
            creado_por=user,
            auto_confirmar=True
        )
        asientos.append(asiento3)
        
        # 4. Registro del Costo de Venta
        asiento4 = AsientoService.crear_asiento(
            empresa=empresa,
            fecha=date(2025, 1, 10),
            descripcion='Costo de mercadería vendida',
            lineas=[
                {
                    'cuenta_id': cuentas['costo_ventas'].id,
                    'detalle': 'Costo de venta factura #001',
                    'debe': Decimal('3000.00'),
                    'haber': Decimal('0.00')
                },
                {
                    'cuenta_id': cuentas['inventario'].id,
                    'detalle': 'Salida de inventario',
                    'debe': Decimal('0.00'),
                    'haber': Decimal('3000.00')
                }
            ],
            creado_por=user,
            auto_confirmar=True
        )
        asientos.append(asiento4)
        
        # 5. Pago a Proveedor
        asiento5 = AsientoService.crear_asiento(
            empresa=empresa,
            fecha=date(2025, 1, 15),
            descripcion='Pago parcial a proveedor ABC',
            lineas=[
                {
                    'cuenta_id': cuentas['proveedores'].id,
                    'detalle': 'Abono a deuda factura #001',
                    'debe': Decimal('4000.00'),
                    'haber': Decimal('0.00')
                },
                {
                    'cuenta_id': cuentas['banco'].id,
                    'detalle': 'Pago mediante transferencia',
                    'debe': Decimal('0.00'),
                    'haber': Decimal('4000.00')
                }
            ],
            creado_por=user,
            auto_confirmar=True
        )
        asientos.append(asiento5)
        
        # 6. Pago de Arriendo (menor a $1,000 - puede usar caja)
        asiento6 = AsientoService.crear_asiento(
            empresa=empresa,
            fecha=date(2025, 1, 31),
            descripcion='Pago arriendo de local - Enero 2025',
            lineas=[
                {
                    'cuenta_id': cuentas['arriendo'].id,
                    'detalle': 'Arriendo mes de enero',
                    'debe': Decimal('800.00'),
                    'haber': Decimal('0.00')
                },
                {
                    'cuenta_id': cuentas['caja'].id,
                    'detalle': 'Pago en efectivo',
                    'debe': Decimal('0.00'),
                    'haber': Decimal('800.00')
                }
            ],
            creado_por=user,
            auto_confirmar=True
        )
        asientos.append(asiento6)
        
        # 7. Pago de Sueldos (mayor a $1,000 - debe usar banco)
        asiento7 = AsientoService.crear_asiento(
            empresa=empresa,
            fecha=date(2025, 1, 31),
            descripcion='Pago de sueldos - Enero 2025',
            lineas=[
                {
                    'cuenta_id': cuentas['sueldos'].id,
                    'detalle': 'Sueldos personal enero',
                    'debe': Decimal('3500.00'),
                    'haber': Decimal('0.00')
                },
                {
                    'cuenta_id': cuentas['banco'].id,
                    'detalle': 'Pago mediante transferencia bancaria',
                    'debe': Decimal('0.00'),
                    'haber': Decimal('3500.00')
                }
            ],
            creado_por=user,
            auto_confirmar=True
        )
        asientos.append(asiento7)
        
        # 8. Servicios Básicos
        asiento8 = AsientoService.crear_asiento(
            empresa=empresa,
            fecha=date(2025, 1, 31),
            descripcion='Pago servicios básicos - Enero 2025',
            lineas=[
                {
                    'cuenta_id': cuentas['servicios'].id,
                    'detalle': 'Luz, agua, internet',
                    'debe': Decimal('250.00'),
                    'haber': Decimal('0.00')
                },
                {
                    'cuenta_id': cuentas['banco'].id,
                    'detalle': 'Pago servicios básicos',
                    'debe': Decimal('0.00'),
                    'haber': Decimal('250.00')
                }
            ],
            creado_por=user,
            auto_confirmar=True
        )
        asientos.append(asiento8)
        
        # 9. Venta a Crédito
        asiento9 = AsientoService.crear_asiento(
            empresa=empresa,
            fecha=date(2025, 2, 5),
            descripcion='Venta a crédito según factura #002',
            lineas=[
                {
                    'cuenta_id': cuentas['clientes'].id,
                    'detalle': 'Venta a crédito - Cliente ABC',
                    'debe': Decimal('3500.00'),
                    'haber': Decimal('0.00')
                },
                {
                    'cuenta_id': cuentas['ventas'].id,
                    'detalle': 'Venta según factura #002',
                    'debe': Decimal('0.00'),
                    'haber': Decimal('3500.00')
                }
            ],
            creado_por=user,
            auto_confirmar=True
        )
        asientos.append(asiento9)
        
        # 10. Costo de Venta a Crédito
        asiento10 = AsientoService.crear_asiento(
            empresa=empresa,
            fecha=date(2025, 2, 5),
            descripcion='Costo de mercadería vendida a crédito',
            lineas=[
                {
                    'cuenta_id': cuentas['costo_ventas'].id,
                    'detalle': 'Costo factura #002',
                    'debe': Decimal('2000.00'),
                    'haber': Decimal('0.00')
                },
                {
                    'cuenta_id': cuentas['inventario'].id,
                    'detalle': 'Salida de inventario',
                    'debe': Decimal('0.00'),
                    'haber': Decimal('2000.00')
                }
            ],
            creado_por=user,
            auto_confirmar=True
        )
        asientos.append(asiento10)
        
        return asientos
