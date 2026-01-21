#!/usr/bin/env python
"""
Script para generar asientos contables de ejemplo que permitan
visualizar correctamente el dashboard ML/AI.
"""

import os
import sys
import django
from decimal import Decimal
from datetime import date, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from contabilidad.models import (
    Empresa, EmpresaAsiento, EmpresaTransaccion, 
    EmpresaPlanCuenta, EstadoAsiento
)
from django.contrib.auth import get_user_model

User = get_user_model()

def crear_asientos_ejemplo():
    """Crea asientos de ejemplo para demostrar el dashboard ML/AI."""
    
    # Obtener empresa y usuario
    empresa = Empresa.objects.get(pk=1)
    usuario = User.objects.get(username='elikat')
    
    print("=" * 70)
    print(f"GENERANDO ASIENTOS DE EJEMPLO PARA: {empresa.nombre}")
    print("=" * 70)
    
    # Verificar cuentas necesarias (deben ser AUXILIARES)
    cuentas = {
        'activo': EmpresaPlanCuenta.objects.filter(empresa=empresa, tipo='Activo', es_auxiliar=True).first(),
        'pasivo': EmpresaPlanCuenta.objects.filter(empresa=empresa, tipo='Pasivo', es_auxiliar=True).first(),
        'patrimonio': EmpresaPlanCuenta.objects.filter(empresa=empresa, tipo='Patrimonio', es_auxiliar=True).first(),
        'ingreso': EmpresaPlanCuenta.objects.filter(empresa=empresa, tipo='Ingreso', es_auxiliar=True).first(),
        'gasto': EmpresaPlanCuenta.objects.filter(empresa=empresa, tipo='Gasto', es_auxiliar=True).first(),
        'costo': EmpresaPlanCuenta.objects.filter(empresa=empresa, tipo='Costo', es_auxiliar=True).first(),
    }
    
    # Verificar que existen todas las cuentas
    faltantes = [k for k, v in cuentas.items() if v is None]
    if faltantes:
        print(f"\n⚠️  ADVERTENCIA: Faltan cuentas: {', '.join(faltantes)}")
        return
    
    print("\n✓ Cuentas disponibles:")
    for tipo, cuenta in cuentas.items():
        print(f"  - {tipo.capitalize():12s}: {cuenta.codigo} - {cuenta.descripcion}")
    
    # Fecha base
    fecha_base = date.today() - timedelta(days=15)
    
    asientos_creados = []
    
    # 1. Asiento de Apertura (Capital inicial)
    print("\n1️⃣  Creando asiento de apertura (Capital inicial)...")
    asiento1 = EmpresaAsiento.objects.create(
        empresa=empresa,
        fecha=fecha_base,
        descripcion_general="Apertura - Capital inicial en efectivo",
        estado=EstadoAsiento.CONFIRMADO,
        creado_por=usuario
    )
    EmpresaTransaccion.objects.create(
        asiento=asiento1,
        cuenta=cuentas['activo'],  # Efectivo/Caja
        detalle_linea="Efectivo inicial",
        debe=Decimal('50000.00'),
        haber=Decimal('0.00'),
        creado_por=usuario
    )
    EmpresaTransaccion.objects.create(
        asiento=asiento1,
        cuenta=cuentas['patrimonio'],  # Capital
        detalle_linea="Capital social",
        debe=Decimal('0.00'),
        haber=Decimal('50000.00'),
        creado_por=usuario
    )
    asientos_creados.append(f"#{asiento1.numero_asiento} - Apertura: $50,000")
    
    # 2. Venta de servicios (Ingreso)
    print("2️⃣  Creando asiento de venta de servicios...")
    asiento2 = EmpresaAsiento.objects.create(
        empresa=empresa,
        fecha=fecha_base + timedelta(days=2),
        descripcion_general="Venta de servicios de consultoría",
        estado=EstadoAsiento.CONFIRMADO,
        creado_por=usuario
    )
    EmpresaTransaccion.objects.create(
        asiento=asiento2,
        cuenta=cuentas['activo'],
        detalle_linea="Cobro servicios consultoría",
        debe=Decimal('15000.00'),
        haber=Decimal('0.00'),
        creado_por=usuario
    )
    EmpresaTransaccion.objects.create(
        asiento=asiento2,
        cuenta=cuentas['ingreso'],
        detalle_linea="Ingreso por servicios",
        debe=Decimal('0.00'),
        haber=Decimal('15000.00'),
        creado_por=usuario
    )
    asientos_creados.append(f"#{asiento2.numero_asiento} - Venta servicios: $15,000")
    
    # 3. Pago de gastos operativos
    print("3️⃣  Creando asiento de gastos operativos...")
    asiento3 = EmpresaAsiento.objects.create(
        empresa=empresa,
        fecha=fecha_base + timedelta(days=5),
        descripcion_general="Pago de gastos administrativos",
        estado=EstadoAsiento.CONFIRMADO,
        creado_por=usuario
    )
    EmpresaTransaccion.objects.create(
        asiento=asiento3,
        cuenta=cuentas['gasto'],
        detalle_linea="Gastos de oficina y suministros",
        debe=Decimal('3500.00'),
        haber=Decimal('0.00'),
        creado_por=usuario
    )
    EmpresaTransaccion.objects.create(
        asiento=asiento3,
        cuenta=cuentas['activo'],
        detalle_linea="Pago en efectivo",
        debe=Decimal('0.00'),
        haber=Decimal('3500.00'),
        creado_por=usuario
    )
    asientos_creados.append(f"#{asiento3.numero_asiento} - Gastos operativos: $3,500")
    
    # 4. Compra de insumos (Costo)
    print("4️⃣  Creando asiento de costos...")
    asiento4 = EmpresaAsiento.objects.create(
        empresa=empresa,
        fecha=fecha_base + timedelta(days=7),
        descripcion_general="Compra de materiales e insumos",
        estado=EstadoAsiento.CONFIRMADO,
        creado_por=usuario
    )
    EmpresaTransaccion.objects.create(
        asiento=asiento4,
        cuenta=cuentas['costo'],
        detalle_linea="Materiales para proyectos",
        debe=Decimal('5000.00'),
        haber=Decimal('0.00'),
        creado_por=usuario
    )
    EmpresaTransaccion.objects.create(
        asiento=asiento4,
        cuenta=cuentas['activo'],
        detalle_linea="Pago materiales",
        debe=Decimal('0.00'),
        haber=Decimal('5000.00'),
        creado_por=usuario
    )
    asientos_creados.append(f"#{asiento4.numero_asiento} - Costos materiales: $5,000")
    
    # 5. Préstamo bancario (Pasivo)
    print("5️⃣  Creando asiento de préstamo bancario...")
    asiento5 = EmpresaAsiento.objects.create(
        empresa=empresa,
        fecha=fecha_base + timedelta(days=10),
        descripcion_general="Préstamo bancario a corto plazo",
        estado=EstadoAsiento.CONFIRMADO,
        creado_por=usuario
    )
    EmpresaTransaccion.objects.create(
        asiento=asiento5,
        cuenta=cuentas['activo'],
        detalle_linea="Efectivo recibido del banco",
        debe=Decimal('20000.00'),
        haber=Decimal('0.00'),
        creado_por=usuario
    )
    EmpresaTransaccion.objects.create(
        asiento=asiento5,
        cuenta=cuentas['pasivo'],
        detalle_linea="Préstamo bancario",
        debe=Decimal('0.00'),
        haber=Decimal('20000.00'),
        creado_por=usuario
    )
    asientos_creados.append(f"#{asiento5.numero_asiento} - Préstamo bancario: $20,000")
    
    # 6. Segunda venta (más ingresos)
    print("6️⃣  Creando segundo asiento de ventas...")
    asiento6 = EmpresaAsiento.objects.create(
        empresa=empresa,
        fecha=fecha_base + timedelta(days=12),
        descripcion_general="Venta de servicios profesionales",
        estado=EstadoAsiento.CONFIRMADO,
        creado_por=usuario
    )
    EmpresaTransaccion.objects.create(
        asiento=asiento6,
        cuenta=cuentas['activo'],
        detalle_linea="Cobro servicios profesionales",
        debe=Decimal('12000.00'),
        haber=Decimal('0.00'),
        creado_por=usuario
    )
    EmpresaTransaccion.objects.create(
        asiento=asiento6,
        cuenta=cuentas['ingreso'],
        detalle_linea="Servicios profesionales",
        debe=Decimal('0.00'),
        haber=Decimal('12000.00'),
        creado_por=usuario
    )
    asientos_creados.append(f"#{asiento6.numero_asiento} - Venta servicios: $12,000")
    
    print("\n" + "=" * 70)
    print("✅ ASIENTOS CREADOS EXITOSAMENTE")
    print("=" * 70)
    for asiento in asientos_creados:
        print(f"  ✓ {asiento}")
    
    # Calcular totales
    print("\n" + "=" * 70)
    print("RESUMEN FINANCIERO")
    print("=" * 70)
    
    total_ingresos = Decimal('15000.00') + Decimal('12000.00')
    total_gastos = Decimal('3500.00')
    total_costos = Decimal('5000.00')
    utilidad = total_ingresos - total_gastos - total_costos
    
    print(f"  Ingresos totales:  ${total_ingresos:,.2f}")
    print(f"  Gastos totales:    ${total_gastos:,.2f}")
    print(f"  Costos totales:    ${total_costos:,.2f}")
    print(f"  Utilidad neta:     ${utilidad:,.2f}")
    
    # Activos y pasivos (simplificado)
    saldo_efectivo = Decimal('50000.00') + Decimal('15000.00') - Decimal('3500.00') - Decimal('5000.00') + Decimal('20000.00') + Decimal('12000.00')
    total_pasivos = Decimal('20000.00') + Decimal('1750.00')  # Préstamo + pasivos anteriores
    
    print(f"\n  Efectivo/Activos:  ${saldo_efectivo:,.2f}")
    print(f"  Pasivos totales:   ${total_pasivos:,.2f}")
    
    print("\n" + "=" * 70)
    print("📊 Ahora recarga: http://127.0.0.1:8000/contabilidad/1/ml-dashboard/")
    print("=" * 70)
    print("\nEl dashboard ahora mostrará:")
    print("  ✓ Razón Corriente (Liquidez)")
    print("  ✓ ROA (Rentabilidad sobre Activos)")
    print("  ✓ Razón de Endeudamiento")
    print("  ✓ Margen Neto")
    print("  ✓ Gráficos radar y barras con datos reales")
    print("  ✓ Insights automáticos basados en IA")

if __name__ == "__main__":
    try:
        crear_asientos_ejemplo()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
