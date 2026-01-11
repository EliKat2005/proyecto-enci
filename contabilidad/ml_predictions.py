"""
Servicio de Predicciones Financieras usando Prophet (Facebook).
Predice flujos de efectivo, ingresos, gastos y otras métricas financieras.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from django.db import connection
from prophet import Prophet

from contabilidad.models import (
    Empresa,
    PrediccionFinanciera,
)

logger = logging.getLogger(__name__)


class PredictionService:
    """
    Servicio para generar predicciones financieras usando Prophet.
    Prophet es robusto con datos faltantes, tendencias y estacionalidad.
    """

    def __init__(self, empresa: Empresa):
        self.empresa = empresa

    def obtener_serie_temporal(
        self, tipo_dato: str, fecha_inicio: date = None, fecha_fin: date = None
    ) -> pd.DataFrame:
        """
        Obtiene serie temporal de datos financieros.

        Args:
            tipo_dato: 'INGR', 'GAST', 'FLUJ', 'PATR', 'UTIL'
            fecha_inicio: Fecha de inicio (default: 1 año atrás)
            fecha_fin: Fecha final (default: hoy)

        Returns:
            DataFrame con columnas ['ds', 'y'] para Prophet
        """
        if fecha_fin is None:
            fecha_fin = date.today()
        if fecha_inicio is None:
            fecha_inicio = fecha_fin - timedelta(days=365)

        logger.info(f"Obteniendo serie temporal {tipo_dato} desde {fecha_inicio} hasta {fecha_fin}")

        with connection.cursor() as cursor:
            # Query optimizado con agregación por fecha
            if tipo_dato == "INGR":
                # Ingresos (naturaleza acreedora)
                cursor.execute(
                    """
                    SELECT
                        a.fecha as ds,
                        SUM(t.haber - t.debe) as y
                    FROM contabilidad_empresa_asiento a
                    INNER JOIN contabilidad_empresa_transaccion t ON a.id = t.asiento_id
                    INNER JOIN contabilidad_empresa_plandecuentas c ON t.cuenta_id = c.id
                    WHERE a.empresa_id = %s
                        AND a.estado = 'Confirmado'
                        AND a.anulado = FALSE
                        AND a.fecha BETWEEN %s AND %s
                        AND c.tipo = 'Ingreso'
                    GROUP BY a.fecha
                    ORDER BY a.fecha
                """,
                    [self.empresa.id, fecha_inicio, fecha_fin],
                )

            elif tipo_dato == "GAST":
                # Gastos y costos (naturaleza deudora)
                cursor.execute(
                    """
                    SELECT
                        a.fecha as ds,
                        SUM(t.debe - t.haber) as y
                    FROM contabilidad_empresa_asiento a
                    INNER JOIN contabilidad_empresa_transaccion t ON a.id = t.asiento_id
                    INNER JOIN contabilidad_empresa_plandecuentas c ON t.cuenta_id = c.id
                    WHERE a.empresa_id = %s
                        AND a.estado = 'Confirmado'
                        AND a.anulado = FALSE
                        AND a.fecha BETWEEN %s AND %s
                        AND c.tipo IN ('Gasto', 'Costo')
                    GROUP BY a.fecha
                    ORDER BY a.fecha
                """,
                    [self.empresa.id, fecha_inicio, fecha_fin],
                )

            elif tipo_dato == "FLUJ":
                # Flujo de efectivo (cuentas de caja y bancos - código 11xx)
                cursor.execute(
                    """
                    SELECT
                        a.fecha as ds,
                        SUM(t.debe - t.haber) as y
                    FROM contabilidad_empresa_asiento a
                    INNER JOIN contabilidad_empresa_transaccion t ON a.id = t.asiento_id
                    INNER JOIN contabilidad_empresa_plandecuentas c ON t.cuenta_id = c.id
                    WHERE a.empresa_id = %s
                        AND a.estado = 'Confirmado'
                        AND a.anulado = FALSE
                        AND a.fecha BETWEEN %s AND %s
                        AND c.tipo = 'Activo'
                        AND (
                            c.codigo LIKE '11%%'
                            OR LOWER(c.descripcion) LIKE '%%caja%%'
                            OR LOWER(c.descripcion) LIKE '%%banco%%'
                        )
                    GROUP BY a.fecha
                    ORDER BY a.fecha
                """,
                    [self.empresa.id, fecha_inicio, fecha_fin],
                )

            elif tipo_dato == "UTIL":
                # Utilidad = Ingresos - (Gastos + Costos)
                cursor.execute(
                    """
                    SELECT
                        a.fecha as ds,
                        SUM(CASE
                            WHEN c.tipo = 'Ingreso' THEN t.haber - t.debe
                            WHEN c.tipo IN ('Gasto', 'Costo') THEN -(t.debe - t.haber)
                            ELSE 0
                        END) as y
                    FROM contabilidad_empresa_asiento a
                    INNER JOIN contabilidad_empresa_transaccion t ON a.id = t.asiento_id
                    INNER JOIN contabilidad_empresa_plandecuentas c ON t.cuenta_id = c.id
                    WHERE a.empresa_id = %s
                        AND a.estado = 'Confirmado'
                        AND a.anulado = FALSE
                        AND a.fecha BETWEEN %s AND %s
                        AND c.tipo IN ('Ingreso', 'Gasto', 'Costo')
                    GROUP BY a.fecha
                    ORDER BY a.fecha
                """,
                    [self.empresa.id, fecha_inicio, fecha_fin],
                )

            else:
                raise ValueError(f"Tipo de dato no soportado: {tipo_dato}")

            rows = cursor.fetchall()

        # Convertir a DataFrame
        if not rows:
            logger.warning(f"No hay datos disponibles para {tipo_dato}")
            return pd.DataFrame(columns=["ds", "y"])

        df = pd.DataFrame(rows, columns=["ds", "y"])
        df["ds"] = pd.to_datetime(df["ds"])
        df["y"] = df["y"].astype(float)

        # Rellenar fechas faltantes con 0 (importante para Prophet)
        df = df.set_index("ds").resample("D").sum().reset_index()
        df["y"] = df["y"].fillna(0)

        logger.info(f"Serie temporal obtenida: {len(df)} registros")
        return df

    def predecir_con_prophet(
        self,
        df: pd.DataFrame,
        periodos: int = 30,
        intervalo_confianza: float = 0.95,
    ) -> tuple[Prophet, pd.DataFrame]:
        """
        Entrena modelo Prophet y genera predicciones.

        Args:
            df: DataFrame con columnas ['ds', 'y']
            periodos: Días a predecir
            intervalo_confianza: Nivel de confianza para intervalos

        Returns:
            Tupla (modelo, predicciones_df)
        """
        if len(df) < 10:
            raise ValueError("Se necesitan al menos 10 observaciones para entrenar")

        logger.info(f"Entrenando modelo Prophet con {len(df)} observaciones")

        # Configurar Prophet
        model = Prophet(
            interval_width=intervalo_confianza,
            daily_seasonality=False,  # Datos diarios sin patrón diario
            weekly_seasonality=True,  # Considerar patrones semanales
            yearly_seasonality="auto",  # Auto-detectar estacionalidad anual
            changepoint_prior_scale=0.05,  # Flexibilidad para cambios de tendencia
        )

        # Entrenar modelo
        model.fit(df)

        # Generar predicciones futuras
        future = model.make_future_dataframe(periods=periodos)
        forecast = model.predict(future)

        logger.info(f"Predicciones generadas para {periodos} días")
        return model, forecast

    def generar_predicciones(
        self,
        tipo_prediccion: str,
        dias_historicos: int = 365,
        dias_futuros: int = 30,
        guardar: bool = True,
    ) -> dict:
        """
        Genera predicciones financieras y las guarda en la base de datos.

        Args:
            tipo_prediccion: 'INGR', 'GAST', 'FLUJ', 'UTIL'
            dias_historicos: Días históricos para entrenar
            dias_futuros: Días a predecir
            guardar: Si True, guarda en BD

        Returns:
            Dict con predicciones, métricas y modelo
        """
        fecha_fin = date.today()
        fecha_inicio = fecha_fin - timedelta(days=dias_historicos)

        # Obtener datos históricos
        df = self.obtener_serie_temporal(tipo_prediccion, fecha_inicio, fecha_fin)

        if len(df) < 10:
            logger.warning(f"Datos insuficientes para {tipo_prediccion}: {len(df)} registros")
            return {
                "success": False,
                "error": "Datos insuficientes para generar predicciones",
            }

        try:
            # Entrenar y predecir
            model, forecast = self.predecir_con_prophet(df, periodos=dias_futuros)

            # Calcular métricas de error en datos históricos
            metricas = self._calcular_metricas_error(df, forecast)

            # Extraer predicciones futuras
            predicciones_futuras = forecast[forecast["ds"] > df["ds"].max()].copy()

            # Guardar en base de datos si se solicita
            if guardar:
                self._guardar_predicciones(tipo_prediccion, predicciones_futuras, metricas, model)

            resultado = {
                "success": True,
                "tipo_prediccion": tipo_prediccion,
                "empresa": self.empresa.nombre,
                "dias_historicos": len(df),
                "dias_predichos": len(predicciones_futuras),
                "metricas": metricas,
                "predicciones": predicciones_futuras[
                    ["ds", "yhat", "yhat_lower", "yhat_upper"]
                ].to_dict("records"),
                "tendencia": self._analizar_tendencia(predicciones_futuras),
            }

            logger.info(f"Predicciones generadas exitosamente para {tipo_prediccion}")
            return resultado

        except Exception as e:
            logger.error(f"Error generando predicciones: {e}")
            return {"success": False, "error": str(e)}

    def _calcular_metricas_error(self, df_real: pd.DataFrame, forecast: pd.DataFrame) -> dict:
        """
        Calcula métricas de error del modelo (MAE, RMSE, MAPE).

        Args:
            df_real: Datos reales
            forecast: Predicciones

        Returns:
            Dict con métricas
        """
        # Merge para comparar valores reales vs predichos
        merged = df_real.merge(forecast[["ds", "yhat"]], on="ds", how="inner")

        if len(merged) == 0:
            return {"mae": None, "rmse": None, "mape": None}

        y_true = merged["y"].values
        y_pred = merged["yhat"].values

        # MAE (Mean Absolute Error)
        mae = np.mean(np.abs(y_true - y_pred))

        # RMSE (Root Mean Squared Error)
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))

        # MAPE (Mean Absolute Percentage Error)
        # Evitar división por cero
        non_zero_mask = y_true != 0
        if non_zero_mask.any():
            mape = (
                np.mean(
                    np.abs(y_true[non_zero_mask] - y_pred[non_zero_mask])
                    / np.abs(y_true[non_zero_mask])
                )
                * 100
            )
        else:
            mape = None

        return {"mae": float(mae), "rmse": float(rmse), "mape": float(mape) if mape else None}

    def _analizar_tendencia(self, predicciones: pd.DataFrame) -> str:
        """
        Analiza la tendencia de las predicciones.

        Args:
            predicciones: DataFrame con predicciones

        Returns:
            Descripción de la tendencia
        """
        if len(predicciones) < 2:
            return "Sin suficientes datos"

        valores = predicciones["yhat"].values
        primer_tercio = valores[: len(valores) // 3].mean()
        ultimo_tercio = valores[-len(valores) // 3 :].mean()

        cambio_porcentual = (
            ((ultimo_tercio - primer_tercio) / abs(primer_tercio) * 100)
            if primer_tercio != 0
            else 0
        )

        if abs(cambio_porcentual) < 5:
            return f"Estable (cambio: {cambio_porcentual:.1f}%)"
        elif cambio_porcentual > 5:
            return f"Creciente (+{cambio_porcentual:.1f}%)"
        else:
            return f"Decreciente ({cambio_porcentual:.1f}%)"

    def _guardar_predicciones(
        self,
        tipo_prediccion: str,
        predicciones: pd.DataFrame,
        metricas: dict,
        modelo: Prophet,
    ):
        """
        Guarda predicciones en la base de datos.

        Args:
            tipo_prediccion: Tipo de predicción
            predicciones: DataFrame con predicciones
            metricas: Métricas del modelo
            modelo: Modelo Prophet entrenado
        """
        # Eliminar predicciones antiguas del mismo tipo
        PrediccionFinanciera.objects.filter(
            empresa=self.empresa,
            tipo_prediccion=tipo_prediccion,
            modelo_usado="PROPHET",
        ).delete()

        # Crear nuevas predicciones
        objetos = []
        for _, row in predicciones.iterrows():
            obj = PrediccionFinanciera(
                empresa=self.empresa,
                tipo_prediccion=tipo_prediccion,
                modelo_usado="PROPHET",
                fecha_prediccion=row["ds"].date(),
                valor_predicho=Decimal(str(round(row["yhat"], 2))),
                limite_inferior=Decimal(str(round(row["yhat_lower"], 2))),
                limite_superior=Decimal(str(round(row["yhat_upper"], 2))),
                confianza=Decimal("95.00"),
                metricas_modelo=metricas,
                datos_entrenamiento={
                    "dias_entrenamiento": len(modelo.history),
                    "fecha_inicio_entrenamiento": str(modelo.history["ds"].min().date()),
                    "fecha_fin_entrenamiento": str(modelo.history["ds"].max().date()),
                },
            )
            objetos.append(obj)

        # Bulk create para eficiencia
        PrediccionFinanciera.objects.bulk_create(objetos)
        logger.info(f"Guardadas {len(objetos)} predicciones en la base de datos")

    def generar_todas_predicciones(
        self, dias_historicos: int = 365, dias_futuros: int = 30
    ) -> dict:
        """
        Genera predicciones para todos los tipos disponibles.

        Args:
            dias_historicos: Días históricos para entrenar
            dias_futuros: Días a predecir

        Returns:
            Dict con resultados de todas las predicciones
        """
        tipos = ["INGR", "GAST", "FLUJ", "UTIL"]
        resultados = {}

        for tipo in tipos:
            logger.info(f"Generando predicciones para {tipo}")
            resultado = self.generar_predicciones(
                tipo_prediccion=tipo,
                dias_historicos=dias_historicos,
                dias_futuros=dias_futuros,
                guardar=True,
            )
            resultados[tipo] = resultado

        return resultados

    def obtener_predicciones_guardadas(self, tipo_prediccion: str = None) -> list[dict]:
        """
        Obtiene predicciones guardadas en la base de datos.

        Args:
            tipo_prediccion: Filtrar por tipo (opcional)

        Returns:
            Lista de predicciones
        """
        queryset = PrediccionFinanciera.objects.filter(
            empresa=self.empresa, modelo_usado="PROPHET"
        ).order_by("fecha_prediccion")

        if tipo_prediccion:
            queryset = queryset.filter(tipo_prediccion=tipo_prediccion)

        predicciones = []
        for p in queryset:
            predicciones.append(
                {
                    "tipo": p.get_tipo_prediccion_display(),
                    "tipo_codigo": p.tipo_prediccion,
                    "fecha": p.fecha_prediccion.isoformat(),
                    "valor_predicho": float(p.valor_predicho),
                    "limite_inferior": float(p.limite_inferior) if p.limite_inferior else None,
                    "limite_superior": float(p.limite_superior) if p.limite_superior else None,
                    "confianza": float(p.confianza),
                    "metricas": p.metricas_modelo,
                }
            )

        return predicciones
