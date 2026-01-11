"""
Comando Django para generar datos de prueba ML/AI.
"""

from datetime import date, timedelta
from decimal import Decimal
from random import choice, randint, uniform

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from contabilidad.models import (
    Empresa,
    EmpresaAsiento,
    EmpresaPlanCuenta,
    EmpresaTercero,
    EmpresaTransaccion,
    EstadoAsiento,
    NaturalezaCuenta,
    TipoCuenta,
)

User = get_user_model()

# Configuración
EMPRESA_ID = 1
NUM_ASIENTOS = 60
MESES_HISTORIA = 12


class Command(BaseCommand):
    help = "Genera datos de prueba completos para funcionalidades ML/AI"

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa-id", type=int, default=EMPRESA_ID, help="ID de la empresa (default: 1)"
        )
        parser.add_argument(
            "--num-asientos",
            type=int,
            default=NUM_ASIENTOS,
            help=f"Número de asientos a generar (default: {NUM_ASIENTOS})",
        )
        parser.add_argument(
            "--meses",
            type=int,
            default=MESES_HISTORIA,
            help=f"Meses de historia (default: {MESES_HISTORIA})",
        )

    def handle(self, *args, **options):
        empresa_id = options["empresa_id"]
        num_asientos = options["num_asientos"]
        meses_historia = options["meses"]

        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("  🚀 GENERADOR DE DATOS ML/AI PARA CONTABILIDAD"))
        self.stdout.write("=" * 60)
        self.stdout.write("")

        try:
            # Obtener empresa
            self.print_step("🔍 VERIFICANDO EMPRESA")
            empresa = Empresa.objects.get(id=empresa_id)
            self.stdout.write(f"  ✓ Empresa encontrada: {empresa.nombre} (ID: {empresa.id})")
            self.stdout.write(f"  ✓ Propietario: {empresa.owner.username}")

            usuario = empresa.owner

            # Crear plan de cuentas
            cuentas = self.crear_plan_cuentas_completo(empresa)

            # Crear terceros
            terceros = self.crear_terceros(empresa, usuario)

            # Generar asientos históricos
            asientos_creados = self.generar_asientos_historicos(
                empresa, cuentas, terceros, usuario, num_asientos, meses_historia
            )

            # Resumen final
            self.print_step("📊 RESUMEN FINAL")
            self.stdout.write(f"  ✓ Empresa: {empresa.nombre}")
            self.stdout.write(f"  ✓ Cuentas en plan: {len(cuentas)}")
            self.stdout.write(f"  ✓ Terceros: {len(terceros)}")
            self.stdout.write(f"  ✓ Asientos generados: {asientos_creados}")

            self.stdout.write("")
            self.stdout.write("=" * 60)
            self.stdout.write(self.style.SUCCESS("  ✅ DATOS GENERADOS EXITOSAMENTE"))
            self.stdout.write("=" * 60)
            self.stdout.write("")
            self.stdout.write("Ahora puedes probar las funcionalidades ML/AI:")
            self.stdout.write(
                f"  • Dashboard: http://127.0.0.1:8000/contabilidad/{empresa_id}/ml-dashboard/"
            )
            self.stdout.write(
                f"  • Predicciones: http://127.0.0.1:8000/contabilidad/{empresa_id}/ml-predictions/"
            )
            self.stdout.write(
                f"  • Anomalías: http://127.0.0.1:8000/contabilidad/{empresa_id}/ml-anomalies/"
            )
            self.stdout.write(
                f"  • Búsqueda Semántica: http://127.0.0.1:8000/contabilidad/{empresa_id}/ml-embeddings/"
            )

        except Empresa.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Empresa con ID {empresa_id} no encontrada"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error inesperado: {e}"))
            import traceback

            traceback.print_exc()

    def print_step(self, message):
        """Imprime un separador de sección."""
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS(f"  {message}"))
        self.stdout.write("=" * 60)

    def crear_plan_cuentas_completo(self, empresa):
        """Crea un plan de cuentas completo para la empresa."""
        self.print_step("📊 CREANDO PLAN DE CUENTAS COMPLETO")

        # Definición del plan de cuentas
        cuentas_data = [
            # ACTIVO
            {
                "codigo": "1",
                "descripcion": "ACTIVO",
                "tipo": TipoCuenta.ACTIVO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": False,
            },
            {
                "codigo": "1.1",
                "descripcion": "ACTIVO CORRIENTE",
                "tipo": TipoCuenta.ACTIVO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": False,
                "padre": "1",
            },
            {
                "codigo": "1.1.01",
                "descripcion": "CAJA",
                "tipo": TipoCuenta.ACTIVO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "1.1",
            },
            {
                "codigo": "1.1.02",
                "descripcion": "BANCOS",
                "tipo": TipoCuenta.ACTIVO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "1.1",
            },
            {
                "codigo": "1.1.03",
                "descripcion": "CUENTAS POR COBRAR CLIENTES",
                "tipo": TipoCuenta.ACTIVO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "1.1",
            },
            {
                "codigo": "1.1.04",
                "descripcion": "INVENTARIOS",
                "tipo": TipoCuenta.ACTIVO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "1.1",
            },
            {
                "codigo": "1.2",
                "descripcion": "ACTIVO NO CORRIENTE",
                "tipo": TipoCuenta.ACTIVO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": False,
                "padre": "1",
            },
            {
                "codigo": "1.2.01",
                "descripcion": "MUEBLES Y ENSERES",
                "tipo": TipoCuenta.ACTIVO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "1.2",
            },
            {
                "codigo": "1.2.02",
                "descripcion": "EQUIPOS DE OFICINA",
                "tipo": TipoCuenta.ACTIVO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "1.2",
            },
            {
                "codigo": "1.2.03",
                "descripcion": "EQUIPOS DE CÓMPUTO",
                "tipo": TipoCuenta.ACTIVO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "1.2",
            },
            {
                "codigo": "1.2.04",
                "descripcion": "VEHÍCULOS",
                "tipo": TipoCuenta.ACTIVO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "1.2",
            },
            # PASIVO
            {
                "codigo": "2",
                "descripcion": "PASIVO",
                "tipo": TipoCuenta.PASIVO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": False,
            },
            {
                "codigo": "2.1",
                "descripcion": "PASIVO CORRIENTE",
                "tipo": TipoCuenta.PASIVO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": False,
                "padre": "2",
            },
            {
                "codigo": "2.1.01",
                "descripcion": "CUENTAS POR PAGAR PROVEEDORES",
                "tipo": TipoCuenta.PASIVO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": True,
                "padre": "2.1",
            },
            {
                "codigo": "2.1.02",
                "descripcion": "IMPUESTOS POR PAGAR",
                "tipo": TipoCuenta.PASIVO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": True,
                "padre": "2.1",
            },
            {
                "codigo": "2.1.03",
                "descripcion": "SALARIOS POR PAGAR",
                "tipo": TipoCuenta.PASIVO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": True,
                "padre": "2.1",
            },
            {
                "codigo": "2.2",
                "descripcion": "PASIVO NO CORRIENTE",
                "tipo": TipoCuenta.PASIVO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": False,
                "padre": "2",
            },
            {
                "codigo": "2.2.01",
                "descripcion": "PRÉSTAMOS BANCARIOS LARGO PLAZO",
                "tipo": TipoCuenta.PASIVO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": True,
                "padre": "2.2",
            },
            # PATRIMONIO
            {
                "codigo": "3",
                "descripcion": "PATRIMONIO",
                "tipo": TipoCuenta.PATRIMONIO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": False,
            },
            {
                "codigo": "3.1",
                "descripcion": "CAPITAL",
                "tipo": TipoCuenta.PATRIMONIO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": False,
                "padre": "3",
            },
            {
                "codigo": "3.1.01",
                "descripcion": "CAPITAL SOCIAL",
                "tipo": TipoCuenta.PATRIMONIO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": True,
                "padre": "3.1",
            },
            {
                "codigo": "3.2",
                "descripcion": "RESULTADOS",
                "tipo": TipoCuenta.PATRIMONIO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": False,
                "padre": "3",
            },
            {
                "codigo": "3.2.01",
                "descripcion": "UTILIDADES RETENIDAS",
                "tipo": TipoCuenta.PATRIMONIO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": True,
                "padre": "3.2",
            },
            {
                "codigo": "3.2.02",
                "descripcion": "UTILIDAD DEL EJERCICIO",
                "tipo": TipoCuenta.PATRIMONIO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": True,
                "padre": "3.2",
            },
            # INGRESOS
            {
                "codigo": "4",
                "descripcion": "INGRESOS",
                "tipo": TipoCuenta.INGRESO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": False,
            },
            {
                "codigo": "4.1",
                "descripcion": "INGRESOS OPERACIONALES",
                "tipo": TipoCuenta.INGRESO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": False,
                "padre": "4",
            },
            {
                "codigo": "4.1.01",
                "descripcion": "VENTAS DE PRODUCTOS",
                "tipo": TipoCuenta.INGRESO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": True,
                "padre": "4.1",
            },
            {
                "codigo": "4.1.02",
                "descripcion": "PRESTACIÓN DE SERVICIOS",
                "tipo": TipoCuenta.INGRESO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": True,
                "padre": "4.1",
            },
            {
                "codigo": "4.2",
                "descripcion": "INGRESOS NO OPERACIONALES",
                "tipo": TipoCuenta.INGRESO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": False,
                "padre": "4",
            },
            {
                "codigo": "4.2.01",
                "descripcion": "INTERESES GANADOS",
                "tipo": TipoCuenta.INGRESO,
                "naturaleza": NaturalezaCuenta.ACREEDORA,
                "es_auxiliar": True,
                "padre": "4.2",
            },
            # GASTOS
            {
                "codigo": "5",
                "descripcion": "GASTOS",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": False,
            },
            {
                "codigo": "5.1",
                "descripcion": "COSTO DE VENTAS",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": False,
                "padre": "5",
            },
            {
                "codigo": "5.1.01",
                "descripcion": "COSTO DE PRODUCTOS VENDIDOS",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "5.1",
            },
            {
                "codigo": "5.2",
                "descripcion": "GASTOS ADMINISTRATIVOS",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": False,
                "padre": "5",
            },
            {
                "codigo": "5.2.01",
                "descripcion": "SUELDOS Y SALARIOS",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "5.2",
            },
            {
                "codigo": "5.2.02",
                "descripcion": "ARRIENDO",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "5.2",
            },
            {
                "codigo": "5.2.03",
                "descripcion": "SERVICIOS PÚBLICOS",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "5.2",
            },
            {
                "codigo": "5.2.04",
                "descripcion": "ÚTILES Y PAPELERÍA",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "5.2",
            },
            {
                "codigo": "5.3",
                "descripcion": "GASTOS DE VENTAS",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": False,
                "padre": "5",
            },
            {
                "codigo": "5.3.01",
                "descripcion": "COMISIONES DE VENTAS",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "5.3",
            },
            {
                "codigo": "5.3.02",
                "descripcion": "PUBLICIDAD Y MARKETING",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "5.3",
            },
            {
                "codigo": "5.4",
                "descripcion": "GASTOS FINANCIEROS",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": False,
                "padre": "5",
            },
            {
                "codigo": "5.4.01",
                "descripcion": "INTERESES PAGADOS",
                "tipo": TipoCuenta.GASTO,
                "naturaleza": NaturalezaCuenta.DEUDORA,
                "es_auxiliar": True,
                "padre": "5.4",
            },
        ]

        # Crear cuentas
        cuentas_creadas = {}
        for cuenta_data in cuentas_data:
            # Si tiene padre, obtenerlo
            padre = None
            if "padre" in cuenta_data:
                padre = cuentas_creadas.get(cuenta_data["padre"])

            cuenta, created = EmpresaPlanCuenta.objects.get_or_create(
                empresa=empresa,
                codigo=cuenta_data["codigo"],
                defaults={
                    "descripcion": cuenta_data["descripcion"],
                    "tipo": cuenta_data["tipo"],
                    "naturaleza": cuenta_data["naturaleza"],
                    "es_auxiliar": cuenta_data["es_auxiliar"],
                    "activa": True,
                },
            )

            # Actualizar padre si es necesario
            if padre and not cuenta.padre:
                cuenta.padre = padre
                cuenta.save()

            cuentas_creadas[cuenta.codigo] = cuenta

            if created:
                self.stdout.write(f"  ✓ Creada: {cuenta.codigo} - {cuenta.descripcion}")
            else:
                self.stdout.write(f"  → Existente: {cuenta.codigo} - {cuenta.descripcion}")

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"✅ Plan de cuentas completo: {len(cuentas_creadas)} cuentas")
        )
        return cuentas_creadas

    def crear_terceros(self, empresa, usuario):
        """Crea terceros de ejemplo."""
        self.print_step("👥 CREANDO TERCEROS")

        terceros_data = [
            {"tipo": "CLIENTE", "numero_identificacion": "1234567890", "nombre": "JUAN PÉREZ"},
            {"tipo": "CLIENTE", "numero_identificacion": "0987654321", "nombre": "MARÍA GARCÍA"},
            {
                "tipo": "PROVEEDOR",
                "numero_identificacion": "900123456-1",
                "nombre": "PROVEEDOR X S.A.S.",
            },
            {
                "tipo": "PROVEEDOR",
                "numero_identificacion": "900654321-2",
                "nombre": "PROVEEDOR Y LTDA",
            },
            {"tipo": "EMPLEADO", "numero_identificacion": "1122334455", "nombre": "CARLOS LÓPEZ"},
        ]

        terceros_creados = []
        for tercero_data in terceros_data:
            tercero, created = EmpresaTercero.objects.get_or_create(
                empresa=empresa,
                numero_identificacion=tercero_data["numero_identificacion"],
                defaults={
                    "tipo": tercero_data["tipo"],
                    "nombre": tercero_data["nombre"],
                    "creado_por": usuario,
                },
            )
            terceros_creados.append(tercero)
            if created:
                self.stdout.write(f"  ✓ Creado: {tercero.nombre}")
            else:
                self.stdout.write(f"  → Existente: {tercero.nombre}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✅ Terceros creados: {len(terceros_creados)}"))
        return terceros_creados

    def generar_asientos_historicos(
        self, empresa, cuentas, terceros, usuario, num_asientos, meses_historia
    ):
        """Genera asientos contables históricos variados."""
        self.print_step(f"📝 GENERANDO {num_asientos} ASIENTOS HISTÓRICOS")

        # Fecha inicial (hace meses_historia meses)
        fecha_inicial = date.today() - timedelta(days=30 * meses_historia)

        # Cuentas específicas para transacciones
        caja = cuentas.get("1.1.01")
        bancos = cuentas.get("1.1.02")
        cxc_clientes = cuentas.get("1.1.03")
        inventarios = cuentas.get("1.1.04")
        cxp_proveedores = cuentas.get("2.1.01")
        impuestos = cuentas.get("2.1.02")
        salarios_pagar = cuentas.get("2.1.03")
        ventas = cuentas.get("4.1.01")
        servicios = cuentas.get("4.1.02")
        costo_ventas = cuentas.get("5.1.01")
        sueldos = cuentas.get("5.2.01")
        arriendo = cuentas.get("5.2.02")
        servicios_pub = cuentas.get("5.2.03")
        utiles = cuentas.get("5.2.04")
        comisiones = cuentas.get("5.3.01")
        publicidad = cuentas.get("5.3.02")

        asientos_creados = 0

        # Tipos de transacciones con diferentes probabilidades
        tipos_transaccion = [
            ("venta_contado", caja, ventas, 0.25),
            ("venta_credito", cxc_clientes, ventas, 0.15),
            ("cobro_cliente", bancos, cxc_clientes, 0.10),
            ("compra_inventario", inventarios, cxp_proveedores, 0.15),
            ("pago_proveedor", cxp_proveedores, bancos, 0.10),
            ("pago_nomina", sueldos, salarios_pagar, 0.05),
            ("pago_salario", salarios_pagar, bancos, 0.05),
            ("pago_arriendo", arriendo, bancos, 0.03),
            ("pago_servicios", servicios_pub, bancos, 0.03),
            ("gasto_utiles", utiles, caja, 0.02),
            ("comision_ventas", comisiones, bancos, 0.02),
            ("gasto_publicidad", publicidad, bancos, 0.02),
            ("venta_servicio", bancos, servicios, 0.03),
        ]

        for i in range(num_asientos):
            # Fecha aleatoria dentro del rango
            dias_offset = randint(0, 30 * meses_historia)
            fecha = fecha_inicial + timedelta(days=dias_offset)

            # Seleccionar tipo de transacción basado en probabilidades
            rand = uniform(0, 1)
            acum = 0
            tipo_trans = None
            for tipo, cuenta_debito, cuenta_credito, prob in tipos_transaccion:
                acum += prob
                if rand < acum:
                    tipo_trans = (tipo, cuenta_debito, cuenta_credito)
                    break

            if not tipo_trans:
                tipo_trans = tipos_transaccion[0][:3]

            tipo_nombre, cuenta_debito, cuenta_credito = tipo_trans

            # Monto aleatorio según tipo
            if "venta" in tipo_nombre or "cobro" in tipo_nombre:
                monto = Decimal(randint(100000, 5000000))
            elif "pago" in tipo_nombre:
                monto = Decimal(randint(50000, 2000000))
            elif "gasto" in tipo_nombre or "comision" in tipo_nombre:
                monto = Decimal(randint(20000, 500000))
            else:
                monto = Decimal(randint(50000, 1000000))

            # Tercero aleatorio (si aplica)
            tercero = None
            if "cliente" in tipo_nombre or "venta" in tipo_nombre:
                tercero = choice([t for t in terceros if t.tipo == "CLIENTE"])
            elif "proveedor" in tipo_nombre or "compra" in tipo_nombre:
                tercero = choice([t for t in terceros if t.tipo == "PROVEEDOR"])
            elif "nomina" in tipo_nombre or "salario" in tipo_nombre:
                tercero = choice([t for t in terceros if t.tipo == "EMPLEADO"])

            # Crear asiento
            try:
                asiento = EmpresaAsiento.objects.create(
                    empresa=empresa,
                    fecha=fecha,
                    concepto=f"{tipo_nombre.replace('_', ' ').title()} - Asiento {i+1}",
                    estado=EstadoAsiento.CONFIRMADO,
                    creado_por=usuario,
                )

                # Transacción débito
                EmpresaTransaccion.objects.create(
                    asiento=asiento,
                    cuenta=cuenta_debito,
                    tipo_transaccion="D",
                    monto=monto,
                    tercero=tercero,
                )

                # Transacción crédito
                EmpresaTransaccion.objects.create(
                    asiento=asiento,
                    cuenta=cuenta_credito,
                    tipo_transaccion="C",
                    monto=monto,
                    tercero=tercero,
                )

                asientos_creados += 1

                if (i + 1) % 10 == 0:
                    self.stdout.write(f"  ✓ Generados: {i + 1}/{num_asientos} asientos...")

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  ⚠ Error en asiento {i+1}: {e}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✅ Asientos históricos creados: {asientos_creados}"))
        return asientos_creados
