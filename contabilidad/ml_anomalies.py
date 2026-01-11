"""
Servicio de detección de anomalías en transacciones contables usando ML.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
from django.db import connection, transaction
from django.utils import timezone
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from contabilidad.models import (
    AnomaliaDetectada,
    Empresa,
)

logger = logging.getLogger(__name__)


class AnomalyService:
    """
    Servicio para detectar anomalías en transacciones contables.

    Detecta:
    - Montos inusuales (Isolation Forest)
    - Frecuencias anormales
    - Patrones sospechosos
    - Inconsistencias temporales
    """

    def __init__(self, empresa: Empresa):
        """
        Inicializa el servicio de detección de anomalías.

        Args:
            empresa: Empresa a analizar
        """
        self.empresa = empresa

    def detectar_anomalias_monto(
        self,
        dias_historicos: int = 180,
        contamination: float = 0.05,
        guardar: bool = True,
    ) -> dict:
        """
        Detecta transacciones con montos anómalos usando Isolation Forest.

        Args:
            dias_historicos: Días de historial para entrenar
            contamination: Proporción esperada de outliers (0.01-0.5)
            guardar: Si debe guardar las anomalías en la BD

        Returns:
            dict con success, anomalias_detectadas, total_transacciones, estadisticas
        """
        try:
            fecha_inicio = datetime.now().date() - timedelta(days=dias_historicos)

            # Obtener datos de transacciones
            df = self._obtener_datos_transacciones(fecha_inicio)

            if len(df) < 10:
                return {
                    "success": False,
                    "error": f"Datos insuficientes: solo {len(df)} transacciones",
                }

            # Preparar features para el modelo
            features = self._preparar_features_monto(df)

            # Entrenar modelo Isolation Forest
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)

            modelo = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100,
                max_samples="auto",
            )
            predicciones = modelo.fit_predict(features_scaled)
            scores = modelo.score_samples(features_scaled)

            # Identificar anomalías (predicción = -1)
            df["anomalia"] = predicciones == -1
            df["score"] = scores

            anomalias = df[df["anomalia"]].copy()

            logger.info(
                f"Detectadas {len(anomalias)} anomalías de {len(df)} transacciones "
                f"({len(anomalias) / len(df) * 100:.1f}%)"
            )

            # Calcular estadísticas
            estadisticas = self._calcular_estadisticas_anomalias(df, anomalias)

            # Guardar anomalías
            if guardar and len(anomalias) > 0:
                anomalias_guardadas = self._guardar_anomalias_monto(anomalias)
            else:
                anomalias_guardadas = 0

            return {
                "success": True,
                "tipo_deteccion": "MONTO",
                "anomalias_detectadas": len(anomalias),
                "total_transacciones": len(df),
                "porcentaje_anomalias": len(anomalias) / len(df) * 100,
                "anomalias_guardadas": anomalias_guardadas if guardar else None,
                "estadisticas": estadisticas,
                "anomalias_detalle": anomalias[
                    [
                        "transaccion_id",
                        "fecha",
                        "monto",
                        "cuenta_codigo",
                        "cuenta_descripcion",
                        "score",
                    ]
                ]
                .head(20)
                .to_dict("records"),
            }

        except Exception as e:
            logger.error(f"Error detectando anomalías de monto: {e}")
            return {"success": False, "error": str(e)}

    def detectar_anomalias_frecuencia(
        self, dias_historicos: int = 180, umbral_desviaciones: float = 3.0, guardar: bool = True
    ) -> dict:
        """
        Detecta cuentas con frecuencias anormales de transacciones.

        Args:
            dias_historicos: Días de historial para analizar
            umbral_desviaciones: Número de desviaciones estándar para considerar anómalo
            guardar: Si debe guardar las anomalías en la BD

        Returns:
            dict con success, anomalias_detectadas, estadisticas
        """
        try:
            fecha_inicio = datetime.now().date() - timedelta(days=dias_historicos)

            # Query para obtener frecuencias por cuenta
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        c.id as cuenta_id,
                        c.codigo,
                        c.descripcion,
                        COUNT(*) as num_transacciones,
                        AVG(t.debe + t.haber) as monto_promedio,
                        MIN(a.fecha) as primera_fecha,
                        MAX(a.fecha) as ultima_fecha,
                        COUNT(DISTINCT a.id) as num_asientos
                    FROM contabilidad_empresa_plandecuentas c
                    INNER JOIN contabilidad_empresa_transaccion t ON c.id = t.cuenta_id
                    INNER JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                    WHERE c.empresa_id = %s
                        AND a.fecha >= %s
                        AND a.anulado = FALSE
                        AND a.estado = 'Confirmado'
                    GROUP BY c.id, c.codigo, c.descripcion
                    HAVING COUNT(*) > 0
                    """,
                    [self.empresa.id, fecha_inicio],
                )

                columnas = [col[0] for col in cursor.description]
                datos = cursor.fetchall()

            if not datos:
                return {
                    "success": False,
                    "error": "No hay transacciones en el periodo",
                }

            df = pd.DataFrame(datos, columns=columnas)

            # Calcular estadísticas
            media = df["num_transacciones"].mean()
            std = df["num_transacciones"].std()

            if std == 0:
                return {
                    "success": False,
                    "error": "Desviación estándar es 0, no se pueden detectar anomalías",
                }

            # Detectar anomalías (frecuencia muy alta o muy baja)
            df["z_score"] = (df["num_transacciones"] - media) / std
            df["anomalia"] = np.abs(df["z_score"]) > umbral_desviaciones

            anomalias = df[df["anomalia"]].copy()

            logger.info(f"Detectadas {len(anomalias)} cuentas con frecuencia anómala de {len(df)}")

            # Guardar anomalías
            if guardar and len(anomalias) > 0:
                anomalias_guardadas = self._guardar_anomalias_frecuencia(anomalias)
            else:
                anomalias_guardadas = 0

            return {
                "success": True,
                "tipo_deteccion": "FRECUENCIA",
                "anomalias_detectadas": len(anomalias),
                "total_cuentas_analizadas": len(df),
                "anomalias_guardadas": anomalias_guardadas if guardar else None,
                "estadisticas": {
                    "frecuencia_media": float(media),
                    "frecuencia_std": float(std),
                    "umbral_superior": float(media + umbral_desviaciones * std),
                    "umbral_inferior": float(media - umbral_desviaciones * std),
                },
                "anomalias_detalle": anomalias[
                    [
                        "cuenta_id",
                        "codigo",
                        "descripcion",
                        "num_transacciones",
                        "z_score",
                        "monto_promedio",
                    ]
                ]
                .head(20)
                .to_dict("records"),
            }

        except Exception as e:
            logger.error(f"Error detectando anomalías de frecuencia: {e}")
            return {"success": False, "error": str(e)}

    def detectar_anomalias_temporales(
        self, dias_historicos: int = 180, guardar: bool = True
    ) -> dict:
        """
        Detecta transacciones en horarios o fechas inusuales.

        Args:
            dias_historicos: Días de historial para analizar
            guardar: Si debe guardar las anomalías en la BD

        Returns:
            dict con success, anomalias_detectadas
        """
        try:
            fecha_inicio = datetime.now().date() - timedelta(days=dias_historicos)

            # Query para obtener transacciones con información temporal
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        a.id as asiento_id,
                        a.fecha,
                        a.fecha_creacion,
                        DAYOFWEEK(a.fecha) as dia_semana,
                        HOUR(a.fecha_creacion) as hora_creacion,
                        COUNT(t.id) as num_transacciones,
                        SUM(t.debe + t.haber) as monto_total
                    FROM contabilidad_empresa_asiento a
                    LEFT JOIN contabilidad_empresa_transaccion t ON a.id = t.asiento_id
                    WHERE a.empresa_id = %s
                        AND a.fecha >= %s
                        AND a.anulado = FALSE
                    GROUP BY a.id, a.fecha, a.fecha_creacion
                    """,
                    [self.empresa.id, fecha_inicio],
                )

                columnas = [col[0] for col in cursor.description]
                datos = cursor.fetchall()

            if not datos:
                return {
                    "success": False,
                    "error": "No hay asientos en el periodo",
                }

            df = pd.DataFrame(datos, columns=columnas)
            anomalias_temp = []

            # Detectar transacciones en fines de semana (1=Domingo, 7=Sábado en MySQL)
            anomalias_fin_semana = df[df["dia_semana"].isin([1, 7])].copy()
            if len(anomalias_fin_semana) > 0:
                anomalias_fin_semana["motivo"] = "Transacción en fin de semana"
                anomalias_temp.append(anomalias_fin_semana)

            # Detectar transacciones fuera del horario laboral (antes 6am o después 10pm)
            anomalias_horario = df[(df["hora_creacion"] < 6) | (df["hora_creacion"] > 22)].copy()
            if len(anomalias_horario) > 0:
                anomalias_horario["motivo"] = "Transacción fuera de horario laboral"
                anomalias_temp.append(anomalias_horario)

            # Combinar todas las anomalías temporales
            if anomalias_temp:
                anomalias = pd.concat(anomalias_temp).drop_duplicates(subset=["asiento_id"])
            else:
                anomalias = pd.DataFrame()

            logger.info(f"Detectadas {len(anomalias)} anomalías temporales de {len(df)} asientos")

            # Guardar anomalías
            if guardar and len(anomalias) > 0:
                anomalias_guardadas = self._guardar_anomalias_temporales(anomalias)
            else:
                anomalias_guardadas = 0

            return {
                "success": True,
                "tipo_deteccion": "TEMPORAL",
                "anomalias_detectadas": len(anomalias),
                "total_asientos_analizados": len(df),
                "anomalias_guardadas": anomalias_guardadas if guardar else None,
                "anomalias_detalle": anomalias[
                    ["asiento_id", "fecha", "dia_semana", "hora_creacion", "motivo"]
                ]
                .head(20)
                .to_dict("records")
                if len(anomalias) > 0
                else [],
            }

        except Exception as e:
            logger.error(f"Error detectando anomalías temporales: {e}")
            return {"success": False, "error": str(e)}

    def detectar_anomalias_patrones(self, dias_historicos: int = 180, guardar: bool = True) -> dict:
        """
        Detecta patrones sospechosos en transacciones.

        Detecta:
        - Números redondos sospechosos (100, 1000, 5000, etc.)
        - Transacciones duplicadas exactas en corto tiempo
        - Secuencias inusuales de montos

        Args:
            dias_historicos: Días de historial para analizar
            guardar: Si debe guardar las anomalías en la BD

        Returns:
            dict con success, anomalias_detectadas
        """
        try:
            fecha_inicio = datetime.now().date() - timedelta(days=dias_historicos)

            # Obtener transacciones
            df = self._obtener_datos_transacciones(fecha_inicio)

            if len(df) < 10:
                return {
                    "success": False,
                    "error": f"Datos insuficientes: solo {len(df)} transacciones",
                }

            anomalias_patron = []

            # 1. Detectar números redondos sospechosos
            # Montos que son exactamente múltiplos de 1000 y mayores a 10000
            df["monto_float"] = df["monto"].astype(float)
            df["es_redondo"] = (df["monto_float"] % 1000 == 0) & (df["monto_float"] >= 10000)

            anomalias_redondos = df[df["es_redondo"]].copy()
            if len(anomalias_redondos) > 0:
                anomalias_redondos["motivo"] = "Monto redondo sospechoso"
                anomalias_redondos["patron_tipo"] = "REDONDO"
                anomalias_patron.append(anomalias_redondos)

            # 2. Detectar transacciones duplicadas (mismo monto, misma cuenta, mismo día)
            df_sorted = df.sort_values(["cuenta_id", "fecha", "monto"])
            df_sorted["duplicado"] = (
                (df_sorted["cuenta_id"] == df_sorted["cuenta_id"].shift())
                & (df_sorted["fecha"] == df_sorted["fecha"].shift())
                & (df_sorted["monto"] == df_sorted["monto"].shift())
            )

            anomalias_duplicados = df_sorted[df_sorted["duplicado"]].copy()
            if len(anomalias_duplicados) > 0:
                anomalias_duplicados["motivo"] = "Transacción duplicada"
                anomalias_duplicados["patron_tipo"] = "DUPLICADO"
                anomalias_patron.append(anomalias_duplicados)

            # 3. Detectar secuencias exactas (3 o más transacciones consecutivas con mismo monto)
            df_sorted["mismo_monto_consecutivo"] = (
                df_sorted["monto"] == df_sorted["monto"].shift()
            ) & (df_sorted["monto"] == df_sorted["monto"].shift(2))

            anomalias_secuencias = df_sorted[df_sorted["mismo_monto_consecutivo"]].copy()
            if len(anomalias_secuencias) > 0:
                anomalias_secuencias["motivo"] = "Secuencia de montos idénticos"
                anomalias_secuencias["patron_tipo"] = "SECUENCIA"
                anomalias_patron.append(anomalias_secuencias)

            # Combinar todas las anomalías de patrón
            if anomalias_patron:
                anomalias = pd.concat(anomalias_patron).drop_duplicates(subset=["transaccion_id"])
            else:
                anomalias = pd.DataFrame()

            logger.info(
                f"Detectadas {len(anomalias)} anomalías de patrón de {len(df)} transacciones"
            )

            # Guardar anomalías
            if guardar and len(anomalias) > 0:
                anomalias_guardadas = self._guardar_anomalias_patrones(anomalias)
            else:
                anomalias_guardadas = 0

            return {
                "success": True,
                "tipo_deteccion": "PATRON",
                "anomalias_detectadas": len(anomalias),
                "total_transacciones": len(df),
                "anomalias_guardadas": anomalias_guardadas if guardar else None,
                "anomalias_detalle": anomalias[
                    [
                        "transaccion_id",
                        "fecha",
                        "monto",
                        "cuenta_codigo",
                        "motivo",
                        "patron_tipo",
                    ]
                ]
                .head(20)
                .to_dict("records")
                if len(anomalias) > 0
                else [],
            }

        except Exception as e:
            logger.error(f"Error detectando anomalías de patrón: {e}")
            return {"success": False, "error": str(e)}

    def detectar_todas_anomalias(self, dias_historicos: int = 180, guardar: bool = True) -> dict:
        """
        Ejecuta todos los tipos de detección de anomalías.

        Args:
            dias_historicos: Días de historial para analizar
            guardar: Si debe guardar las anomalías en la BD

        Returns:
            dict con resumen de todas las detecciones
        """
        logger.info(f"Iniciando detección completa de anomalías para {self.empresa.nombre}")

        resultados = {}

        # 1. Anomalías de monto (Isolation Forest)
        logger.info("Detectando anomalías de monto...")
        resultados["monto"] = self.detectar_anomalias_monto(
            dias_historicos=dias_historicos, guardar=guardar
        )

        # 2. Anomalías de frecuencia
        logger.info("Detectando anomalías de frecuencia...")
        resultados["frecuencia"] = self.detectar_anomalias_frecuencia(
            dias_historicos=dias_historicos, guardar=guardar
        )

        # 3. Anomalías temporales
        logger.info("Detectando anomalías temporales...")
        resultados["temporal"] = self.detectar_anomalias_temporales(
            dias_historicos=dias_historicos, guardar=guardar
        )

        # 4. Anomalías de patrón
        logger.info("Detectando anomalías de patrón...")
        resultados["patron"] = self.detectar_anomalias_patrones(
            dias_historicos=dias_historicos, guardar=guardar
        )

        # Calcular totales
        total_anomalias = sum(
            r.get("anomalias_detectadas", 0) for r in resultados.values() if r.get("success")
        )
        total_guardadas = sum(
            r.get("anomalias_guardadas", 0)
            for r in resultados.values()
            if r.get("success") and r.get("anomalias_guardadas") is not None
        )

        return {
            "success": True,
            "empresa": self.empresa.nombre,
            "dias_historicos": dias_historicos,
            "total_anomalias_detectadas": total_anomalias,
            "total_anomalias_guardadas": total_guardadas if guardar else None,
            "resultados_por_tipo": resultados,
        }

    # Métodos auxiliares privados

    def _obtener_datos_transacciones(self, fecha_inicio) -> pd.DataFrame:
        """Obtiene datos de transacciones para análisis."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    t.id as transaccion_id,
                    a.id as asiento_id,
                    a.fecha,
                    c.id as cuenta_id,
                    c.codigo as cuenta_codigo,
                    c.descripcion as cuenta_descripcion,
                    c.tipo as cuenta_tipo,
                    (t.debe + t.haber) as monto,
                    t.debe,
                    t.haber,
                    a.fecha_creacion
                FROM contabilidad_empresa_transaccion t
                INNER JOIN contabilidad_empresa_asiento a ON t.asiento_id = a.id
                INNER JOIN contabilidad_empresa_plandecuentas c ON t.cuenta_id = c.id
                WHERE c.empresa_id = %s
                    AND a.fecha >= %s
                    AND a.anulado = FALSE
                    AND a.estado = 'Confirmado'
                ORDER BY a.fecha, t.id
                """,
                [self.empresa.id, fecha_inicio],
            )

            columnas = [col[0] for col in cursor.description]
            datos = cursor.fetchall()

        return pd.DataFrame(datos, columns=columnas)

    def _preparar_features_monto(self, df: pd.DataFrame) -> np.ndarray:
        """Prepara features para el modelo de detección de anomalías de monto."""
        features = []

        # Feature 1: Monto (log-transformado para manejar outliers)
        monto = df["monto"].astype(float)
        monto_log = np.log1p(monto)  # log(1 + x) para evitar log(0)
        features.append(monto_log)

        # Feature 2: Ratio debe/haber (con manejo de división por 0)
        debe = df["debe"].astype(float)
        haber = df["haber"].astype(float)
        ratio = np.where(haber > 0, debe / haber, debe)
        features.append(ratio)

        # Feature 3: Día del mes (normalizado)
        dia_mes = pd.to_datetime(df["fecha"]).dt.day / 31.0
        features.append(dia_mes)

        # Feature 4: Día de la semana (normalizado)
        dia_semana = pd.to_datetime(df["fecha"]).dt.dayofweek / 6.0
        features.append(dia_semana)

        return np.column_stack(features)

    def _calcular_estadisticas_anomalias(self, df: pd.DataFrame, anomalias: pd.DataFrame) -> dict:
        """Calcula estadísticas sobre las anomalías detectadas."""
        stats = {
            "monto_promedio_normal": float(
                df[~df["anomalia"]]["monto"].mean() if len(df[~df["anomalia"]]) > 0 else 0
            ),
            "monto_promedio_anomalo": float(anomalias["monto"].mean() if len(anomalias) > 0 else 0),
            "monto_max_anomalo": float(anomalias["monto"].max() if len(anomalias) > 0 else 0),
            "monto_min_anomalo": float(anomalias["monto"].min() if len(anomalias) > 0 else 0),
            "score_promedio": float(anomalias["score"].mean() if len(anomalias) > 0 else 0),
            "score_min": float(anomalias["score"].min() if len(anomalias) > 0 else 0),
        }

        # Distribución por tipo de cuenta
        if len(anomalias) > 0:
            distribucion = anomalias["cuenta_tipo"].value_counts().to_dict()
            stats["distribucion_por_tipo"] = distribucion

        return stats

    @transaction.atomic
    def _guardar_anomalias_monto(self, anomalias: pd.DataFrame) -> int:
        """Guarda anomalías de monto en la base de datos."""
        objetos = []

        for _, row in anomalias.iterrows():
            # Determinar severidad basada en el score
            score = float(row["score"])
            if score < -0.5:
                severidad = "CRITICA"
            elif score < -0.3:
                severidad = "ALTA"
            elif score < -0.1:
                severidad = "MEDIA"
            else:
                severidad = "BAJA"

            descripcion = (
                f"Monto anómalo: ${row['monto']:,.2f} en cuenta {row['cuenta_codigo']} - "
                f"{row['cuenta_descripcion']}. Score: {score:.4f}"
            )

            objetos.append(
                AnomaliaDetectada(
                    empresa=self.empresa,
                    transaccion_id=int(row["transaccion_id"]),
                    tipo_anomalia="MONTO",
                    severidad=severidad,
                    score_anomalia=Decimal(str(score)),
                    descripcion=descripcion,
                    algoritmo_usado="IsolationForest",
                )
            )

        if objetos:
            AnomaliaDetectada.objects.bulk_create(objetos, ignore_conflicts=True)

        return len(objetos)

    @transaction.atomic
    def _guardar_anomalias_frecuencia(self, anomalias: pd.DataFrame) -> int:
        """Guarda anomalías de frecuencia en la base de datos."""
        objetos = []

        for _, row in anomalias.iterrows():
            # Determinar severidad basada en el z-score
            z_score = float(row["z_score"])
            if abs(z_score) > 5:
                severidad = "CRITICA"
            elif abs(z_score) > 4:
                severidad = "ALTA"
            elif abs(z_score) > 3:
                severidad = "MEDIA"
            else:
                severidad = "BAJA"

            if z_score > 0:
                tipo_anomalia = "Frecuencia excesivamente alta"
            else:
                tipo_anomalia = "Frecuencia excesivamente baja"

            descripcion = (
                f"{tipo_anomalia}: {int(row['num_transacciones'])} transacciones en cuenta "
                f"{row['codigo']} - {row['descripcion']}. Z-score: {z_score:.2f}"
            )

            objetos.append(
                AnomaliaDetectada(
                    empresa=self.empresa,
                    tipo_anomalia="FREQ",
                    severidad=severidad,
                    score_anomalia=Decimal(str(abs(z_score))),
                    descripcion=descripcion,
                    algoritmo_usado="Z-Score",
                )
            )

        if objetos:
            AnomaliaDetectada.objects.bulk_create(objetos, ignore_conflicts=True)

        return len(objetos)

    @transaction.atomic
    def _guardar_anomalias_temporales(self, anomalias: pd.DataFrame) -> int:
        """Guarda anomalías temporales en la base de datos."""
        objetos = []

        for _, row in anomalias.iterrows():
            objetos.append(
                AnomaliaDetectada(
                    empresa=self.empresa,
                    asiento_id=int(row["asiento_id"]),
                    tipo_anomalia="TEMP",
                    severidad="MEDIA",
                    score_anomalia=Decimal("1.0"),
                    descripcion=f"{row['motivo']} - Fecha: {row['fecha']}, "
                    f"Día: {int(row['dia_semana'])}, Hora: {int(row['hora_creacion'])}:00",
                    algoritmo_usado="TemporalAnalysis",
                )
            )

        if objetos:
            AnomaliaDetectada.objects.bulk_create(objetos, ignore_conflicts=True)

        return len(objetos)

    @transaction.atomic
    def _guardar_anomalias_patrones(self, anomalias: pd.DataFrame) -> int:
        """Guarda anomalías de patrón en la base de datos."""
        objetos = []

        for _, row in anomalias.iterrows():
            # Severidad según el tipo de patrón
            if row["patron_tipo"] == "DUPLICADO":
                severidad = "ALTA"
            elif row["patron_tipo"] == "SECUENCIA":
                severidad = "MEDIA"
            else:  # REDONDO
                severidad = "BAJA"

            objetos.append(
                AnomaliaDetectada(
                    empresa=self.empresa,
                    transaccion_id=int(row["transaccion_id"]),
                    tipo_anomalia="PTRN",
                    severidad=severidad,
                    score_anomalia=Decimal("1.0"),
                    descripcion=f"{row['motivo']} - Monto: ${row['monto']:,.2f}, "
                    f"Cuenta: {row['cuenta_codigo']}",
                    algoritmo_usado="PatternAnalysis",
                )
            )

        if objetos:
            AnomaliaDetectada.objects.bulk_create(objetos, ignore_conflicts=True)

        return len(objetos)

    def obtener_anomalias_sin_revisar(self, limit: int = 50) -> list:
        """
        Obtiene anomalías sin revisar ordenadas por severidad.

        Args:
            limit: Número máximo de anomalías a retornar

        Returns:
            Lista de objetos AnomaliaDetectada
        """
        return list(
            AnomaliaDetectada.objects.filter(empresa=self.empresa, revisada=False)
            .order_by("-severidad", "-fecha_deteccion")
            .select_related("empresa")[:limit]
        )

    def marcar_como_revisada(
        self, anomalia_id: int, es_falso_positivo: bool, notas: str, usuario=None
    ) -> bool:
        """
        Marca una anomalía como revisada.

        Args:
            anomalia_id: ID de la anomalía
            es_falso_positivo: Si es un falso positivo
            notas: Notas de la revisión
            usuario: Usuario que revisa (opcional)

        Returns:
            True si se marcó exitosamente
        """
        try:
            anomalia = AnomaliaDetectada.objects.get(id=anomalia_id, empresa=self.empresa)
            anomalia.revisada = True
            anomalia.es_falso_positivo = es_falso_positivo
            anomalia.notas_revision = notas
            anomalia.fecha_revision = timezone.now()
            if usuario:
                anomalia.revisada_por = usuario
            anomalia.save()
            return True
        except AnomaliaDetectada.DoesNotExist:
            logger.error(f"Anomalía {anomalia_id} no encontrada")
            return False
