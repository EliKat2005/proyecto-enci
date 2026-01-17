#!/usr/bin/env python
# ruff: noqa: E402
"""
Script para generar datos de prueba completos para las funcionalidades ML/AI.
Genera un plan de cuentas completo y asientos contables históricos.

Ejecutar con: python manage.py shell < scripts/generar_datos_ml_prueba.py
O: uv run python manage.py shell < scripts/generar_datos_ml_prueba.py
"""

import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from random import choice, randint

import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

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
EMPRESA_ID = 1  # Empresa de aleela
NUM_ASIENTOS = 60  # Número de asientos a generar
MESES_HISTORIA = 12  # Meses de historia


def print_step(msg):
    """Imprime un paso del proceso."""
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print("=" * 60)


def crear_plan_cuentas_completo(empresa):
    """Crea un plan de cuentas completo para la empresa."""
    print_step("📊 CREANDO PLAN DE CUENTAS COMPLETO")

    # Estructura del plan de cuentas
    cuentas = [
        # ACTIVOS (1)
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
        },
        {
            "codigo": "1.1.01",
            "descripcion": "CAJA",
            "tipo": TipoCuenta.ACTIVO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "1.1.02",
            "descripcion": "BANCOS",
            "tipo": TipoCuenta.ACTIVO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "1.1.03",
            "descripcion": "CUENTAS POR COBRAR CLIENTES",
            "tipo": TipoCuenta.ACTIVO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "1.1.04",
            "descripcion": "INVENTARIOS",
            "tipo": TipoCuenta.ACTIVO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "1.2",
            "descripcion": "ACTIVO NO CORRIENTE",
            "tipo": TipoCuenta.ACTIVO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": False,
        },
        {
            "codigo": "1.2.01",
            "descripcion": "MUEBLES Y ENSERES",
            "tipo": TipoCuenta.ACTIVO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "1.2.02",
            "descripcion": "EQUIPOS DE OFICINA",
            "tipo": TipoCuenta.ACTIVO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "1.2.03",
            "descripcion": "EQUIPOS DE CÓMPUTO",
            "tipo": TipoCuenta.ACTIVO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "1.2.04",
            "descripcion": "VEHÍCULOS",
            "tipo": TipoCuenta.ACTIVO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        # PASIVOS (2)
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
        },
        {
            "codigo": "2.1.01",
            "descripcion": "CUENTAS POR PAGAR PROVEEDORES",
            "tipo": TipoCuenta.PASIVO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "2.1.02",
            "descripcion": "IMPUESTOS POR PAGAR",
            "tipo": TipoCuenta.PASIVO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "2.1.03",
            "descripcion": "SALARIOS POR PAGAR",
            "tipo": TipoCuenta.PASIVO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "2.2",
            "descripcion": "PASIVO NO CORRIENTE",
            "tipo": TipoCuenta.PASIVO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": False,
        },
        {
            "codigo": "2.2.01",
            "descripcion": "PRÉSTAMOS BANCARIOS LARGO PLAZO",
            "tipo": TipoCuenta.PASIVO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": True,
        },
        # PATRIMONIO (3)
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
        },
        {
            "codigo": "3.1.01",
            "descripcion": "CAPITAL SOCIAL",
            "tipo": TipoCuenta.PATRIMONIO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "3.2",
            "descripcion": "RESULTADOS",
            "tipo": TipoCuenta.PATRIMONIO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": False,
        },
        {
            "codigo": "3.2.01",
            "descripcion": "UTILIDADES RETENIDAS",
            "tipo": TipoCuenta.PATRIMONIO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "3.2.02",
            "descripcion": "UTILIDAD DEL EJERCICIO",
            "tipo": TipoCuenta.PATRIMONIO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": True,
        },
        # INGRESOS (4)
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
        },
        {
            "codigo": "4.1.01",
            "descripcion": "VENTAS DE PRODUCTOS",
            "tipo": TipoCuenta.INGRESO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "4.1.02",
            "descripcion": "PRESTACIÓN DE SERVICIOS",
            "tipo": TipoCuenta.INGRESO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "4.2",
            "descripcion": "INGRESOS NO OPERACIONALES",
            "tipo": TipoCuenta.INGRESO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": False,
        },
        {
            "codigo": "4.2.01",
            "descripcion": "INTERESES GANADOS",
            "tipo": TipoCuenta.INGRESO,
            "naturaleza": NaturalezaCuenta.ACREEDORA,
            "es_auxiliar": True,
        },
        # GASTOS (5)
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
        },
        {
            "codigo": "5.1.01",
            "descripcion": "COSTO DE PRODUCTOS VENDIDOS",
            "tipo": TipoCuenta.GASTO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "5.2",
            "descripcion": "GASTOS ADMINISTRATIVOS",
            "tipo": TipoCuenta.GASTO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": False,
        },
        {
            "codigo": "5.2.01",
            "descripcion": "SUELDOS Y SALARIOS",
            "tipo": TipoCuenta.GASTO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "5.2.02",
            "descripcion": "ARRIENDO",
            "tipo": TipoCuenta.GASTO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "5.2.03",
            "descripcion": "SERVICIOS PÚBLICOS",
            "tipo": TipoCuenta.GASTO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "5.2.04",
            "descripcion": "ÚTILES Y PAPELERÍA",
            "tipo": TipoCuenta.GASTO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "5.3",
            "descripcion": "GASTOS DE VENTAS",
            "tipo": TipoCuenta.GASTO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": False,
        },
        {
            "codigo": "5.3.01",
            "descripcion": "COMISIONES DE VENTAS",
            "tipo": TipoCuenta.GASTO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "5.3.02",
            "descripcion": "PUBLICIDAD Y MARKETING",
            "tipo": TipoCuenta.GASTO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
        {
            "codigo": "5.4",
            "descripcion": "GASTOS FINANCIEROS",
            "tipo": TipoCuenta.GASTO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": False,
        },
        {
            "codigo": "5.4.01",
            "descripcion": "INTERESES PAGADOS",
            "tipo": TipoCuenta.GASTO,
            "naturaleza": NaturalezaCuenta.DEUDORA,
            "es_auxiliar": True,
        },
    ]

    cuentas_creadas = {}
    for cuenta_data in cuentas:
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
        cuentas_creadas[cuenta.codigo] = cuenta
        if created:
            print(f"  ✓ Creada: {cuenta.codigo} - {cuenta.descripcion}")
        else:
            print(f"  → Existente: {cuenta.codigo} - {cuenta.descripcion}")

    print(f"\n✅ Plan de cuentas completo: {len(cuentas_creadas)} cuentas")
    return cuentas_creadas


