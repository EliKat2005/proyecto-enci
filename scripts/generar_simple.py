#!/usr/bin/env python
# ruff: noqa: E402
import os
import sys

import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

print("Configurando Django...")
django.setup()
print("Django configurado correctamente")

from datetime import date, timedelta
from decimal import Decimal
from random import choice, randint

from django.contrib.auth import get_user_model

from contabilidad.models import (
    Empresa,
    EmpresaAsiento,
    EmpresaPlanCuenta,
    EmpresaTercero,
    EmpresaTransaccion,
    EstadoAsiento,
)

print("Imports completados")

User = get_user_model()


def main():
    print("\n" + "=" * 60)
    print("  GENERADOR DE DATOS ML/AI")
    print("=" * 60 + "\n")

    # Obtener empresa
    try:
        empresa = Empresa.objects.get(id=1)
        print(f"✓ Empresa: {empresa.nombre}")
        print(f"✓ Propietario: {empresa.owner.username}\n")
    except Empresa.DoesNotExist:
        print("❌ Empresa ID 1 no encontrada")
        return

    usuario = empresa.owner

    # Crear algunos terceros simples
    print("Creando terceros...")
    terceros_data = [
        {"tipo": "CLIENTE", "numero_identificacion": "TEST001", "nombre": "Cliente Test 1"},
        {"tipo": "PROVEEDOR", "numero_identificacion": "TEST002", "nombre": "Proveedor Test 1"},
    ]

    terceros = []
    for t_data in terceros_data:
        t, created = EmpresaTercero.objects.get_or_create(
            empresa=empresa,
            numero_identificacion=t_data["numero_identificacion"],
            defaults={
                "tipo": t_data["tipo"],
                "nombre": t_data["nombre"],
                "creado_por": usuario,
            },
        )
        terceros.append(t)
        status = "✓ Creado" if created else "→ Existente"
        print(f"  {status}: {t.nombre}")

    # Obtener cuentas existentes
    print("\nObteniendo cuentas...")
    caja = EmpresaPlanCuenta.objects.filter(empresa=empresa, codigo="1.1.01").first()
    ventas = EmpresaPlanCuenta.objects.filter(empresa=empresa, codigo="4.1.01").first()

    if not caja or not ventas:
        print("❌ Cuentas básicas no encontradas (1.1.01, 4.1.01)")
        return

    print(f"  ✓ Caja: {caja.codigo} - {caja.descripcion}")
    print(f"  ✓ Ventas: {ventas.codigo} - {ventas.descripcion}")

    # Generar 60 asientos de ejemplo con más variedad
    print("\nGenerando 60 asientos históricos...")
    fecha_inicial = date.today() - timedelta(days=365)

    # Obtener más cuentas para variedad
    bancos = EmpresaPlanCuenta.objects.filter(empresa=empresa, codigo="1.1.02").first()
    cxc_clientes = EmpresaPlanCuenta.objects.filter(empresa=empresa, codigo="1.1.03").first()
    inventarios = EmpresaPlanCuenta.objects.filter(empresa=empresa, codigo="1.1.04").first()
    cxp_proveedores = EmpresaPlanCuenta.objects.filter(empresa=empresa, codigo="2.1.01").first()
    costo_ventas = EmpresaPlanCuenta.objects.filter(empresa=empresa, codigo="5.1.01").first()
    sueldos = EmpresaPlanCuenta.objects.filter(empresa=empresa, codigo="5.2.01").first()
    arriendo = EmpresaPlanCuenta.objects.filter(empresa=empresa, codigo="5.2.02").first()

    tipos_asientos = [
        # (cuenta_debe, cuenta_haber, descripcion, monto_min, monto_max)
        (caja, ventas, "Venta en efectivo", 100000, 1000000),
        (bancos, ventas, "Venta con tarjeta", 200000, 1500000),
        (cxc_clientes, ventas, "Venta a crédito", 500000, 3000000),
        (bancos, cxc_clientes, "Cobro a cliente", 300000, 2000000),
        (inventarios, cxp_proveedores, "Compra de mercancía", 400000, 2500000),
        (cxp_proveedores, bancos, "Pago a proveedor", 300000, 2000000),
        (costo_ventas, inventarios, "Costo de ventas", 200000, 800000),
        (sueldos, bancos, "Pago de nómina", 1000000, 3000000),
        (arriendo, caja, "Pago de arriendo", 800000, 1500000),
    ]

    for i in range(60):
        # Seleccionar tipo de asiento aleatoriamente
        cuenta_debe, cuenta_haber, descripcion, min_m, max_m = choice(tipos_asientos)

        # Verificar que ambas cuentas existan
        if not cuenta_debe or not cuenta_haber:
            continue

        # Fecha aleatoria en el último año
        dias_offset = randint(0, 360)
        fecha = fecha_inicial + timedelta(days=dias_offset)
        monto = Decimal(randint(min_m, max_m))

        # Seleccionar tercero apropiado
        if (
            "cliente" in descripcion.lower()
            or "cobro" in descripcion.lower()
            or "venta" in descripcion.lower()
        ):
            tercero = terceros[0]
        elif "proveedor" in descripcion.lower() or "compra" in descripcion.lower():
            tercero = terceros[1] if len(terceros) > 1 else None
        else:
            tercero = None

        asiento = EmpresaAsiento.objects.create(
            empresa=empresa,
            fecha=fecha,
            descripcion_general=f"{descripcion} {i+1}",
            estado=EstadoAsiento.CONFIRMADO,
            creado_por=usuario,
        )

        # Transacción débito
        EmpresaTransaccion.objects.create(
            asiento=asiento,
            cuenta=cuenta_debe,
            debe=monto,
            haber=Decimal("0.00"),
            tercero=tercero,
        )

        # Transacción crédito
        EmpresaTransaccion.objects.create(
            asiento=asiento,
            cuenta=cuenta_haber,
            debe=Decimal("0.00"),
            haber=monto,
            tercero=tercero,
        )

        if (i + 1) % 10 == 0:
            print(f"  ✓ Generados {i+1}/60 asientos...")

    print("\n" + "=" * 60)
    print("  ✅ DATOS GENERADOS EXITOSAMENTE")
    print("=" * 60)


if __name__ == "__main__":
    main()
