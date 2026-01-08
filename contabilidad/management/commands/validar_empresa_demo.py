"""
Script de validación automática para la empresa demo.

Ejecuta verificaciones programáticas de:
- Partida doble en todos los asientos
- Balance de comprobación cuadrado
- Saldos de cuentas
- Integridad de datos

Uso:
    python manage.py validar_empresa_demo
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Sum

from contabilidad.models import (
    Empresa,
    EmpresaAsiento,
    EmpresaPlanCuenta,
    EmpresaTransaccion,
    PeriodoContable,
)
from contabilidad.services import EstadosFinancierosService, LibroMayorService


class Command(BaseCommand):
    help = "Valida la integridad de los datos de la empresa demo"

    def handle(self, *args, **options):
        try:
            empresa = Empresa.objects.get(nombre="Comercial Demo S.A.")
        except Empresa.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "✗ La empresa demo no existe. Ejecute primero: "
                    "python manage.py crear_empresa_demo"
                )
            )
            return

        self.stdout.write(self.style.WARNING("\n" + "=" * 70))
        self.stdout.write(self.style.WARNING("VALIDACIÓN AUTOMÁTICA - EMPRESA DEMO"))
        self.stdout.write(self.style.WARNING("=" * 70 + "\n"))

        errores = 0
        advertencias = 0

        # 1. Validar estructura de cuentas
        self.stdout.write(self.style.HTTP_INFO("1. Validando estructura del plan de cuentas..."))
        e, w = self._validar_plan_cuentas(empresa)
        errores += e
        advertencias += w

        # 2. Validar asientos contables
        self.stdout.write(self.style.HTTP_INFO("\n2. Validando asientos contables..."))
        e, w = self._validar_asientos(empresa)
        errores += e
        advertencias += w

        # 3. Validar balance de comprobación
        self.stdout.write(self.style.HTTP_INFO("\n3. Validando balance de comprobación..."))
        e, w = self._validar_balance(empresa)
        errores += e
        advertencias += w

        # 4. Validar estados financieros
        self.stdout.write(self.style.HTTP_INFO("\n4. Validando estados financieros..."))
        e, w = self._validar_estados_financieros(empresa)
        errores += e
        advertencias += w

        # 5. Validar periodos
        self.stdout.write(self.style.HTTP_INFO("\n5. Validando periodos contables..."))
        e, w = self._validar_periodos(empresa)
        errores += e
        advertencias += w

        # Resumen final
        self.stdout.write("\n" + "=" * 70)
        if errores == 0 and advertencias == 0:
            self.stdout.write(
                self.style.SUCCESS("✓ VALIDACIÓN EXITOSA - Todos los controles aprobados")
            )
        elif errores == 0:
            self.stdout.write(
                self.style.WARNING(f"⚠ VALIDACIÓN COMPLETADA - {advertencias} advertencia(s)")
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    f"✗ VALIDACIÓN FALLIDA - {errores} error(es), {advertencias} advertencia(s)"
                )
            )
        self.stdout.write("=" * 70 + "\n")

    def _validar_plan_cuentas(self, empresa):
        """Valida la estructura del plan de cuentas."""
        errores = 0
        advertencias = 0

        cuentas = EmpresaPlanCuenta.objects.filter(empresa=empresa)
        total_cuentas = cuentas.count()
        auxiliares = cuentas.filter(es_auxiliar=True).count()

        self.stdout.write(f"  Total cuentas: {total_cuentas}")
        self.stdout.write(f"  Cuentas auxiliares: {auxiliares}")

        # Validar que existen las cuentas principales
        codigos_requeridos = ["1", "2", "3", "4", "5", "6"]
        for codigo in codigos_requeridos:
            if not cuentas.filter(codigo=codigo).exists():
                self.stdout.write(self.style.ERROR(f"  ✗ Falta cuenta principal: {codigo}"))
                errores += 1

        # Validar naturalezas
        for cuenta in cuentas:
            if (
                cuenta.codigo.startswith("1")
                or cuenta.codigo.startswith("5")
                or cuenta.codigo.startswith("6")
            ):
                if cuenta.naturaleza != "Deudora":
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ Cuenta {cuenta.codigo} ({cuenta.naturaleza}) debe tener naturaleza DEUDORA"
                        )
                    )
                    errores += 1
            elif (
                cuenta.codigo.startswith("2")
                or cuenta.codigo.startswith("3")
                or cuenta.codigo.startswith("4")
            ):
                if cuenta.naturaleza != "Acreedora":
                    self.stdout.write(
                        self.style.ERROR(
                            f"  ✗ Cuenta {cuenta.codigo} ({cuenta.naturaleza}) debe tener naturaleza ACREEDORA"
                        )
                    )
                    errores += 1

        if errores == 0:
            self.stdout.write(self.style.SUCCESS("  ✓ Plan de cuentas válido"))

        return errores, advertencias

    def _validar_asientos(self, empresa):
        """Valida que todos los asientos cumplan con partida doble."""
        errores = 0
        advertencias = 0

        asientos = EmpresaAsiento.objects.filter(empresa=empresa)
        total_asientos = asientos.count()
        self.stdout.write(f"  Total asientos: {total_asientos}")

        for asiento in asientos:
            transacciones = EmpresaTransaccion.objects.filter(asiento=asiento)

            total_debe = transacciones.aggregate(total=Sum("debe"))["total"] or Decimal("0")

            total_haber = transacciones.aggregate(total=Sum("haber"))["total"] or Decimal("0")

            diferencia = abs(total_debe - total_haber)

            if diferencia > Decimal("0.01"):  # Tolerancia de 1 centavo
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Asiento #{asiento.numero} desbalanceado: "
                        f"Debe=${total_debe}, Haber=${total_haber}, Diff=${diferencia}"
                    )
                )
                errores += 1

            # Validar que no hay transacciones con debe y haber simultáneos
            transacciones_invalidas = transacciones.filter(debe__gt=0, haber__gt=0).count()

            if transacciones_invalidas > 0:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Asiento #{asiento.numero} tiene {transacciones_invalidas} "
                        f"línea(s) con debe y haber simultáneos"
                    )
                )
                errores += 1

        if errores == 0:
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ Todos los {total_asientos} asientos cumplen partida doble")
            )

        return errores, advertencias

    def _validar_balance(self, empresa):
        """Valida que el balance de comprobación cuadra."""
        errores = 0
        advertencias = 0

        # Obtener todas las transacciones
        transacciones = EmpresaTransaccion.objects.filter(
            asiento__empresa=empresa, asiento__estado="CONFIRMADO"
        )

        total_debe = transacciones.aggregate(total=Sum("debe"))["total"] or Decimal("0")
        total_haber = transacciones.aggregate(total=Sum("haber"))["total"] or Decimal("0")

        diferencia = abs(total_debe - total_haber)

        self.stdout.write(f"  Total Debe: ${total_debe:,.2f}")
        self.stdout.write(f"  Total Haber: ${total_haber:,.2f}")
        self.stdout.write(f"  Diferencia: ${diferencia:,.2f}")

        if diferencia > Decimal("0.01"):
            self.stdout.write(
                self.style.ERROR(f"  ✗ Balance de comprobación descuadrado: ${diferencia}")
            )
            errores += 1
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ Balance de comprobación cuadrado"))

        # Validar saldos por cuenta
        cuentas_auxiliares = EmpresaPlanCuenta.objects.filter(empresa=empresa, es_auxiliar=True)

        for cuenta in cuentas_auxiliares:
            resultado = LibroMayorService.calcular_saldos_cuenta(cuenta)
            saldo_final = resultado["saldo_final"]

            # Advertencia si cuenta tiene saldo negativo contra su naturaleza
            if cuenta.naturaleza == "DEUDORA" and saldo_final < 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Cuenta {cuenta.codigo} ({cuenta.descripcion}) "
                        f"tiene saldo acreedor ${abs(saldo_final):,.2f} (naturaleza deudora)"
                    )
                )
                advertencias += 1
            elif cuenta.naturaleza == "ACREEDORA" and saldo_final > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Cuenta {cuenta.codigo} ({cuenta.descripcion}) "
                        f"tiene saldo deudor ${saldo_final:,.2f} (naturaleza acreedora)"
                    )
                )
                advertencias += 1

        return errores, advertencias

    def _validar_estados_financieros(self, empresa):
        """Valida los estados financieros."""
        errores = 0
        advertencias = 0

        fecha_corte = date(2025, 1, 31)

        # Balance General
        balance = EstadosFinancierosService.balance_general(empresa, fecha_corte)

        total_activo = balance["activos"]
        total_pasivo = balance["pasivos"]
        total_patrimonio = balance["patrimonio"]

        self.stdout.write(f"  Total Activo: ${total_activo:,.2f}")
        self.stdout.write(f"  Total Pasivo: ${total_pasivo:,.2f}")
        self.stdout.write(f"  Total Patrimonio: ${total_patrimonio:,.2f}")

        diferencia = total_activo - (total_pasivo + total_patrimonio)

        if abs(diferencia) > Decimal("0.01"):
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ Balance General descuadrado: ${abs(diferencia):,.2f}\n"
                    f"    Esto es normal si no se ha cerrado el periodo.\n"
                    f"    La utilidad/pérdida debe trasladarse al patrimonio."
                )
            )
            advertencias += 1
        else:
            self.stdout.write(
                self.style.SUCCESS("  ✓ Balance General cuadrado (Activo = Pasivo + Patrimonio)")
            )

        # Estado de Resultados
        resultados = EstadosFinancierosService.estado_de_resultados(
            empresa=empresa, fecha_inicio=date(2025, 1, 1), fecha_fin=fecha_corte
        )

        utilidad_neta = resultados["utilidad_neta"]
        self.stdout.write(f"  Utilidad Neta del periodo: ${utilidad_neta:,.2f}")

        if utilidad_neta < 0:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ La empresa tiene pérdida de ${abs(utilidad_neta):,.2f}\n"
                    f"    Esto es normal en los primeros meses de operación."
                )
            )
            advertencias += 1

        return errores, advertencias

    def _validar_periodos(self, empresa):
        """Valida los periodos contables."""
        errores = 0
        advertencias = 0

        periodos = PeriodoContable.objects.filter(empresa=empresa)
        total_periodos = periodos.count()

        self.stdout.write(f"  Total periodos: {total_periodos}")

        if total_periodos != 12:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ Se esperaban 12 periodos (año completo), se encontraron {total_periodos}"
                )
            )
            advertencias += 1

        periodos_abiertos = periodos.filter(estado="ABIERTO").count()
        periodos_cerrados = periodos.filter(estado="CERRADO").count()

        self.stdout.write(f"  Periodos abiertos: {periodos_abiertos}")
        self.stdout.write(f"  Periodos cerrados: {periodos_cerrados}")

        if errores == 0:
            self.stdout.write(self.style.SUCCESS("  ✓ Periodos contables válidos"))

        return errores, advertencias
