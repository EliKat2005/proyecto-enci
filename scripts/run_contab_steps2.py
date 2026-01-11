from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from contabilidad.models import (
    Empresa,
    EmpresaPlanCuenta,
    EmpresaTercero,
)
from contabilidad.services import AsientoService, EstadosFinancierosService, LibroMayorService

User = get_user_model()


def run():
    user = User.objects.get(username="santypro")
    emp = Empresa.objects.get(nombre="Empresa Prueba Santy")
    print("Using Empresa id", emp.id, "owner", emp.owner.username)

    from contabilidad.models import NaturalezaCuenta, TipoCuenta

    def ensure(codigo, descripcion, tipo, naturaleza, estado_situacion, es_auxiliar, padre=None):
        obj, created = EmpresaPlanCuenta.objects.get_or_create(
            empresa=emp,
            codigo=codigo,
            defaults={
                "descripcion": descripcion,
                "tipo": tipo,
                "naturaleza": naturaleza,
                "estado_situacion": estado_situacion,
                "es_auxiliar": es_auxiliar,
                "padre": padre,
            },
        )
        if not created:
            obj.descripcion = descripcion
            obj.tipo = tipo
            obj.naturaleza = naturaleza
            obj.estado_situacion = estado_situacion
            obj.es_auxiliar = es_auxiliar
            if padre:
                obj.padre = padre
            obj.save()
        return obj

    c1 = ensure("1", "Activo", TipoCuenta.ACTIVO, NaturalezaCuenta.DEUDORA, True, False)
    c11 = ensure(
        "1.1", "Activo Corriente", TipoCuenta.ACTIVO, NaturalezaCuenta.DEUDORA, True, False, c1
    )
    caja = ensure("1.1.01", "Caja", TipoCuenta.ACTIVO, NaturalezaCuenta.DEUDORA, True, True, c11)
    banco = ensure("1.1.02", "Bancos", TipoCuenta.ACTIVO, NaturalezaCuenta.DEUDORA, True, True, c11)
    ing_ventas = ensure(
        "4.1.01", "Ventas", TipoCuenta.INGRESO, NaturalezaCuenta.ACREEDORA, False, True
    )
    gasto_var = ensure(
        "5.1.01", "Gastos Varios", TipoCuenta.GASTO, NaturalezaCuenta.DEUDORA, False, True
    )

    print("Cuentas creadas/aseguradas:", caja.id, banco.id, ing_ventas.id)

    tercero, tcreated = EmpresaTercero.objects.get_or_create(
        empresa=emp,
        numero_identificacion="99999999",
        defaults={"tipo": "CLIENTE", "nombre": "Cliente Prueba", "creado_por": user},
    )
    print("Tercero id", tercero.id)

    # Crear asiento válido
    try:
        asiento1 = AsientoService.crear_asiento(
            empresa=emp,
            fecha=date.today(),
            descripcion="Venta contado pequeña (script)",
            lineas=[
                {"cuenta_id": caja.id, "detalle": "Cobro en efectivo", "debe": Decimal("800.00")},
                {
                    "cuenta_id": ing_ventas.id,
                    "detalle": "Venta",
                    "haber": Decimal("800.00"),
                    "tercero_id": tercero.id,
                },
            ],
            creado_por=user,
            auto_confirmar=True,
        )
        print("Asiento valido creado id", asiento1.id)
    except Exception as exc:
        print("ERROR creando asiento valido:", exc)

    # Intentar crear asiento que viola bancarizacion
    try:
        asiento2 = AsientoService.crear_asiento(
            empresa=emp,
            fecha=date.today(),
            descripcion="Venta contado grande (debe usar banco) (script)",
            lineas=[
                {
                    "cuenta_id": caja.id,
                    "detalle": "Cobro en efectivo grande",
                    "debe": Decimal("1500.00"),
                },
                {
                    "cuenta_id": ing_ventas.id,
                    "detalle": "Venta grande",
                    "haber": Decimal("1500.00"),
                    "tercero_id": tercero.id,
                },
            ],
            creado_por=user,
            auto_confirmar=True,
        )
        print("Asiento erroneo creado id", asiento2.id)
    except Exception as exc:
        print("Validación bancaria correcta, se rechazó el asiento:", type(exc).__name__, str(exc))

    # Corregir usando banco
    try:
        asiento3 = AsientoService.crear_asiento(
            empresa=emp,
            fecha=date.today(),
            descripcion="Venta a banco (script)",
            lineas=[
                {
                    "cuenta_id": banco.id,
                    "detalle": "Cobro por transferencia",
                    "debe": Decimal("1500.00"),
                },
                {
                    "cuenta_id": ing_ventas.id,
                    "detalle": "Venta grande",
                    "haber": Decimal("1500.00"),
                    "tercero_id": tercero.id,
                },
            ],
            creado_por=user,
            auto_confirmar=True,
        )
        print("Asiento banco creado id", asiento3.id)
    except Exception as exc:
        print("ERROR creando asiento banco:", exc)

    # Reportes
    bal = LibroMayorService.balance_de_comprobacion(emp, fecha=date.today())
    print("\nBalance de Comprobacion (resumen):")
    for item in bal:
        print("-", item["codigo"], item["descripcion"], "D:", item["debe"], "H:", item["haber"])

    ero = EstadosFinancierosService.estado_de_resultados(
        emp, date.today().replace(day=1), date.today()
    )
    print("\nEstado de Resultados (resumen):")
    print("Ingresos:", ero.get("ingresos"))
    print("Gastos:", ero.get("gastos"))
    print("Utilidad Neta:", ero.get("utilidad_neta"))

    print("\nDONE")


if __name__ == "__main__":
    run()