def crear_terceros(empresa, usuario):
    """Crea terceros de ejemplo."""
    print_step("👥 CREANDO TERCEROS")

    terceros_data = [
        {"tipo": "CLIENTE", "numero_identificacion": "1234567890", "nombre": "JUAN PÉREZ"},
        {"tipo": "CLIENTE", "numero_identificacion": "0987654321", "nombre": "MARÍA GARCÍA"},
        {
            "tipo": "PROVEEDOR",
            "numero_identificacion": "900123456-1",
            "nombre": "PROVEEDOR X S.A.S.",
        },
        {"tipo": "PROVEEDOR", "numero_identificacion": "900654321-2", "nombre": "PROVEEDOR Y LTDA"},
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
            print(f"  ✓ Creado: {tercero.nombre}")
        else:
            print(f"  → Existente: {tercero.nombre}")

    print(f"\n✅ Terceros creados: {len(terceros_creados)}")
    return terceros_creados


def generar_asientos_historicos(empresa, cuentas, terceros, usuario):
    """Genera asientos contables históricos variados."""
    print_step(f"📝 GENERANDO {NUM_ASIENTOS} ASIENTOS HISTÓRICOS")

    # Fecha inicial (hace MESES_HISTORIA meses)
    fecha_inicial = date.today() - timedelta(days=30 * MESES_HISTORIA)

    # Cuentas específicas para transacciones
    caja = cuentas.get("1.1.01")
    bancos = cuentas.get("1.1.02")
    cxc_clientes = cuentas.get("1.1.03")
    inventarios = cuentas.get("1.1.04")
    equipos_computo = cuentas.get("1.2.03")
    vehiculos = cuentas.get("1.2.04")

    cxp_proveedores = cuentas.get("2.1.01")
    impuestos = cuentas.get("2.1.02")
    salarios_pagar = cuentas.get("2.1.03")
    prestamos = cuentas.get("2.2.01")

    capital_social = cuentas.get("3.1.01")

    ventas_productos = cuentas.get("4.1.01")
    servicios = cuentas.get("4.1.02")
    intereses_ganados = cuentas.get("4.2.01")

    costo_ventas = cuentas.get("5.1.01")
    sueldos = cuentas.get("5.2.01")
    arriendo = cuentas.get("5.2.02")
    servicios_publicos = cuentas.get("5.2.03")
    papeleria = cuentas.get("5.2.04")
    comisiones = cuentas.get("5.3.01")
    publicidad = cuentas.get("5.3.02")
    intereses_pagados = cuentas.get("5.4.01")

    # Tipos de transacciones posibles
    tipos_transacciones = [
        # 1. Aporte de capital inicial
        {
            "descripcion": "Aporte inicial de capital en efectivo",
            "lineas": [
                {"cuenta": caja, "debe": 50000000, "haber": 0},
                {"cuenta": capital_social, "debe": 0, "haber": 50000000},
            ],
        },
        # 2. Venta de contado
        {
            "descripcion": "Venta de productos de contado",
            "lineas": [
                {
                    "cuenta": caja,
                    "debe": lambda: randint(500000, 5000000),
                    "haber": 0,
                    "tercero": True,
                },
                {"cuenta": ventas_productos, "debe": 0, "haber": lambda v: v},
            ],
        },
        # 3. Venta a crédito
        {
            "descripcion": "Venta de productos a crédito",
            "lineas": [
                {
                    "cuenta": cxc_clientes,
                    "debe": lambda: randint(1000000, 8000000),
                    "haber": 0,
                    "tercero": True,
                },
                {"cuenta": ventas_productos, "debe": 0, "haber": lambda v: v},
            ],
        },
        # 4. Cobro a clientes
        {
            "descripcion": "Cobro de cartera a clientes",
            "lineas": [
                {"cuenta": bancos, "debe": lambda: randint(500000, 3000000), "haber": 0},
                {"cuenta": cxc_clientes, "debe": 0, "haber": lambda v: v, "tercero": True},
            ],
        },
        # 5. Prestación de servicios
        {
            "descripcion": "Ingresos por prestación de servicios",
            "lineas": [
                {
                    "cuenta": caja,
                    "debe": lambda: randint(800000, 4000000),
                    "haber": 0,
                    "tercero": True,
                },
                {"cuenta": servicios, "debe": 0, "haber": lambda v: v},
            ],
        },
        # 6. Compra de inventario
        {
            "descripcion": "Compra de inventario a proveedores",
            "lineas": [
                {"cuenta": inventarios, "debe": lambda: randint(2000000, 10000000), "haber": 0},
                {"cuenta": cxp_proveedores, "debe": 0, "haber": lambda v: v, "tercero": True},
            ],
        },
        # 7. Pago a proveedores
        {
            "descripcion": "Pago a proveedores",
            "lineas": [
                {
                    "cuenta": cxp_proveedores,
                    "debe": lambda: randint(1000000, 5000000),
                    "haber": 0,
                    "tercero": True,
                },
                {"cuenta": bancos, "debe": 0, "haber": lambda v: v},
            ],
        },
        # 8. Pago de nómina
        {
            "descripcion": "Pago de sueldos y salarios",
            "lineas": [
                {"cuenta": sueldos, "debe": lambda: randint(3000000, 8000000), "haber": 0},
                {"cuenta": bancos, "debe": 0, "haber": lambda v: int(v * 0.92)},
                {"cuenta": salarios_pagar, "debe": 0, "haber": lambda v: int(v * 0.08)},
            ],
        },
        # 9. Pago de arriendo
        {
            "descripcion": "Pago de arriendo del local",
            "lineas": [
                {"cuenta": arriendo, "debe": lambda: randint(1500000, 3000000), "haber": 0},
                {"cuenta": bancos, "debe": 0, "haber": lambda v: v},
            ],
        },
        # 10. Servicios públicos
        {
            "descripcion": "Pago de servicios públicos",
            "lineas": [
                {"cuenta": servicios_publicos, "debe": lambda: randint(200000, 800000), "haber": 0},
                {"cuenta": caja, "debe": 0, "haber": lambda v: v},
            ],
        },
        # 11. Compra de papelería
        {
            "descripcion": "Compra de útiles y papelería",
            "lineas": [
                {"cuenta": papeleria, "debe": lambda: randint(100000, 500000), "haber": 0},
                {"cuenta": caja, "debe": 0, "haber": lambda v: v},
            ],
        },
        # 12. Gastos de publicidad
        {
            "descripcion": "Inversión en publicidad y marketing",
            "lineas": [
                {"cuenta": publicidad, "debe": lambda: randint(500000, 2000000), "haber": 0},
                {"cuenta": bancos, "debe": 0, "haber": lambda v: v},
            ],
        },
        # 13. Compra de equipos
        {
            "descripcion": "Compra de equipos de cómputo",
            "lineas": [
                {"cuenta": equipos_computo, "debe": lambda: randint(2000000, 5000000), "haber": 0},
                {"cuenta": bancos, "debe": 0, "haber": lambda v: v},
            ],
        },
        # 14. Pago de intereses
        {
            "descripcion": "Pago de intereses sobre préstamos",
            "lineas": [
                {"cuenta": intereses_pagados, "debe": lambda: randint(300000, 1000000), "haber": 0},
                {"cuenta": bancos, "debe": 0, "haber": lambda v: v},
            ],
        },
        # 15. Comisiones de ventas
        {
            "descripcion": "Pago de comisiones a vendedores",
            "lineas": [
                {"cuenta": comisiones, "debe": lambda: randint(400000, 1500000), "haber": 0},
                {"cuenta": caja, "debe": 0, "haber": lambda v: v, "tercero": True},
            ],
        },
    ]

    asientos_creados = 0
    errores = 0

    for i in range(NUM_ASIENTOS):
        # Fecha aleatoria dentro del rango
        dias_desde_inicio = randint(0, 30 * MESES_HISTORIA)
        fecha_asiento = fecha_inicial + timedelta(days=dias_desde_inicio)

        # Seleccionar tipo de transacción aleatorio
        tipo_trans = choice(tipos_transacciones)

        try:
            # Crear asiento
            numero_asiento = EmpresaAsiento.objects.filter(empresa=empresa).count() + 1
            asiento = EmpresaAsiento.objects.create(
                empresa=empresa,
                numero_asiento=numero_asiento,
                fecha=fecha_asiento,
                descripcion=tipo_trans["descripcion"],
                creado_por=usuario,
                estado=EstadoAsiento.CONFIRMADO,
            )

            # Generar montos dinámicos
            valor_referencia = None

            # Crear transacciones
            for linea in tipo_trans["lineas"]:
                # Calcular montos
                if callable(linea["debe"]):
                    if valor_referencia is None:
                        valor_referencia = linea["debe"]()
                    debe = Decimal(
                        str(
                            linea["debe"](valor_referencia)
                            if linea["debe"].__code__.co_argcount > 0
                            else linea["debe"]()
                        )
                    )
                else:
                    debe = Decimal(str(linea["debe"]))

                if callable(linea["haber"]):
                    haber = Decimal(str(linea["haber"](valor_referencia)))
                else:
                    haber = Decimal(str(linea["haber"]))

                # Seleccionar tercero si es necesario
                tercero = None
                if linea.get("tercero") and terceros:
                    tercero = choice(terceros)

                # Crear transacción
                EmpresaTransaccion.objects.create(
                    asiento=asiento,
                    cuenta=linea["cuenta"],
                    detalle=tipo_trans["descripcion"],
                    debe=debe,
                    haber=haber,
                    tercero=tercero,
                )

            asientos_creados += 1
            if asientos_creados % 10 == 0:
                print(f"  ✓ {asientos_creados} asientos creados...")

        except Exception as e:
            errores += 1
            print(f"  ✗ Error en asiento {i+1}: {e}")

    print(f"\n✅ Asientos creados: {asientos_creados}")
    if errores > 0:
        print(f"⚠️ Errores: {errores}")

    return asientos_creados


def main():
    """Función principal."""
    print("\n" + "=" * 60)
    print("  🚀 GENERADOR DE DATOS ML/AI PARA CONTABILIDAD")
    print("=" * 60)

    try:
        # Obtener empresa
        print_step("🔍 VERIFICANDO EMPRESA")
        empresa = Empresa.objects.get(id=EMPRESA_ID)
        print(f"  ✓ Empresa encontrada: {empresa.nombre} (ID: {empresa.id})")
        print(f"  ✓ Propietario: {empresa.owner.username}")

        # Obtener usuario
        usuario = empresa.owner

        # Crear plan de cuentas
        cuentas = crear_plan_cuentas_completo(empresa)

        # Crear terceros
        terceros = crear_terceros(empresa, usuario)

        # Generar asientos históricos
        asientos_creados = generar_asientos_historicos(empresa, cuentas, terceros, usuario)

        # Resumen final
        print_step("📊 RESUMEN FINAL")
        print(f"  ✓ Empresa: {empresa.nombre}")
        print(f"  ✓ Cuentas en plan: {len(cuentas)}")
        print(f"  ✓ Terceros: {len(terceros)}")
        print(f"  ✓ Asientos generados: {asientos_creados}")

        total_transacciones = EmpresaTransaccion.objects.filter(asiento__empresa=empresa).count()
        print(f"  ✓ Transacciones totales: {total_transacciones}")

        print("\n" + "=" * 60)
        print("  ✅ DATOS GENERADOS EXITOSAMENTE")
        print("=" * 60)
        print("\n  Ahora puedes usar las funcionalidades ML/AI:")
        print("  • Dashboard: http://127.0.0.1:8000/contabilidad/1/ml-dashboard/")
        print("  • Analytics: http://127.0.0.1:8000/contabilidad/1/ml-analytics/")
        print("  • Predicciones: http://127.0.0.1:8000/contabilidad/1/ml-predictions/")
        print("  • Anomalías: http://127.0.0.1:8000/contabilidad/1/ml-anomalies/")
        print("  • Búsqueda: http://127.0.0.1:8000/contabilidad/1/ml-embeddings/")
        print()

    except Empresa.DoesNotExist:
        print(f"\n❌ Error: No existe la empresa con ID {EMPRESA_ID}")
        print("   Verifica el ID de la empresa de aleela")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
