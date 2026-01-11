"""
Tests para el servicio de predicciones con Prophet.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from contabilidad.ml_predictions import PredictionService
from contabilidad.models import (
    Empresa,
    EmpresaAsiento,
    EmpresaPlanCuenta,
    EmpresaTransaccion,
    PlanDeCuentas,
    PrediccionFinanciera,
)
from core.models import Grupo

User = get_user_model()


class PredictionServiceTest(TestCase):
    """Tests para el servicio de predicciones."""

    def setUp(self):
        """Configura el entorno de pruebas."""
        # Crear usuario y grupo
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="test123"
        )
        self.grupo = Grupo.objects.create(nombre="Test Grupo", creado_por=self.user)
        self.grupo.miembros.add(self.user)

        # Crear empresa
        self.empresa = Empresa.objects.create(
            nombre="Test Empresa S.A.",
            nit="123456789",
            grupo=self.grupo,
            creado_por=self.user,
        )

        # Crear plan de cuentas con cuentas necesarias
        self._crear_plan_cuentas()

        # Crear datos históricos (últimos 12 meses)
        self._crear_datos_historicos()

    def _crear_plan_cuentas(self):
        """Crea un plan de cuentas básico."""
        # Activos
        self.cuenta_caja = PlanDeCuentas.objects.create(
            codigo="1105",
            descripcion="Caja",
            tipo="A",
            naturaleza="D",
            nivel=4,
            codigo_padre="1100",
        )
        self.empresa_caja = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa, cuenta_plan=self.cuenta_caja
        )

        self.cuenta_bancos = PlanDeCuentas.objects.create(
            codigo="1110",
            descripcion="Bancos",
            tipo="A",
            naturaleza="D",
            nivel=4,
            codigo_padre="1100",
        )
        self.empresa_bancos = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa, cuenta_plan=self.cuenta_bancos
        )

        # Ingresos
        self.cuenta_ventas = PlanDeCuentas.objects.create(
            codigo="4135",
            descripcion="Comercio al por mayor y al por menor",
            tipo="I",
            naturaleza="C",
            nivel=4,
            codigo_padre="4000",
        )
        self.empresa_ventas = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa, cuenta_plan=self.cuenta_ventas
        )

        # Gastos
        self.cuenta_gastos = PlanDeCuentas.objects.create(
            codigo="5195",
            descripcion="Diversos",
            tipo="G",
            naturaleza="D",
            nivel=4,
            codigo_padre="5000",
        )
        self.empresa_gastos = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa, cuenta_plan=self.cuenta_gastos
        )

        # Costos
        self.cuenta_costos = PlanDeCuentas.objects.create(
            codigo="6135",
            descripcion="Comercio al por mayor y al por menor",
            tipo="C",
            naturaleza="D",
            nivel=4,
            codigo_padre="6000",
        )
        self.empresa_costos = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa, cuenta_plan=self.cuenta_costos
        )

    def _crear_datos_historicos(self):
        """Crea datos históricos de transacciones para los últimos 12 meses."""
        fecha_inicio = date.today() - timedelta(days=365)

        # Crear asientos mensuales con patrón de crecimiento
        for mes in range(12):
            fecha = fecha_inicio + timedelta(days=30 * mes)

            # Base con tendencia creciente
            base_ventas = 100000 + (mes * 5000)  # Crecimiento lineal
            base_gastos = 30000 + (mes * 1000)
            base_costos = 50000 + (mes * 2000)

            # Crear varios asientos en el mes
            for dia in [5, 15, 25]:
                fecha_asiento = fecha + timedelta(days=dia)

                # Asiento de ventas
                asiento_ventas = EmpresaAsiento.objects.create(
                    empresa_cuenta=self.empresa_ventas,
                    numero_asiento=f"{fecha_asiento.year}{fecha_asiento.month:02d}{dia:02d}",
                    fecha=fecha_asiento,
                    tipo="N",
                    descripcion=f"Ventas del día {dia}",
                )

                # Débito a bancos
                EmpresaTransaccion.objects.create(
                    asiento=asiento_ventas,
                    empresa_cuenta=self.empresa_bancos,
                    tipo_movimiento="D",
                    monto=Decimal(base_ventas / 3),
                )

                # Crédito a ventas
                EmpresaTransaccion.objects.create(
                    asiento=asiento_ventas,
                    empresa_cuenta=self.empresa_ventas,
                    tipo_movimiento="C",
                    monto=Decimal(base_ventas / 3),
                )

                # Asiento de gastos
                asiento_gastos = EmpresaAsiento.objects.create(
                    empresa_cuenta=self.empresa_gastos,
                    numero_asiento=f"{fecha_asiento.year}{fecha_asiento.month:02d}{dia:02d}G",
                    fecha=fecha_asiento,
                    tipo="N",
                    descripcion=f"Gastos del día {dia}",
                )

                # Débito a gastos
                EmpresaTransaccion.objects.create(
                    asiento=asiento_gastos,
                    empresa_cuenta=self.empresa_gastos,
                    tipo_movimiento="D",
                    monto=Decimal(base_gastos / 3),
                )

                # Crédito a bancos
                EmpresaTransaccion.objects.create(
                    asiento=asiento_gastos,
                    empresa_cuenta=self.empresa_bancos,
                    tipo_movimiento="C",
                    monto=Decimal(base_gastos / 3),
                )

                # Asiento de costos
                asiento_costos = EmpresaAsiento.objects.create(
                    empresa_cuenta=self.empresa_costos,
                    numero_asiento=f"{fecha_asiento.year}{fecha_asiento.month:02d}{dia:02d}C",
                    fecha=fecha_asiento,
                    tipo="N",
                    descripcion=f"Costos del día {dia}",
                )

                # Débito a costos
                EmpresaTransaccion.objects.create(
                    asiento=asiento_costos,
                    empresa_cuenta=self.empresa_costos,
                    tipo_movimiento="D",
                    monto=Decimal(base_costos / 3),
                )

                # Crédito a bancos
                EmpresaTransaccion.objects.create(
                    asiento=asiento_costos,
                    empresa_cuenta=self.empresa_bancos,
                    tipo_movimiento="C",
                    monto=Decimal(base_costos / 3),
                )

    def test_obtener_serie_temporal_ingresos(self):
        """Test: obtener serie temporal de ingresos."""
        service = PredictionService(self.empresa)

        fecha_inicio = date.today() - timedelta(days=365)
        fecha_fin = date.today()

        df = service.obtener_serie_temporal("INGR", fecha_inicio, fecha_fin)

        # Verificar que el DataFrame tiene las columnas correctas
        self.assertIn("ds", df.columns)
        self.assertIn("y", df.columns)

        # Verificar que hay datos
        self.assertGreater(len(df), 0)

        # Verificar que los valores son positivos (naturaleza crédito)
        self.assertTrue((df["y"] >= 0).all())

    def test_obtener_serie_temporal_gastos(self):
        """Test: obtener serie temporal de gastos."""
        service = PredictionService(self.empresa)

        fecha_inicio = date.today() - timedelta(days=365)
        fecha_fin = date.today()

        df = service.obtener_serie_temporal("GAST", fecha_inicio, fecha_fin)

        # Verificar estructura
        self.assertIn("ds", df.columns)
        self.assertIn("y", df.columns)

        # Verificar datos
        self.assertGreater(len(df), 0)
        self.assertTrue((df["y"] >= 0).all())

    def test_obtener_serie_temporal_flujo(self):
        """Test: obtener serie temporal de flujo de efectivo."""
        service = PredictionService(self.empresa)

        fecha_inicio = date.today() - timedelta(days=365)
        fecha_fin = date.today()

        df = service.obtener_serie_temporal("FLUJ", fecha_inicio, fecha_fin)

        # Verificar estructura
        self.assertIn("ds", df.columns)
        self.assertIn("y", df.columns)

        # Verificar que hay datos
        self.assertGreater(len(df), 0)

        # El flujo puede ser positivo o negativo
        self.assertTrue(df["y"].dtype in ["float64", "int64"])

    def test_obtener_serie_temporal_utilidad(self):
        """Test: obtener serie temporal de utilidad."""
        service = PredictionService(self.empresa)

        fecha_inicio = date.today() - timedelta(days=365)
        fecha_fin = date.today()

        df = service.obtener_serie_temporal("UTIL", fecha_inicio, fecha_fin)

        # Verificar estructura
        self.assertIn("ds", df.columns)
        self.assertIn("y", df.columns)

        # Verificar datos
        self.assertGreater(len(df), 0)

    def test_generar_predicciones_ingresos(self):
        """Test: generar predicciones de ingresos."""
        service = PredictionService(self.empresa)

        resultado = service.generar_predicciones(
            tipo_prediccion="INGR",
            dias_historicos=365,
            dias_futuros=30,
            guardar=False,
        )

        # Verificar éxito
        self.assertTrue(resultado["success"])

        # Verificar predicciones
        self.assertIn("predicciones", resultado)
        predicciones = resultado["predicciones"]
        self.assertEqual(len(predicciones), 30)

        # Verificar estructura de predicción
        primera_pred = predicciones[0]
        self.assertIn("ds", primera_pred)
        self.assertIn("yhat", primera_pred)
        self.assertIn("yhat_lower", primera_pred)
        self.assertIn("yhat_upper", primera_pred)

        # Verificar métricas
        self.assertIn("metricas", resultado)
        metricas = resultado["metricas"]
        self.assertIn("mae", metricas)
        self.assertIn("rmse", metricas)
        self.assertIn("mape", metricas)

        # Verificar tendencia
        self.assertIn("tendencia", resultado)

    def test_generar_predicciones_con_guardado(self):
        """Test: generar y guardar predicciones."""
        service = PredictionService(self.empresa)

        # Limpiar predicciones previas
        PrediccionFinanciera.objects.filter(empresa=self.empresa).delete()

        resultado = service.generar_predicciones(
            tipo_prediccion="INGR",
            dias_historicos=365,
            dias_futuros=30,
            guardar=True,
        )

        # Verificar éxito
        self.assertTrue(resultado["success"])

        # Verificar que se guardaron en la base de datos
        predicciones_bd = PrediccionFinanciera.objects.filter(
            empresa=self.empresa, tipo_prediccion="INGR"
        )
        self.assertEqual(predicciones_bd.count(), 30)

        # Verificar campos de la primera predicción
        primera = predicciones_bd.first()
        self.assertEqual(primera.modelo_usado, "PROPHET")
        self.assertIsNotNone(primera.valor_predicho)
        self.assertIsNotNone(primera.limite_inferior)
        self.assertIsNotNone(primera.limite_superior)
        self.assertIsNotNone(primera.confianza)
        self.assertIsNotNone(primera.metricas_modelo)

    def test_generar_todas_predicciones(self):
        """Test: generar todas las predicciones."""
        service = PredictionService(self.empresa)

        # Limpiar predicciones previas
        PrediccionFinanciera.objects.filter(empresa=self.empresa).delete()

        resultados = service.generar_todas_predicciones(dias_historicos=365, dias_futuros=30)

        # Verificar que se generaron los 4 tipos
        self.assertEqual(len(resultados), 4)
        self.assertIn("INGR", resultados)
        self.assertIn("GAST", resultados)
        self.assertIn("FLUJ", resultados)
        self.assertIn("UTIL", resultados)

        # Verificar que al menos algunos fueron exitosos
        exitosos = sum(1 for r in resultados.values() if r.get("success"))
        self.assertGreater(exitosos, 0)

    def test_obtener_predicciones_guardadas(self):
        """Test: obtener predicciones guardadas de la BD."""
        service = PredictionService(self.empresa)

        # Generar y guardar predicciones
        service.generar_predicciones(
            tipo_prediccion="INGR",
            dias_historicos=365,
            dias_futuros=30,
            guardar=True,
        )

        # Obtener predicciones guardadas
        predicciones = service.obtener_predicciones_guardadas("INGR")

        # Verificar que se obtuvieron
        self.assertGreater(len(predicciones), 0)

        # Verificar estructura
        primera = predicciones[0]
        self.assertIsInstance(primera, PrediccionFinanciera)
        self.assertEqual(primera.tipo_prediccion, "INGR")

    def test_datos_insuficientes(self):
        """Test: error cuando no hay suficientes datos históricos."""
        # Crear empresa nueva sin datos
        empresa_vacia = Empresa.objects.create(
            nombre="Empresa Vacía",
            nit="999999999",
            grupo=self.grupo,
            creado_por=self.user,
        )

        service = PredictionService(empresa_vacia)

        resultado = service.generar_predicciones(
            tipo_prediccion="INGR",
            dias_historicos=365,
            dias_futuros=30,
            guardar=False,
        )

        # Debe fallar por falta de datos
        self.assertFalse(resultado["success"])
        self.assertIn("error", resultado)

    def test_metricas_error_calculo(self):
        """Test: cálculo de métricas de error."""
        service = PredictionService(self.empresa)

        # Obtener datos históricos
        fecha_inicio = date.today() - timedelta(days=90)
        fecha_fin = date.today()
        df = service.obtener_serie_temporal("INGR", fecha_inicio, fecha_fin)

        if len(df) >= 30:
            # Predecir
            model, forecast = service.predecir_con_prophet(
                df, periodos=30, intervalo_confianza=0.95
            )

            # Calcular métricas en el conjunto de entrenamiento
            metricas = service._calcular_metricas_error(df, forecast)

            # Verificar que las métricas existen
            self.assertIn("mae", metricas)
            self.assertIn("rmse", metricas)
            self.assertIn("mape", metricas)

            # Verificar que son números válidos
            self.assertIsInstance(metricas["mae"], float)
            self.assertIsInstance(metricas["rmse"], float)
            self.assertIsInstance(metricas["mape"], float)

            # Verificar que son positivos
            self.assertGreaterEqual(metricas["mae"], 0)
            self.assertGreaterEqual(metricas["rmse"], 0)
            self.assertGreaterEqual(metricas["mape"], 0)

    def test_analizar_tendencia_creciente(self):
        """Test: análisis de tendencia creciente."""
        service = PredictionService(self.empresa)

        # Crear predicciones con tendencia creciente
        predicciones = [{"ds": f"2024-01-{i:02d}", "yhat": 1000 + (i * 100)} for i in range(1, 31)]

        tendencia = service._analizar_tendencia(predicciones)

        # Debe detectar crecimiento
        self.assertIn("Creciente", tendencia)
        self.assertIn("%", tendencia)

    def test_analizar_tendencia_decreciente(self):
        """Test: análisis de tendencia decreciente."""
        service = PredictionService(self.empresa)

        # Crear predicciones con tendencia decreciente
        predicciones = [{"ds": f"2024-01-{i:02d}", "yhat": 10000 - (i * 100)} for i in range(1, 31)]

        tendencia = service._analizar_tendencia(predicciones)

        # Debe detectar decrecimiento
        self.assertIn("Decreciente", tendencia)
        self.assertIn("%", tendencia)

    def test_analizar_tendencia_estable(self):
        """Test: análisis de tendencia estable."""
        service = PredictionService(self.empresa)

        # Crear predicciones estables
        predicciones = [{"ds": f"2024-01-{i:02d}", "yhat": 5000} for i in range(1, 31)]

        tendencia = service._analizar_tendencia(predicciones)

        # Debe detectar estabilidad
        self.assertIn("Estable", tendencia)
