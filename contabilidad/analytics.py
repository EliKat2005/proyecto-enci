"""
Servicio de Análisis Financiero y Business Intelligence.
Aprovecha capacidades avanzadas de MariaDB: Window Functions, CTEs, Aggregations, JSON.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db import connection

from contabilidad.models import (
    Empresa,
    EmpresaMetrica,
    EmpresaPlanCuenta,
    EmpresaTransaccion,
    TipoCuenta,
)


class AnalyticsService:
    """Servicio principal de análisis financiero con SQL avanzado."""

    def __init__(self, empresa: Empresa):
        self.empresa = empresa

    def calcular_metricas_periodo(self, fecha_inicio: date, fecha_fin: date) -> EmpresaMetrica:
        """
        Calcula todas las métricas financieras para un período usando queries SQL optimizadas.
        Aprovecha Window Functions y CTEs de MariaDB para cálculos eficientes.
        """

        # Obtener saldos acumulados por tipo de cuenta (desde inicio hasta fecha_fin)
        # Para Balance General: necesitamos saldos acumulados
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH saldos_cuentas AS (
                    SELECT
                        c.tipo,
                        c.naturaleza,
                        SUM(CASE
                            WHEN c.naturaleza = 'Deudora' THEN t.debe - t.haber
                            ELSE t.haber - t.debe
                        END) as saldo
                    FROM contabilidad_empresa_transaccion t
                    INNER JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                    INNER JOIN contabilidad_empresa_plandecuentas c ON t.cuenta_id = c.id
                    WHERE a.empresa_id = %s
                        AND a.estado = 'Confirmado'
                        AND a.anulado = FALSE
                        AND a.fecha <= %s
                    GROUP BY c.tipo, c.naturaleza
                )
                SELECT
                    tipo,
                    SUM(saldo) as total_saldo
                FROM saldos_cuentas
                GROUP BY tipo
            """,
                [self.empresa.id, fecha_fin],
            )

            saldos = {row[0]: Decimal(str(row[1] or 0)) for row in cursor.fetchall()}

        # Extraer valores por tipo de cuenta
        activos = saldos.get(TipoCuenta.ACTIVO, Decimal("0"))
        pasivos = saldos.get(TipoCuenta.PASIVO, Decimal("0"))
        patrimonio = saldos.get(TipoCuenta.PATRIMONIO, Decimal("0"))
        
        # Para Estado de Resultados: ingresos, gastos y costos del período
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.tipo,
                    SUM(CASE
                        WHEN c.naturaleza = 'Deudora' THEN t.debe - t.haber
                        ELSE t.haber - t.debe
                    END) as saldo
                FROM contabilidad_empresa_transaccion t
                INNER JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                INNER JOIN contabilidad_empresa_plandecuentas c ON t.cuenta_id = c.id
                WHERE a.empresa_id = %s
                    AND a.estado = 'Confirmado'
                    AND a.anulado = FALSE
                    AND a.fecha BETWEEN %s AND %s
                    AND c.tipo IN ('Ingreso', 'Gasto', 'Costo')
                GROUP BY c.tipo
            """,
                [self.empresa.id, fecha_inicio, fecha_fin],
            )

            saldos_resultados = {row[0]: Decimal(str(row[1] or 0)) for row in cursor.fetchall()}
        
        ingresos = abs(saldos_resultados.get(TipoCuenta.INGRESO, Decimal("0")))
        gastos = abs(saldos_resultados.get(TipoCuenta.GASTO, Decimal("0")))
        costos = abs(saldos_resultados.get(TipoCuenta.COSTO, Decimal("0")))

        # Calcular activo y pasivo corriente (simplificado: primeros 2 dígitos del código)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.tipo,
                    SUM(CASE
                        WHEN c.naturaleza = 'Deudora' THEN t.debe - t.haber
                        ELSE t.haber - t.debe
                    END) as saldo
                FROM contabilidad_empresa_transaccion t
                INNER JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                INNER JOIN contabilidad_empresa_plandecuentas c ON t.cuenta_id = c.id
                WHERE a.empresa_id = %s
                    AND a.estado = 'Confirmado'
                    AND a.anulado = FALSE
                    AND a.fecha <= %s
                    AND (
                        (c.tipo = 'Activo' AND LEFT(c.codigo, 2) IN ('11', '12', '13'))
                        OR (c.tipo = 'Pasivo' AND LEFT(c.codigo, 2) IN ('21', '22', '23'))
                    )
                GROUP BY c.tipo
            """,
                [self.empresa.id, fecha_fin],
            )

            corrientes = {row[0]: Decimal(str(row[1] or 0)) for row in cursor.fetchall()}

        activo_corriente = corrientes.get(TipoCuenta.ACTIVO, Decimal("0"))
        pasivo_corriente = corrientes.get(TipoCuenta.PASIVO, Decimal("0"))

        # Contar transacciones y cuentas activas
        num_transacciones = EmpresaTransaccion.objects.filter(
            asiento__empresa=self.empresa,
            asiento__fecha__range=(fecha_inicio, fecha_fin),
            asiento__estado="Confirmado",
            asiento__anulado=False,
            asiento__anula_a__isnull=True,
        ).count()

        num_cuentas_activas = (
            EmpresaPlanCuenta.objects.filter(
                empresa=self.empresa,
                empresatransaccion__asiento__fecha__range=(fecha_inicio, fecha_fin),
                empresatransaccion__asiento__estado="Confirmado",
                empresatransaccion__asiento__anulado=False,
                empresatransaccion__asiento__anula_a__isnull=True,
            )
            .distinct()
            .count()
        )

        # Calcular ratios financieros
        utilidad_neta = ingresos - gastos - costos

        razon_corriente = (activo_corriente / pasivo_corriente) if pasivo_corriente > 0 else None
        prueba_acida = razon_corriente  # Simplificado
        margen_neto = (utilidad_neta / ingresos * 100) if ingresos > 0 else None
        roe = (utilidad_neta / patrimonio * 100) if patrimonio > 0 else None
        roa = (utilidad_neta / activos * 100) if activos > 0 else None
        razon_endeudamiento = (pasivos / activos * 100) if activos > 0 else None

        # Crear y guardar métrica
        metrica = EmpresaMetrica.objects.create(
            empresa=self.empresa,
            periodo_inicio=fecha_inicio,
            periodo_fin=fecha_fin,
            activo_corriente=activo_corriente,
            pasivo_corriente=pasivo_corriente,
            razon_corriente=razon_corriente,
            prueba_acida=prueba_acida,
            ingresos_totales=ingresos,
            gastos_totales=gastos + costos,
            utilidad_neta=utilidad_neta,
            margen_neto=margen_neto,
            roe=roe,
            roa=roa,
            total_activos=activos,
            total_pasivos=pasivos,
            total_patrimonio=patrimonio,
            razon_endeudamiento=razon_endeudamiento,
            num_transacciones=num_transacciones,
            num_cuentas_activas=num_cuentas_activas,
        )

        return metrica

    def get_tendencia_ingresos_gastos(self, meses: int = 12) -> dict:
        """
        Obtiene la tendencia de ingresos y gastos usando Window Functions.
        Calcula medias móviles y tasas de crecimiento.
        """
        fecha_fin = date.today()
        fecha_inicio = fecha_fin - timedelta(days=meses * 30)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH movimientos_mensuales AS (
                    SELECT
                        DATE_FORMAT(a.fecha, '%%Y-%%m') as periodo,
                        c.tipo,
                        SUM(CASE
                            WHEN c.naturaleza = 'Deudora' THEN t.debe - t.haber
                            ELSE t.haber - t.debe
                        END) as monto
                    FROM contabilidad_empresa_transaccion t
                    INNER JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                    INNER JOIN contabilidad_empresa_plandecuentas c ON t.cuenta_id = c.id
                    WHERE a.empresa_id = %s
                        AND a.estado = 'Confirmado'
                        AND a.anulado = FALSE
                        AND a.fecha BETWEEN %s AND %s
                        AND c.tipo IN ('Ingreso', 'Gasto', 'Costo')
                    GROUP BY DATE_FORMAT(a.fecha, '%%Y-%%m'), c.tipo
                ),
                agregados AS (
                    SELECT
                        periodo,
                        SUM(CASE WHEN tipo = 'Ingreso' THEN monto ELSE 0 END) as ingresos,
                        SUM(CASE WHEN tipo IN ('Gasto', 'Costo') THEN ABS(monto) ELSE 0 END) as gastos
                    FROM movimientos_mensuales
                    GROUP BY periodo
                )
                SELECT
                    periodo,
                    ingresos,
                    gastos,
                    ingresos - gastos as utilidad,
                    AVG(ingresos) OVER (ORDER BY periodo ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as media_movil_ingresos,
                    AVG(gastos) OVER (ORDER BY periodo ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as media_movil_gastos,
                    LAG(ingresos, 1) OVER (ORDER BY periodo) as ingresos_anterior,
                    LAG(gastos, 1) OVER (ORDER BY periodo) as gastos_anterior
                FROM agregados
                ORDER BY periodo
            """,
                [self.empresa.id, fecha_inicio, fecha_fin],
            )

            rows = cursor.fetchall()

            resultado = {
                "periodos": [],
                "ingresos": [],
                "gastos": [],
                "utilidad": [],
                "media_movil_ingresos": [],
                "media_movil_gastos": [],
                "tasa_crecimiento_ingresos": [],
                "tasa_crecimiento_gastos": [],
            }

            for row in rows:
                periodo, ingresos, gastos, utilidad, mm_ing, mm_gas, ing_ant, gas_ant = row

                resultado["periodos"].append(periodo)
                resultado["ingresos"].append(float(ingresos or 0))
                resultado["gastos"].append(float(gastos or 0))
                resultado["utilidad"].append(float(utilidad or 0))
                resultado["media_movil_ingresos"].append(float(mm_ing or 0))
                resultado["media_movil_gastos"].append(float(mm_gas or 0))

                # Calcular tasas de crecimiento
                tasa_ing = ((ingresos - ing_ant) / ing_ant * 100) if ing_ant and ing_ant > 0 else 0
                tasa_gas = ((gastos - gas_ant) / gas_ant * 100) if gas_ant and gas_ant > 0 else 0

                resultado["tasa_crecimiento_ingresos"].append(float(tasa_ing))
                resultado["tasa_crecimiento_gastos"].append(float(tasa_gas))

        return resultado

    def get_top_cuentas_movimiento(self, limit: int = 10) -> list[dict]:
        """
        Obtiene las cuentas con mayor movimiento usando agregaciones y ranking.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    c.codigo,
                    c.descripcion,
                    c.tipo,
                    COUNT(t.id) as num_transacciones,
                    SUM(t.debe) as total_debe,
                    SUM(t.haber) as total_haber,
                    SUM(t.debe + t.haber) as movimiento_total,
                    RANK() OVER (ORDER BY SUM(t.debe + t.haber) DESC) as ranking
                FROM contabilidad_empresa_plandecuentas c
                INNER JOIN contabilidad_empresa_transaccion t ON c.id = t.cuenta_id
                INNER JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                WHERE a.empresa_id = %s
                    AND a.estado = 'Confirmado'
                    AND a.anulado = FALSE
                GROUP BY c.id, c.codigo, c.descripcion, c.tipo
                ORDER BY movimiento_total DESC
                LIMIT %s
            """,
                [self.empresa.id, limit],
            )

            columnas = [col[0] for col in cursor.description]
            resultados = [dict(zip(columnas, row, strict=False)) for row in cursor.fetchall()]

            # Convertir Decimals a float para JSON
            for resultado in resultados:
                for key in ["total_debe", "total_haber", "movimiento_total"]:
                    if resultado[key]:
                        resultado[key] = float(resultado[key])

            return resultados

    def get_composicion_patrimonial(self) -> dict:
        """
        Calcula la composición del patrimonio y estructura financiera.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH saldos_tipo AS (
                    SELECT
                        c.tipo,
                        SUM(CASE
                            WHEN c.naturaleza = 'Deudora' THEN t.debe - t.haber
                            ELSE t.haber - t.debe
                        END) as saldo
                    FROM contabilidad_empresa_transaccion t
                    INNER JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                    INNER JOIN contabilidad_empresa_plandecuentas c ON t.cuenta_id = c.id
                    WHERE a.empresa_id = %s
                        AND a.estado = 'Confirmado'
                        AND a.anulado = FALSE
                    GROUP BY c.tipo
                )
                SELECT
                    tipo,
                    saldo,
                    saldo / SUM(ABS(saldo)) OVER () * 100 as porcentaje
                FROM saldos_tipo
            """,
                [self.empresa.id],
            )

            resultado = {
                "composicion": [],
                "total_activos": 0,
                "total_pasivos": 0,
                "total_patrimonio": 0,
            }

            for row in cursor.fetchall():
                tipo, saldo, porcentaje = row
                saldo = float(saldo or 0)
                porcentaje = float(porcentaje or 0)

                resultado["composicion"].append(
                    {"tipo": tipo, "saldo": saldo, "porcentaje": porcentaje}
                )

                if tipo == "Activo":
                    resultado["total_activos"] = saldo
                elif tipo == "Pasivo":
                    resultado["total_pasivos"] = abs(saldo)
                elif tipo == "Patrimonio":
                    resultado["total_patrimonio"] = saldo

            return resultado

    def get_analisis_jerarquico_cuentas(self) -> list[dict]:
        """
        Análisis jerárquico del plan de cuentas usando CTEs recursivas.
        Muestra agregaciones por nivel de jerarquía.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH RECURSIVE jerarquia AS (
                    -- Nodo raíz: cuentas sin padre
                    SELECT
                        c.id,
                        c.codigo,
                        c.descripcion,
                        c.tipo,
                        c.padre_id,
                        1 as nivel,
                        CAST(c.codigo AS CHAR(500)) as ruta
                    FROM contabilidad_empresa_plandecuentas c
                    WHERE c.empresa_id = %s AND c.padre_id IS NULL

                    UNION ALL

                    -- Nodos hijos recursivos
                    SELECT
                        c.id,
                        c.codigo,
                        c.descripcion,
                        c.tipo,
                        c.padre_id,
                        j.nivel + 1,
                        CONCAT(j.ruta, ' > ', c.codigo)
                    FROM contabilidad_empresa_plandecuentas c
                    INNER JOIN jerarquia j ON c.padre_id = j.id
                    WHERE c.empresa_id = %s
                )
                SELECT
                    j.nivel,
                    j.ruta,
                    j.codigo,
                    j.descripcion,
                    j.tipo,
                    COALESCE(SUM(t.debe), 0) as total_debe,
                    COALESCE(SUM(t.haber), 0) as total_haber,
                    COUNT(DISTINCT t.id) as num_transacciones
                FROM jerarquia j
                LEFT JOIN contabilidad_empresa_transaccion t ON j.id = t.cuenta_id
                LEFT JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                    AND a.estado = 'Confirmado'
                    AND a.anulado = FALSE
                GROUP BY j.id, j.nivel, j.ruta, j.codigo, j.descripcion, j.tipo
                ORDER BY j.ruta
            """,
                [self.empresa.id, self.empresa.id],
            )

            columnas = [col[0] for col in cursor.description]
            resultados = [dict(zip(columnas, row, strict=False)) for row in cursor.fetchall()]

            for resultado in resultados:
                for key in ["total_debe", "total_haber"]:
                    if resultado[key]:
                        resultado[key] = float(resultado[key])

            return resultados
