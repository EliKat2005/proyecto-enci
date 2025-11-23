from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date

from contabilidad.models import Empresa, EmpresaPlanCuenta
from contabilidad.services import AsientoService, EstadosFinancierosService


class Command(BaseCommand):
    help = "Crea datos de prueba contables y valida reglas (plan, asientos, bancarización, auxiliares)."

    def handle(self, *args, **options):
        User = get_user_model()
        usuario = User.objects.order_by('id').first()
        if not usuario:
            self.stdout.write(self.style.ERROR('No hay usuarios en el sistema. Cree un usuario primero.'))
            return

        # Crear empresa de pruebas
        empresa, created_emp = Empresa.objects.get_or_create(
            owner=usuario,
            nombre='Empresa Demo Contable',
            defaults={'descripcion': 'Empresa de prueba para validaciones contables.'}
        )
        if created_emp:
            self.stdout.write(self.style.SUCCESS(f'Creada empresa: {empresa.nombre}'))
        else:
            self.stdout.write(self.style.WARNING(f'Usando empresa existente: {empresa.nombre}'))

        # Crear plan de cuentas jerárquico
        def crear_cuenta(codigo, descripcion, tipo, naturaleza, padre=None, aux=False, estado_situacion=True):
            obj, created = EmpresaPlanCuenta.objects.get_or_create(
                empresa=empresa,
                codigo=codigo,
                defaults={
                    'descripcion': descripcion,
                    'tipo': tipo,
                    'naturaleza': naturaleza,
                    'padre': padre,
                    'es_auxiliar': aux,
                    'estado_situacion': estado_situacion,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f' ✓ Cuenta creada {codigo} ({"Aux" if aux else "Grupo"})'))
            return obj

        self.stdout.write(self.style.MIGRATE_HEADING('Creando plan de cuentas...'))
        activo = crear_cuenta('1', 'ACTIVO', 'Activo', 'Deudora', aux=False)
        activo_corriente = crear_cuenta('1.1', 'ACTIVO CORRIENTE', 'Activo', 'Deudora', padre=activo, aux=False)
        caja = crear_cuenta('1.1.01', 'Caja', 'Activo', 'Deudora', padre=activo_corriente, aux=True)
        banco = crear_cuenta('1.1.02', 'Banco', 'Activo', 'Deudora', padre=activo_corriente, aux=True)

        ingreso = crear_cuenta('4', 'INGRESOS', 'Ingreso', 'Acreedora', aux=False, estado_situacion=False)
        ventas = crear_cuenta('4.1', 'VENTAS', 'Ingreso', 'Acreedora', padre=ingreso, aux=False, estado_situacion=False)
        ventas_locales = crear_cuenta('4.1.01', 'Ventas Locales', 'Ingreso', 'Acreedora', padre=ventas, aux=True, estado_situacion=False)

        gasto = crear_cuenta('5', 'GASTOS', 'Gasto', 'Deudora', aux=False, estado_situacion=False)
        gastos_admin = crear_cuenta('5.1', 'Gastos Administrativos', 'Gasto', 'Deudora', padre=gasto, aux=False, estado_situacion=False)
        sueldos = crear_cuenta('5.1.01', 'Sueldos', 'Gasto', 'Deudora', padre=gastos_admin, aux=True, estado_situacion=False)

        patrimonio = crear_cuenta('3', 'PATRIMONIO', 'Patrimonio', 'Acreedora', aux=False)
        resultados_ejercicio = crear_cuenta('3.3', 'Resultados del Ejercicio', 'Patrimonio', 'Acreedora', padre=patrimonio, aux=True)

        # Validaciones de reglas
        self.stdout.write('\n'+self.style.MIGRATE_HEADING('Probando reglas de asiento...'))

        # 1) Intentar asiento desbalanceado
        try:
            AsientoService.crear_asiento(
                empresa=empresa,
                fecha=date.today(),
                descripcion='Asiento desbalanceado (debe != haber)',
                lineas=[
                    {'cuenta_id': caja.id, 'detalle': 'Entrada caja', 'debe': Decimal('100.00'), 'haber': Decimal('0.00')},
                    {'cuenta_id': ventas_locales.id, 'detalle': 'Venta', 'debe': Decimal('0.00'), 'haber': Decimal('90.00')},
                ],
                creado_por=usuario,
                auto_confirmar=True
            )
            self.stdout.write(self.style.ERROR('ERROR: Se creó asiento desbalanceado (esto no debería ocurrir).'))
        except Exception as e:
            self.stdout.write(self.style.SUCCESS(f'Regla partida doble OK: {e}'))

        # 2) Intentar usar cuenta NO auxiliar
        try:
            AsientoService.crear_asiento(
                empresa=empresa,
                fecha=date.today(),
                descripcion='Uso indebido de cuenta no auxiliar',
                lineas=[
                    {'cuenta_id': activo_corriente.id, 'detalle': 'Movimiento inválido', 'debe': Decimal('50.00'), 'haber': Decimal('0.00')},
                    {'cuenta_id': ventas_locales.id, 'detalle': 'Compensación', 'debe': Decimal('0.00'), 'haber': Decimal('50.00')},
                ],
                creado_por=usuario,
                auto_confirmar=False
            )
            self.stdout.write(self.style.ERROR('ERROR: Se permitió movimiento en cuenta no auxiliar.'))
        except Exception as e:
            self.stdout.write(self.style.SUCCESS(f'Regla cuenta auxiliar OK: {e}'))

        # 3) Bancarización: monto > 1000 usando CAJA debe fallar
        try:
            AsientoService.crear_asiento(
                empresa=empresa,
                fecha=date.today(),
                descripcion='Venta grande en efectivo (debería bloquearse)',
                lineas=[
                    {'cuenta_id': caja.id, 'detalle': 'Cobro efectivo', 'debe': Decimal('1500.00'), 'haber': Decimal('0.00')},
                    {'cuenta_id': ventas_locales.id, 'detalle': 'Venta grande', 'debe': Decimal('0.00'), 'haber': Decimal('1500.00')},
                ],
                creado_por=usuario,
                auto_confirmar=True
            )
            self.stdout.write(self.style.ERROR('ERROR: No se bloqueó bancarización con caja.'))
        except Exception as e:
            self.stdout.write(self.style.SUCCESS(f'Regla bancarización OK: {e}'))

        # 4) Bancarización correcta usando Banco
        try:
            asiento_ok = AsientoService.crear_asiento(
                empresa=empresa,
                fecha=date.today(),
                descripcion='Venta grande bancarizada',
                lineas=[
                    {'cuenta_id': banco.id, 'detalle': 'Cobro transferencia', 'debe': Decimal('1500.00'), 'haber': Decimal('0.00')},
                    {'cuenta_id': ventas_locales.id, 'detalle': 'Venta grande', 'debe': Decimal('0.00'), 'haber': Decimal('1500.00')},
                ],
                creado_por=usuario,
                auto_confirmar=True
            )
            self.stdout.write(self.style.SUCCESS(f'Asiento bancarizado correcto creado # {asiento_ok.numero_asiento}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Fallo creación de asiento bancarizado correcto: {e}'))

        # 5) Crear asiento de gasto pequeño (sin bancarización)
        try:
            asiento_gasto = AsientoService.crear_asiento(
                empresa=empresa,
                fecha=date.today(),
                descripcion='Pago de sueldos menor',
                lineas=[
                    {'cuenta_id': sueldos.id, 'detalle': 'Pago sueldos', 'debe': Decimal('800.00'), 'haber': Decimal('0.00')},
                    {'cuenta_id': caja.id, 'detalle': 'Salida efectivo', 'debe': Decimal('0.00'), 'haber': Decimal('800.00')},
                ],
                creado_por=usuario,
                auto_confirmar=True
            )
            self.stdout.write(self.style.SUCCESS(f'Asiento gasto menor creado # {asiento_gasto.numero_asiento}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Fallo asiento gasto menor: {e}'))

        # 6) Estado de resultados de hoy
        try:
            er = EstadosFinancierosService.estado_de_resultados(
                empresa=empresa,
                fecha_inicio=date.today(),
                fecha_fin=date.today()
            )
            self.stdout.write(self.style.MIGRATE_LABEL('Estado de Resultados (Hoy):'))
            self.stdout.write(f"  Ingresos: {er['ingresos']}")
            self.stdout.write(f"  Costos: {er['costos']}")
            self.stdout.write(f"  Gastos: {er['gastos']}")
            self.stdout.write(f"  Utilidad Neta: {er['utilidad_neta']}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error calculando estado de resultados: {e}'))

        self.stdout.write('\n' + self.style.SUCCESS('Seeding y validaciones contables completadas. Revisa las vistas plan y diario.'))
