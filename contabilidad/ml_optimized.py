"""
Servicios ML optimizados con capacidades avanzadas de MariaDB 11.8+.
Aprovecha: Window Functions, Percentiles, CTEs, FULLTEXT Search, Vector Operations.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db import connection

from .models import Empresa, EmpresaMetricasCache, TipoCuenta

logger = logging.getLogger(__name__)


class OptimizedAnalyticsService:
    """Servicio de análisis optimizado con SQL avanzado de MariaDB."""

    def __init__(self, empresa: Empresa):
        self.empresa = empresa

    def get_dashboard_metrics_cached(self, periodo: date = None) -> dict[str, Any]:
        """
        Obtiene métricas del dashboard con sistema de cache automático.
        Usa triggers de MariaDB para invalidación inteligente.

        Args:
            periodo: Período a consultar (por defecto: mes actual)

        Returns:
            dict con métricas financieras
        """
        if periodo is None:
            periodo = date.today().replace(day=1)

        # Intentar obtener del cache
        cache = EmpresaMetricasCache.objects.filter(empresa=self.empresa, periodo=periodo).first()

        if cache:
            logger.info(f"Cache HIT para empresa {self.empresa.id}, período {periodo}")
            return cache.metricas_json

        # Cache MISS: calcular y guardar
        logger.info(f"Cache MISS para empresa {self.empresa.id}, período {periodo}")
        metricas = self._calcular_metricas_periodo(periodo)

        # Guardar en cache
        EmpresaMetricasCache.objects.update_or_create(
            empresa=self.empresa,
            periodo=periodo,
            defaults={"metricas_json": metricas},
        )

        return metricas

    def _calcular_metricas_periodo(self, periodo: date) -> dict[str, Any]:
        """Calcula métricas usando CTE y agregaciones optimizadas."""
        fecha_inicio = periodo
        fecha_fin = (periodo.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH saldos_cuentas AS (
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
                    GROUP BY c.tipo
                )
                SELECT
                    tipo,
                    ABS(saldo) as saldo_abs
                FROM saldos_cuentas
                """,
                [self.empresa.id, fecha_inicio, fecha_fin],
            )

            saldos = {row[0]: float(row[1]) for row in cursor.fetchall()}

        activos = saldos.get("Activo", 0.0)
        pasivos = saldos.get("Pasivo", 0.0)
        patrimonio = saldos.get("Patrimonio", 0.0)
        ingresos = saldos.get("Ingreso", 0.0)
        gastos = saldos.get("Gasto", 0.0)
        costos = saldos.get("Costo", 0.0)

        # Verificar si hay datos
        if activos == 0 and pasivos == 0 and ingresos == 0:
            return {
                "has_data": False,
                "liquidez": 0.0,
                "roa": 0.0,
                "endeudamiento": 0.0,
                "margen_neto": 0.0,
                "activos": 0.0,
                "pasivos": 0.0,
                "patrimonio": 0.0,
                "ingresos": 0.0,
                "gastos": 0.0,
                "costos": 0.0,
                "utilidad_neta": 0.0,
            }

        # Calcular métricas
        liquidez = activos / pasivos if pasivos > 0 else 0.0
        utilidad_neta = ingresos - costos - gastos
        roa = (utilidad_neta / activos) * 100 if activos > 0 else 0.0
        endeudamiento = (pasivos / activos) * 100 if activos > 0 else 0.0
        margen_neto = (utilidad_neta / ingresos) * 100 if ingresos > 0 else 0.0

        return {
            "has_data": True,
            "liquidez": round(liquidez, 2),
            "roa": round(roa, 2),
            "endeudamiento": round(endeudamiento, 2),
            "margen_neto": round(margen_neto, 2),
            "activos": activos,
            "pasivos": pasivos,
            "patrimonio": patrimonio,
            "ingresos": ingresos,
            "gastos": gastos,
            "costos": costos,
            "utilidad_neta": utilidad_neta,
            "periodo": periodo.strftime("%Y-%m"),
        }

    def detect_anomalies_with_percentiles(
        self, dias: int = 90, percentil_bajo: float = 0.01, percentil_alto: float = 0.99
    ) -> list[dict[str, Any]]:
        """
        Detecta anomalías usando percentiles (más robusto que Z-score).
        Utiliza PERCENT_RANK() de MariaDB para identificar valores atípicos.

        Args:
            dias: Días históricos a analizar
            percentil_bajo: Percentil inferior (default: 1%)
            percentil_alto: Percentil superior (default: 99%)

        Returns:
            Lista de anomalías detectadas
        """
        fecha_inicio = date.today() - timedelta(days=dias)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH stats_por_cuenta AS (
                    SELECT
                        t.id as transaccion_id,
                        t.cuenta_id,
                        c.codigo,
                        c.descripcion,
                        c.tipo,
                        a.id as asiento_id,
                        a.numero_asiento,
                        a.fecha,
                        t.debe + t.haber as monto,
                        -- Percentil usando PERCENT_RANK()
                        PERCENT_RANK() OVER (
                            PARTITION BY t.cuenta_id
                            ORDER BY t.debe + t.haber
                        ) as percentil,
                        -- Mediana de la cuenta
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY t.debe + t.haber)
                            OVER (PARTITION BY t.cuenta_id) as mediana,
                        -- IQR para identificar outliers
                        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY t.debe + t.haber)
                            OVER (PARTITION BY t.cuenta_id) as q3,
                        PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY t.debe + t.haber)
                            OVER (PARTITION BY t.cuenta_id) as q1
                    FROM contabilidad_empresa_transaccion t
                    JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                    JOIN contabilidad_empresa_plandecuentas c ON t.cuenta_id = c.id
                    WHERE a.empresa_id = %s
                      AND a.estado = 'Confirmado'
                      AND a.anulado = FALSE
                      AND a.fecha >= %s
                )
                SELECT
                    asiento_id,
                    numero_asiento,
                    fecha,
                    codigo,
                    descripcion,
                    tipo,
                    monto,
                    percentil,
                    mediana,
                    (q3 - q1) as iqr,
                    CASE
                        WHEN percentil >= %s THEN 'Anomalía Alta'
                        WHEN percentil <= %s THEN 'Anomalía Baja'
                        ELSE 'Normal'
                    END as tipo_anomalia,
                    CASE
                        WHEN percentil >= 0.995 OR percentil <= 0.005 THEN 'CRITICA'
                        WHEN percentil >= %s OR percentil <= %s THEN 'ALTA'
                        ELSE 'MEDIA'
                    END as severidad
                FROM stats_por_cuenta
                WHERE percentil >= %s OR percentil <= %s
                ORDER BY
                    CASE
                        WHEN percentil >= 0.995 OR percentil <= 0.005 THEN 1
                        WHEN percentil >= 0.99 OR percentil <= 0.01 THEN 2
                        ELSE 3
                    END,
                    ABS(0.5 - percentil) DESC
                LIMIT 50
                """,
                [
                    self.empresa.id,
                    fecha_inicio,
                    percentil_alto,
                    percentil_bajo,
                    percentil_alto,
                    percentil_bajo,
                    percentil_alto,
                    percentil_bajo,
                ],
            )

            columnas = [col[0] for col in cursor.description]
            anomalias = [dict(zip(columnas, row, strict=False)) for row in cursor.fetchall()]

            # Convertir Decimals y dates a tipos serializables
            for anomalia in anomalias:
                for key, value in anomalia.items():
                    if isinstance(value, Decimal):
                        anomalia[key] = float(value)
                    elif isinstance(value, date):
                        anomalia[key] = value.strftime("%Y-%m-%d")

            return anomalias

    def analyze_temporal_patterns(self, cuenta_id: int, dias: int = 90) -> dict[str, Any]:
        """
        Analiza patrones temporales de una cuenta usando Window Functions avanzadas.
        Calcula: media móvil, volatilidad, Z-score, tendencias.

        Args:
            cuenta_id: ID de la cuenta a analizar
            dias: Días históricos

        Returns:
            dict con análisis temporal completo
        """
        fecha_inicio = date.today() - timedelta(days=dias)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH transacciones_diarias AS (
                    SELECT
                        DATE(a.fecha) as fecha,
                        SUM(t.debe + t.haber) as monto_diario
                    FROM contabilidad_empresa_transaccion t
                    JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                    WHERE a.empresa_id = %s
                      AND t.cuenta_id = %s
                      AND a.estado = 'Confirmado'
                      AND a.anulado = FALSE
                      AND a.fecha >= %s
                    GROUP BY DATE(a.fecha)
                ),
                stats_rolling AS (
                    SELECT
                        fecha,
                        monto_diario,
                        -- Media móvil 7 días
                        AVG(monto_diario) OVER (
                            ORDER BY fecha
                            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                        ) as media_movil_7d,
                        -- Media móvil 30 días
                        AVG(monto_diario) OVER (
                            ORDER BY fecha
                            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                        ) as media_movil_30d,
                        -- Desviación estándar móvil
                        STDDEV_POP(monto_diario) OVER (
                            ORDER BY fecha
                            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                        ) as volatilidad_30d,
                        -- Z-score para detección de anomalías
                        (monto_diario - AVG(monto_diario) OVER (
                            ORDER BY fecha
                            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                        )) / NULLIF(STDDEV_POP(monto_diario) OVER (
                            ORDER BY fecha
                            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                        ), 0) as z_score,
                        -- Tendencia (comparación con media móvil)
                        CASE
                            WHEN monto_diario > AVG(monto_diario) OVER (
                                ORDER BY fecha
                                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                            ) * 1.2 THEN 'Creciente'
                            WHEN monto_diario < AVG(monto_diario) OVER (
                                ORDER BY fecha
                                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                            ) * 0.8 THEN 'Decreciente'
                            ELSE 'Estable'
                        END as tendencia
                    FROM transacciones_diarias
                )
                SELECT * FROM stats_rolling
                ORDER BY fecha DESC
                """,
                [self.empresa.id, cuenta_id, fecha_inicio],
            )

            columnas = [col[0] for col in cursor.description]
            resultados = [dict(zip(columnas, row, strict=False)) for row in cursor.fetchall()]

            # Convertir tipos
            for resultado in resultados:
                for key, value in resultado.items():
                    if isinstance(value, Decimal):
                        resultado[key] = float(value)
                    elif isinstance(value, date):
                        resultado[key] = value.strftime("%Y-%m-%d")

            # Calcular estadísticas generales
            if resultados:
                z_scores = [r.get("z_score", 0) or 0 for r in resultados]
                anomalias = len([z for z in z_scores if abs(z) > 3])

                return {
                    "datos": resultados,
                    "resumen": {
                        "total_dias": len(resultados),
                        "anomalias_detectadas": anomalias,
                        "porcentaje_anomalias": round((anomalias / len(resultados)) * 100, 2),
                        "volatilidad_promedio": round(
                            sum(r.get("volatilidad_30d", 0) or 0 for r in resultados)
                            / len(resultados),
                            2,
                        ),
                    },
                }

            return {"datos": [], "resumen": {}}

    def semantic_search_fulltext(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Búsqueda semántica optimizada con FULLTEXT INDEX de MariaDB.
        10-50x más rápida que LIKE '%query%'.

        Args:
            query: Texto de búsqueda
            limit: Número máximo de resultados

        Returns:
            Lista de cuentas con relevancia calculada por MariaDB
        """
        with connection.cursor() as cursor:
            # Búsqueda FULLTEXT con relevancia nativa
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.codigo,
                    c.descripcion,
                    c.tipo,
                    c.naturaleza,
                    c.es_auxiliar,
                    -- Score de relevancia calculado por MariaDB
                    MATCH(c.descripcion, c.codigo) AGAINST (%s IN NATURAL LANGUAGE MODE) as relevancia
                FROM contabilidad_empresa_plandecuentas c
                WHERE c.empresa_id = %s
                  AND c.activa = TRUE
                  AND MATCH(c.descripcion, c.codigo) AGAINST (%s IN NATURAL LANGUAGE MODE)
                ORDER BY relevancia DESC
                LIMIT %s
                """,
                [query, self.empresa.id, query, limit],
            )

            columnas = [col[0] for col in cursor.description]
            resultados = [dict(zip(columnas, row, strict=False)) for row in cursor.fetchall()]

            # Convertir Decimals
            for resultado in resultados:
                if resultado.get("relevancia"):
                    resultado["relevancia"] = float(resultado["relevancia"])
                # Convertir bool a python bool
                resultado["es_auxiliar"] = bool(resultado["es_auxiliar"])

            return resultados

    def cluster_cuentas_por_patron(self) -> list[dict[str, Any]]:
        """
        Segmenta cuentas en clusters según patrones de uso.
        Usa normalización Min-Max y clasificación heurística.

        Returns:
            Lista de cuentas con cluster asignado
        """
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH metricas_cuenta AS (
                    SELECT
                        c.id,
                        c.codigo,
                        c.descripcion,
                        c.tipo,
                        COUNT(DISTINCT a.id) as num_transacciones,
                        AVG(t.debe + t.haber) as promedio_monto,
                        STDDEV(t.debe + t.haber) as volatilidad,
                        COUNT(DISTINCT DATE_FORMAT(a.fecha, '%%Y-%%m')) as meses_activos
                    FROM contabilidad_empresa_plandecuentas c
                    LEFT JOIN contabilidad_empresa_transaccion t ON c.id = t.cuenta_id
                    LEFT JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                    WHERE c.empresa_id = %s
                      AND c.activa = TRUE
                      AND a.estado = 'Confirmado'
                      AND a.anulado = FALSE
                    GROUP BY c.id
                    HAVING num_transacciones > 0
                ),
                normalizadas AS (
                    SELECT
                        *,
                        -- Normalización Min-Max
                        (num_transacciones - MIN(num_transacciones) OVER ()) /
                            NULLIF(MAX(num_transacciones) OVER () - MIN(num_transacciones) OVER (), 0) as trans_norm,
                        (promedio_monto - MIN(promedio_monto) OVER ()) /
                            NULLIF(MAX(promedio_monto) OVER () - MIN(promedio_monto) OVER (), 0) as monto_norm,
                        (volatilidad - MIN(volatilidad) OVER ()) /
                            NULLIF(MAX(volatilidad) OVER () - MIN(volatilidad) OVER (), 0) as vol_norm
                    FROM metricas_cuenta
                )
                SELECT
                    id,
                    codigo,
                    descripcion,
                    tipo,
                    num_transacciones,
                    promedio_monto,
                    volatilidad,
                    meses_activos,
                    CASE
                        WHEN trans_norm > 0.7 AND monto_norm > 0.7 THEN 'Alta Actividad - Alto Valor'
                        WHEN trans_norm > 0.7 AND monto_norm <= 0.7 THEN 'Alta Actividad - Bajo Valor'
                        WHEN trans_norm <= 0.7 AND monto_norm > 0.7 THEN 'Baja Actividad - Alto Valor'
                        ELSE 'Baja Actividad - Bajo Valor'
                    END as cluster,
                    trans_norm,
                    monto_norm,
                    vol_norm
                FROM normalizadas
                ORDER BY cluster, num_transacciones DESC
                """,
                [self.empresa.id],
            )

            columnas = [col[0] for col in cursor.description]
            resultados = [dict(zip(columnas, row, strict=False)) for row in cursor.fetchall()]

            # Convertir Decimals
            for resultado in resultados:
                for key in [
                    "promedio_monto",
                    "volatilidad",
                    "trans_norm",
                    "monto_norm",
                    "vol_norm",
                ]:
                    if resultado.get(key):
                        resultado[key] = float(resultado[key])

            return resultados

    def predict_with_linear_regression_sql(
        self, tipo_cuenta: str, dias_historicos: int = 90, dias_futuros: int = 30
    ) -> dict[str, Any]:
        """
        Predicción ligera usando regresión lineal calculada en SQL puro.
        Alternativa rápida a Prophet para predicciones simples.

        Args:
            tipo_cuenta: INGRESO, GASTO, COSTO
            dias_historicos: Días de histórico
            dias_futuros: Días a predecir

        Returns:
            dict con predicción y coeficientes
        """
        fecha_inicio = date.today() - timedelta(days=dias_historicos)

        # Validar tipo_cuenta
        try:
            tipo_enum = TipoCuenta[tipo_cuenta.upper()]
        except KeyError:
            tipo_enum = TipoCuenta.INGRESO

        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH datos_historicos AS (
                    SELECT
                        DATEDIFF(a.fecha, %s) as dias_desde_inicio,
                        SUM(CASE
                            WHEN c.tipo IN ('Ingreso', 'Pasivo') THEN t.haber
                            ELSE t.debe
                        END) as monto_diario
                    FROM contabilidad_empresa_transaccion t
                    JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                    JOIN contabilidad_empresa_plandecuentas c ON t.cuenta_id = c.id
                    WHERE a.empresa_id = %s
                      AND c.tipo = %s
                      AND a.estado = 'Confirmado'
                      AND a.anulado = FALSE
                      AND a.fecha >= %s
                    GROUP BY DATE(a.fecha)
                ),
                regresion AS (
                    SELECT
                        COUNT(*) as n,
                        AVG(dias_desde_inicio) as media_x,
                        AVG(monto_diario) as media_y,
                        SUM((dias_desde_inicio - AVG(dias_desde_inicio) OVER ()) *
                            (monto_diario - AVG(monto_diario) OVER ())) as suma_xy,
                        SUM(POW(dias_desde_inicio - AVG(dias_desde_inicio) OVER (), 2)) as suma_xx
                    FROM datos_historicos
                    WHERE monto_diario > 0
                )
                SELECT
                    n,
                    media_y,
                    -- y = a + bx (ecuación de regresión lineal)
                    (media_y - (suma_xy / NULLIF(suma_xx, 0)) * media_x) as intercept_a,
                    (suma_xy / NULLIF(suma_xx, 0)) as slope_b
                FROM regresion
                """,
                [fecha_inicio, self.empresa.id, tipo_enum.value, fecha_inicio],
            )

            result = cursor.fetchone()

            if not result or not result[0]:
                return {
                    "tipo_cuenta": tipo_cuenta,
                    "error": "No hay datos suficientes para regresión",
                    "prediccion": 0.0,
                }

            n, media_y, intercept, slope = result

            # Calcular predicción para días futuros
            dias_prediccion = dias_historicos + dias_futuros
            prediccion = float(intercept or 0) + float(slope or 0) * dias_prediccion

            return {
                "tipo_cuenta": tipo_cuenta,
                "dias_historicos": dias_historicos,
                "dias_futuros": dias_futuros,
                "n_observaciones": int(n),
                "media_historica": float(media_y or 0),
                "intercept": float(intercept or 0),
                "slope": float(slope or 0),
                "tendencia": "Creciente" if (slope or 0) > 0 else "Decreciente",
                "prediccion": round(max(prediccion, 0), 2),
                "prediccion_lower": round(max(prediccion * 0.9, 0), 2),
                "prediccion_upper": round(prediccion * 1.1, 2),
            }
