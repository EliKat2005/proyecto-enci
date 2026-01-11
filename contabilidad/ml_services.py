"""
Servicios ML/AI para análisis contable avanzado.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Q, Sum

from .models import (
    Empresa,
    EmpresaPlanCuenta,
    EmpresaTransaccion,
    EstadoAsiento,
    TipoCuenta,
)

logger = logging.getLogger(__name__)


class MLAnalyticsService:
    """Servicio para análisis y métricas ML."""

    def __init__(self, empresa: Empresa):
        self.empresa = empresa

    def get_dashboard_metrics(self) -> dict[str, Any]:
        """
        Calcula métricas financieras principales para el dashboard.

        Returns:
            dict con liquidez, ROA, endeudamiento, margen_neto
        """
        # Obtener saldos por tipo de cuenta
        activos = self._get_saldo_por_tipo(TipoCuenta.ACTIVO)
        pasivos = self._get_saldo_por_tipo(TipoCuenta.PASIVO)
        patrimonio = self._get_saldo_por_tipo(TipoCuenta.PATRIMONIO)
        ingresos = self._get_saldo_por_tipo(TipoCuenta.INGRESO)
        gastos = self._get_saldo_por_tipo(TipoCuenta.GASTO)
        costos = self._get_saldo_por_tipo(TipoCuenta.COSTO)

        # Liquidez corriente (activos corrientes / pasivos corrientes)
        # Simplificado: usamos todos los activos y pasivos
        liquidez = float(activos / pasivos) if pasivos > 0 else 0.0

        # Utilidad Neta = Ingresos - Costos - Gastos
        utilidad_neta = ingresos - costos - gastos

        # ROA = Utilidad Neta / Activos Totales × 100
        roa = float((utilidad_neta / activos) * 100) if activos > 0 else 0.0

        # Endeudamiento = Pasivos / Activos × 100
        endeudamiento = float((pasivos / activos) * 100) if activos > 0 else 0.0

        # Margen Neto = Utilidad Neta / Ingresos × 100
        margen_neto = float((utilidad_neta / ingresos) * 100) if ingresos > 0 else 0.0

        return {
            "liquidez": round(liquidez, 2),
            "roa": round(roa, 2),
            "endeudamiento": round(endeudamiento, 2),
            "margen_neto": round(margen_neto, 2),
            "activos": float(activos),
            "pasivos": float(pasivos),
            "patrimonio": float(patrimonio),
            "ingresos": float(ingresos),
            "gastos": float(gastos),
            "costos": float(costos),
            "utilidad_neta": float(utilidad_neta),
        }

    def get_analytics_time_series(self, meses: int = 12) -> dict[str, Any]:
        """
        Genera series de tiempo para analytics.

        Args:
            meses: Número de meses a analizar

        Returns:
            dict con series de tiempo por categoría
        """
        fecha_inicio = date.today() - timedelta(days=30 * meses)

        # Obtener transacciones agrupadas por mes y tipo
        transacciones = EmpresaTransaccion.objects.filter(
            asiento__empresa=self.empresa,
            asiento__fecha__gte=fecha_inicio,
            asiento__estado=EstadoAsiento.CONFIRMADO,
        ).select_related("cuenta", "asiento")

        # Agrupar por mes
        series_por_mes = {}
        for trans in transacciones:
            mes_key = trans.asiento.fecha.strftime("%Y-%m")
            if mes_key not in series_por_mes:
                series_por_mes[mes_key] = {
                    "ingresos": Decimal("0"),
                    "gastos": Decimal("0"),
                    "costos": Decimal("0"),
                    "activos": Decimal("0"),
                    "pasivos": Decimal("0"),
                }

            if trans.cuenta:
                if trans.cuenta.tipo == TipoCuenta.INGRESO:
                    series_por_mes[mes_key]["ingresos"] += trans.haber
                elif trans.cuenta.tipo == TipoCuenta.GASTO:
                    series_por_mes[mes_key]["gastos"] += trans.debe
                elif trans.cuenta.tipo == TipoCuenta.COSTO:
                    series_por_mes[mes_key]["costos"] += trans.debe
                elif trans.cuenta.tipo == TipoCuenta.ACTIVO:
                    series_por_mes[mes_key]["activos"] += trans.debe - trans.haber
                elif trans.cuenta.tipo == TipoCuenta.PASIVO:
                    series_por_mes[mes_key]["pasivos"] += trans.haber - trans.debe

        # Convertir a lista ordenada
        series = []
        for mes in sorted(series_por_mes.keys()):
            data = series_por_mes[mes]
            series.append(
                {
                    "periodo": mes,
                    "ingresos": float(data["ingresos"]),
                    "gastos": float(data["gastos"]),
                    "costos": float(data["costos"]),
                    "utilidad": float(data["ingresos"] - data["costos"] - data["gastos"]),
                    "activos": float(data["activos"]),
                    "pasivos": float(data["pasivos"]),
                }
            )

        return {
            "series": series,
            "total_periodos": len(series),
        }

    def generate_predictions(self, tipo_cuenta: str, periodos: int) -> dict[str, Any]:
        """
        Genera predicciones simples basadas en promedio móvil.

        Args:
            tipo_cuenta: Tipo de cuenta a predecir (INGRESO, GASTO, FLUJO)
            periodos: Número de períodos futuros a predecir

        Returns:
            dict con predicciones
        """
        # Obtener datos históricos
        fecha_inicio = date.today() - timedelta(days=365)

        # Manejar caso especial de FLUJO (Ingresos - Gastos)
        if tipo_cuenta == "FLUJO":
            return self._generate_flujo_predictions(fecha_inicio, periodos)

        # Validar tipo de cuenta
        try:
            tipo_enum = TipoCuenta[tipo_cuenta]
        except KeyError:
            # Si no existe, default a INGRESO
            tipo_enum = TipoCuenta.INGRESO

        # Obtener transacciones del tipo
        transacciones = (
            EmpresaTransaccion.objects.filter(
                asiento__empresa=self.empresa,
                asiento__fecha__gte=fecha_inicio,
                asiento__estado=EstadoAsiento.CONFIRMADO,
                cuenta__tipo=tipo_enum,
            )
            .values("asiento__fecha")
            .annotate(
                total_debe=Sum("debe"),
                total_haber=Sum("haber"),
            )
            .order_by("asiento__fecha")
        )

        # Agrupar por mes
        datos_mensuales = {}
        for trans in transacciones:
            mes = trans["asiento__fecha"].strftime("%Y-%m")
            if mes not in datos_mensuales:
                datos_mensuales[mes] = Decimal("0")

            # Para ingresos y pasivos, usamos haber; para gastos y activos, debe
            if tipo_enum in [TipoCuenta.INGRESO, TipoCuenta.PASIVO]:
                datos_mensuales[mes] += trans["total_haber"]
            else:
                datos_mensuales[mes] += trans["total_debe"]

        # Calcular promedio para predicción simple
        if datos_mensuales:
            promedio = sum(datos_mensuales.values()) / len(datos_mensuales)
        else:
            promedio = Decimal("0")

        # Generar predicciones (simplificado: usar promedio con pequeña variación)
        historico = [
            {"periodo": mes, "valor": float(valor)}
            for mes, valor in sorted(datos_mensuales.items())
        ]

        # Generar fechas futuras
        ultima_fecha = date.today()
        predicciones = []
        for i in range(1, periodos + 1):
            fecha_futura = ultima_fecha + timedelta(days=30 * i)
            # Predicción simple: promedio ± 10%
            prediccion = float(promedio) * (1 + (i * 0.02))  # Crecimiento del 2% por período
            predicciones.append(
                {
                    "periodo": fecha_futura.strftime("%Y-%m"),
                    "valor": round(prediccion, 2),
                    "lower": round(prediccion * 0.9, 2),
                    "upper": round(prediccion * 1.1, 2),
                }
            )

        return {
            "tipo_cuenta": tipo_cuenta,
            "periodos": periodos,
            "historical": historico,
            "predictions": predicciones,
            "promedio": float(promedio),
        }

    def _generate_flujo_predictions(self, fecha_inicio: date, periodos: int) -> dict[str, Any]:
        """
        Genera predicciones de flujo de caja (Ingresos - Costos - Gastos).

        Args:
            fecha_inicio: Fecha desde la cual obtener datos históricos
            periodos: Número de períodos futuros a predecir

        Returns:
            dict con predicciones de flujo
        """
        # Obtener ingresos
        ingresos_trans = (
            EmpresaTransaccion.objects.filter(
                asiento__empresa=self.empresa,
                asiento__fecha__gte=fecha_inicio,
                asiento__estado=EstadoAsiento.CONFIRMADO,
                cuenta__tipo=TipoCuenta.INGRESO,
            )
            .values("asiento__fecha")
            .annotate(total=Sum("haber"))
            .order_by("asiento__fecha")
        )

        # Obtener gastos
        gastos_trans = (
            EmpresaTransaccion.objects.filter(
                asiento__empresa=self.empresa,
                asiento__fecha__gte=fecha_inicio,
                asiento__estado=EstadoAsiento.CONFIRMADO,
                cuenta__tipo=TipoCuenta.GASTO,
            )
            .values("asiento__fecha")
            .annotate(total=Sum("debe"))
            .order_by("asiento__fecha")
        )

        # Obtener costos
        costos_trans = (
            EmpresaTransaccion.objects.filter(
                asiento__empresa=self.empresa,
                asiento__fecha__gte=fecha_inicio,
                asiento__estado=EstadoAsiento.CONFIRMADO,
                cuenta__tipo=TipoCuenta.COSTO,
            )
            .values("asiento__fecha")
            .annotate(total=Sum("debe"))
            .order_by("asiento__fecha")
        )

        # Agrupar ingresos por mes
        ingresos_mensuales = {}
        for trans in ingresos_trans:
            mes = trans["asiento__fecha"].strftime("%Y-%m")
            if mes not in ingresos_mensuales:
                ingresos_mensuales[mes] = Decimal("0")
            ingresos_mensuales[mes] += trans["total"]

        # Agrupar gastos por mes
        gastos_mensuales = {}
        for trans in gastos_trans:
            mes = trans["asiento__fecha"].strftime("%Y-%m")
            if mes not in gastos_mensuales:
                gastos_mensuales[mes] = Decimal("0")
            gastos_mensuales[mes] += trans["total"]

        # Agrupar costos por mes
        costos_mensuales = {}
        for trans in costos_trans:
            mes = trans["asiento__fecha"].strftime("%Y-%m")
            if mes not in costos_mensuales:
                costos_mensuales[mes] = Decimal("0")
            costos_mensuales[mes] += trans["total"]

        # Calcular flujo por mes (Ingresos - Costos - Gastos)
        todos_meses = set(
            list(ingresos_mensuales.keys())
            + list(gastos_mensuales.keys())
            + list(costos_mensuales.keys())
        )
        flujo_mensual = {}
        for mes in todos_meses:
            ingreso = ingresos_mensuales.get(mes, Decimal("0"))
            gasto = gastos_mensuales.get(mes, Decimal("0"))
            costo = costos_mensuales.get(mes, Decimal("0"))
            flujo_mensual[mes] = ingreso - costo - gasto

        # Calcular promedio de flujo
        if flujo_mensual:
            promedio_flujo = sum(flujo_mensual.values()) / len(flujo_mensual)
        else:
            promedio_flujo = Decimal("0")

        # Generar histórico
        historico = [
            {"periodo": mes, "valor": float(valor)} for mes, valor in sorted(flujo_mensual.items())
        ]

        # Generar predicciones futuras
        ultima_fecha = date.today()
        predicciones = []
        for i in range(1, periodos + 1):
            fecha_futura = ultima_fecha + timedelta(days=30 * i)
            # Predicción: promedio con tendencia del 2% por período
            prediccion = float(promedio_flujo) * (1 + (i * 0.02))
            predicciones.append(
                {
                    "periodo": fecha_futura.strftime("%Y-%m"),
                    "valor": round(prediccion, 2),
                    "lower": round(prediccion * 0.9, 2),
                    "upper": round(prediccion * 1.1, 2),
                }
            )

        return {
            "tipo_cuenta": "FLUJO",
            "periodos": periodos,
            "historical": historico,
            "predictions": predicciones,
            "promedio": float(promedio_flujo),
        }

    def detect_anomalies(self, meses: int = 12, umbral: float = 2.0) -> list[dict[str, Any]]:
        """
        Detecta anomalías en transacciones usando desviación estándar simple.

        Args:
            meses: Meses a analizar
            umbral: Desviaciones estándar para considerar anomalía

        Returns:
            Lista de anomalías detectadas
        """
        fecha_inicio = date.today() - timedelta(days=30 * meses)

        # Obtener todas las transacciones
        transacciones = EmpresaTransaccion.objects.filter(
            asiento__empresa=self.empresa,
            asiento__fecha__gte=fecha_inicio,
            asiento__estado=EstadoAsiento.CONFIRMADO,
        ).select_related("cuenta", "asiento", "tercero")

        # Calcular estadísticas por tipo de cuenta
        stats_por_tipo = {}
        valores_por_tipo = {}

        for trans in transacciones:
            if not trans.cuenta:
                continue

            tipo = trans.cuenta.tipo
            monto = trans.debe if trans.debe > 0 else trans.haber

            if tipo not in valores_por_tipo:
                valores_por_tipo[tipo] = []
            valores_por_tipo[tipo].append(float(monto))

        # Calcular promedio y desviación estándar
        import statistics

        for tipo, valores in valores_por_tipo.items():
            if len(valores) > 1:
                stats_por_tipo[tipo] = {
                    "promedio": statistics.mean(valores),
                    "desv_std": statistics.stdev(valores),
                }

        # Detectar anomalías
        anomalias = []
        for trans in transacciones:
            if not trans.cuenta or trans.cuenta.tipo not in stats_por_tipo:
                continue

            monto = float(trans.debe if trans.debe > 0 else trans.haber)
            stats = stats_por_tipo[trans.cuenta.tipo]

            # Calcular Z-score
            if stats["desv_std"] > 0:
                z_score = abs((monto - stats["promedio"]) / stats["desv_std"])

                if z_score > umbral:
                    severidad = "alta" if z_score > 3 else "media"
                    anomalias.append(
                        {
                            "asiento_id": trans.asiento.id,
                            "numero_asiento": trans.asiento.numero_asiento,
                            "fecha": trans.asiento.fecha.strftime("%Y-%m-%d"),
                            "cuenta_codigo": trans.cuenta.codigo,
                            "cuenta_descripcion": trans.cuenta.descripcion,
                            "monto": monto,
                            "z_score": round(z_score, 2),
                            "severidad": severidad,
                            "descripcion": trans.asiento.descripcion_general,
                            "tercero": trans.tercero.nombre if trans.tercero else None,
                        }
                    )

        # Ordenar por z_score descendente
        anomalias.sort(key=lambda x: x["z_score"], reverse=True)

        return anomalias[:50]  # Limitar a 50 anomalías

    def semantic_search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Búsqueda inteligente simple y rápida por descripción y código.
        Optimizada para velocidad y simplicidad.

        Args:
            query: Texto de búsqueda
            limit: Número máximo de resultados

        Returns:
            Lista de cuentas coincidentes con score de relevancia
        """
        query_lower = query.lower()

        # Búsqueda optimizada en una sola consulta
        cuentas = (
            EmpresaPlanCuenta.objects.filter(
                empresa=self.empresa,
                activa=True,
            )
            .filter(Q(descripcion__icontains=query) | Q(codigo__icontains=query))
            .select_related("empresa")[: limit * 2]  # Traer más para rankear mejor
        )

        resultados = []
        for cuenta in cuentas:
            # Score inteligente basado en coincidencia
            desc_lower = cuenta.descripcion.lower()
            codigo_lower = cuenta.codigo.lower()

            score = 0.0

            # Coincidencia exacta en código (más importante)
            if query_lower == codigo_lower:
                score = 1.0
            # Código contiene búsqueda
            elif query_lower in codigo_lower:
                score = 0.95
            # Coincidencia exacta en descripción
            elif query_lower == desc_lower:
                score = 0.9
            # Descripción empieza con búsqueda
            elif desc_lower.startswith(query_lower):
                score = 0.85
            # Descripción contiene búsqueda
            elif query_lower in desc_lower:
                # Más score si está al principio
                pos = desc_lower.find(query_lower)
                score = 0.8 - (pos / len(desc_lower)) * 0.2
            else:
                score = 0.5  # Coincidencia parcial por SQL LIKE

            resultados.append(
                {
                    "id": cuenta.id,
                    "codigo": cuenta.codigo,
                    "descripcion": cuenta.descripcion,
                    "tipo": cuenta.tipo,
                    "naturaleza": cuenta.naturaleza,
                    "score": score,
                }
            )

        # Ordenar por score descendente
        resultados.sort(key=lambda x: x["score"], reverse=True)

        return resultados[:limit]

    def _get_saldo_por_tipo(self, tipo: TipoCuenta) -> Decimal:
        """
        Calcula el saldo total para un tipo de cuenta.

        Args:
            tipo: Tipo de cuenta

        Returns:
            Saldo total (siempre positivo)
        """
        transacciones = EmpresaTransaccion.objects.filter(
            asiento__empresa=self.empresa,
            asiento__estado=EstadoAsiento.CONFIRMADO,
            cuenta__tipo=tipo,
        ).aggregate(
            total_debe=Sum("debe"),
            total_haber=Sum("haber"),
        )

        total_debe = transacciones["total_debe"] or Decimal("0")
        total_haber = transacciones["total_haber"] or Decimal("0")

        # Para activos y gastos: debe - haber (naturaleza deudora)
        # Para pasivos, patrimonio e ingresos: haber - debe (naturaleza acreedora)
        # Retornar valor absoluto para evitar negativos
        if tipo in [TipoCuenta.ACTIVO, TipoCuenta.GASTO]:
            return abs(total_debe - total_haber)
        else:
            return abs(total_haber - total_debe)
