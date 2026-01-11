from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from contabilidad.models import (
    Empresa,
    EmpresaPlanCuenta,
    EmpresaTercero,
)
from contabilidad.services import (
    AsientoService,
    EstadosFinancierosService,
    LibroMayorService,
)

User = get_user_model()


def run():
    print("INICIANDO: creación de datos de prueba contables")

    # 1) Crear usuario docente
    user, created = User.objects.get_or_create(username="santypro")
    if created:
        user.set_password("santypro123")
        user.is_active = True
        user.save()
        print("Usuario creado: santypro")
    else:
        print("Usuario existente: santypro")

    # 2) Crear empresa ficticia
    emp, ecreated = Empresa.objects.get_or_create(
        nombre="Empresa Prueba Santy",
        defaults={
            "descripcion": "Empresa creada para pruebas por script automatizado",
            "owner": user,
            "is_template": False,
        },
    )
    if not ecreated:
        # asegurar owner
        emp.owner = user
        emp.save()
        print("Empresa ya existía; reasignado owner a santypro")
    else:
        print("Empresa creada: Empresa Prueba Santy")

    # 3) Crear plan de cuentas para la empresa (estructura mínima)
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
            # actualizar campos por si acaso
            obj.descripcion = descripcion
            obj.tipo = tipo
            obj.naturaleza = naturaleza
            obj.estado_situacion = estado_situacion
            obj.es_auxiliar = es_auxiliar
            if padre:
                obj.padre = padre
            obj.save()
        return obj

    # Raíces
    c1 = ensure("1", "Activo", TipoCuenta.ACTIVO, NaturalezaCuenta.DEUDORA, True, False)
    c2 = ensure("2", "Pasivo", TipoCuenta.PASIVO, NaturalezaCuenta.ACREEDORA, True, False)
    c3 = ensure("3", "Patrimonio", TipoCuenta.PATRIMONIO, NaturalezaCuenta.ACREEDORA, True, False)
    c4 = ensure("4", "Ingresos", TipoCuenta.INGRESO, NaturalezaCuenta.ACREEDORA, False, False)
    c5 = ensure("5", "Gastos", TipoCuenta.GASTO, NaturalezaCuenta.DEUDORA, False, False)

    # Subniveles y auxiliares
    c11 = ensure(
        "1.1", "Activo Corriente", TipoCuenta.ACTIVO, NaturalezaCuenta.DEUDORA, True, False, c1
    )
    caja = ensure("1.1.01", "Caja", TipoCuenta.ACTIVO, NaturalezaCuenta.DEUDORA, True, True, c11)
    banco = ensure("1.1.02", "Bancos", TipoCuenta.ACTIVO, NaturalezaCuenta.DEUDORA, True, True, c11)

    ing_ventas = ensure(
        "4.1.01", "Ventas", TipoCuenta.INGRESO, NaturalezaCuenta.ACREEDORA, False, True, c4
    )
    gasto_var = ensure(
        "5.1.01", "Gastos Varios", TipoCuenta.GASTO, NaturalezaCuenta.DEUDORA, False, True, c5
    )

    print(
        f"Plan de cuentas creado con cuentas auxiliares: Caja(id={caja.id}), Banco(id={banco.id}), Ventas(id={ing_ventas.id})"
    )

    # 4) Crear un tercero (cliente)
    tercero, tcreated = EmpresaTercero.objects.get_or_create(
        empresa=emp,
        numero_identificacion="99999999",
        defaults={"tipo": "CLIENTE", "nombre": "Cliente Prueba", "creado_por": user},
    )
    if tcreated:
        print("Tercero creado para la empresa: Cliente Prueba")
    else:
        print("Tercero ya existía")

    # 5) Crear asientos: uno válido (800 en caja) y uno inválido (1500 en caja -> bancarización)
    print("\nCreando asiento VALIDO (Caja 800 vs Ventas 800)")
    try:
        asiento1 = AsientoService.crear_asiento(
            empresa=emp,
            fecha=date.today(),
            descripcion="Venta contado pequeña",
            lineas=[
                {"cuenta_id": caja.id, "detalle": "Cobro en efectivo", "debe": Decimal("800.00")},
                {
                    "cuenta_id": ing_ventas.id,
                    "detalle": "Venta de servicios",
                    "haber": Decimal("800.00"),
                    "tercero_id": tercero.id,
                },
            ],
            creado_por=user,
            auto_confirmar=True,
        )
        print("Asiento creado y confirmado:", asiento1.id, "Total:", asiento1.monto_total)
    except Exception as exc:
        print("ERROR creando asiento valido:", exc)

    print("\nIntentando crear asiento NO-BAcARIZABLE (Caja 1500 -> debe fallar)")
    try:
        asiento2 = AsientoService.crear_asiento(
            empresa=emp,
            fecha=date.today(),
            descripcion="Venta contado grande (debe usar banco)",
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
        print("Asiento erroneamente creado:", asiento2.id)
    except Exception as exc:
        print("Se produjo la validación esperada (bancarización):", type(exc).__name__, str(exc))

    print("\nCreando asiento CORREGIDO usando Banco (1500)")
    try:
        asiento3 = AsientoService.crear_asiento(
            empresa=emp,
            fecha=date.today(),
            descripcion="Venta a cuenta bancaria",
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
        print("Asiento creado y confirmado (banco):", asiento3.id, "Total:", asiento3.monto_total)
    except Exception as exc:
        print("ERROR creando asiento banco:", exc)

    # 6) Reportes: Balance de comprobación y Estado de Resultados
    print("\nGenerando Balance de Comprobación (solo auxiliares con movimiento)")
    from datetime import datetime

    bal = LibroMayorService.balance_de_comprobacion(emp, fecha=datetime.today().date())
    for item in bal:
        print("-", item["codigo"], item["descripcion"], "D:", item["debe"], "H:", item["haber"])

    print("\nGenerando Estado de Resultados (hoy)")
    ero = EstadosFinancierosService.estado_de_resultados(
        emp, date.today().replace(day=1), date.today()
    )
    print("Ingresos:", ero.get("ingresos"))
    print("Costos:", ero.get("costos"))
    print("Gastos:", ero.get("gastos"))
    print("Utilidad Neta:", ero.get("utilidad_neta"))

    print("\nFIN: datos de prueba creados y verificados (revise salidas arriba)")


if __name__ == "__main__":
    run()
