"""
Tests para el servicio de detección de anomalías.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from contabilidad.ml_anomalies import AnomalyService
from contabilidad.models import (
    AnomaliaDetectada,
    Empresa,
    EmpresaAsiento,
    EmpresaPlanCuenta,
    EmpresaTransaccion,
    PlanDeCuentas,
)
from core.models import Grupo

User = get_user_model()


class AnomalyServiceTest(TestCase):
    """Tests para el servicio de detección de anomalías."""

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

        # Crear plan de cuentas
        self._crear_plan_cuentas()

        # Crear datos de prueba
        self._crear_datos_normales()
        self._crear_datos_anomalos()

    def _crear_plan_cuentas(self):
        """Crea un plan de cuentas básico."""
        # Caja
        self.cuenta_caja = PlanDeCuentas.objects.create(
            codigo="1105",
            descripcion="Caja",
            tipo="Activo",
            naturaleza="Deudora",
            nivel=4,
            codigo_padre="1100",
        )
        self.empresa_caja = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="1105",
            descripcion="Caja",
            tipo="Activo",
            naturaleza="Deudora",
        )

        # Bancos
        self.cuenta_bancos = PlanDeCuentas.objects.create(
            codigo="1110",
            descripcion="Bancos",
            tipo="Activo",
            naturaleza="Deudora",
            nivel=4,
            codigo_padre="1100",
        )
        self.empresa_bancos = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="1110",
            descripcion="Bancos",
            tipo="Activo",
            naturaleza="Deudora",
        )

        # Ventas
        self.cuenta_ventas = PlanDeCuentas.objects.create(
            codigo="4135",
            descripcion="Ventas",
            tipo="Ingreso",
            naturaleza="Acreedora",
            nivel=4,
            codigo_padre="4000",
        )
        self.empresa_ventas = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="4135",
            descripcion="Ventas",
            tipo="Ingreso",
            naturaleza="Acreedora",
        )

        # Gastos
        self.cuenta_gastos = PlanDeCuentas.objects.create(
            codigo="5195",
            descripcion="Gastos Diversos",
            tipo="Gasto",
            naturaleza="Deudora",
            nivel=4,
            codigo_padre="5000",
        )
        self.empresa_gastos = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="5195",
            descripcion="Gastos Diversos",
            tipo="Gasto",
            naturaleza="Deudora",
        )

    def _crear_datos_normales(self):
        """Crea transacciones normales."""
        fecha_inicio = date.today() - timedelta(days=90)

        for i in range(20):
            fecha = fecha_inicio + timedelta(days=i * 3)

            # Asiento normal de venta
            asiento = EmpresaAsiento.objects.create(
                empresa=self.empresa,
                numero_asiento=1000 + i,
                fecha=fecha,
                descripcion_general=f"Venta #{i}",
                estado="Confirmado",
                anulado=False,
                creado_por=self.user,
            )

            # Débito bancos
            EmpresaTransaccion.objects.create(
                asiento=asiento,
                cuenta=self.empresa_bancos,
                detalle_linea=f"Cobro venta #{i}",
                debe=Decimal("1000.00") + Decimal(i * 50),
                haber=Decimal("0.00"),
                creado_por=self.user,
            )

            # Crédito ventas
            EmpresaTransaccion.objects.create(
                asiento=asiento,
                cuenta=self.empresa_ventas,
                detalle_linea=f"Venta #{i}",
                debe=Decimal("0.00"),
                haber=Decimal("1000.00") + Decimal(i * 50),
                creado_por=self.user,
            )

    def _crear_datos_anomalos(self):
        """Crea transacciones con anomalías."""
        fecha_base = date.today() - timedelta(days=30)

        # 1. Anomalía de MONTO: transacción con monto muy alto
        asiento_monto = EmpresaAsiento.objects.create(
            empresa=self.empresa,
            numero_asiento=2000,
            fecha=fecha_base,
            descripcion_general="Venta anómala",
            estado="Confirmado",
            anulado=False,
            creado_por=self.user,
        )

        EmpresaTransaccion.objects.create(
            asiento=asiento_monto,
            cuenta=self.empresa_bancos,
            detalle_linea="Monto anómalo",
            debe=Decimal("100000.00"),  # Mucho más alto que el promedio
            haber=Decimal("0.00"),
            creado_por=self.user,
        )

        EmpresaTransaccion.objects.create(
            asiento=asiento_monto,
            cuenta=self.empresa_ventas,
            detalle_linea="Venta anómala",
            debe=Decimal("0.00"),
            haber=Decimal("100000.00"),
            creado_por=self.user,
        )

        # 2. Anomalía de PATRÓN: números redondos
        asiento_redondo = EmpresaAsiento.objects.create(
            empresa=self.empresa,
            numero_asiento=2001,
            fecha=fecha_base + timedelta(days=1),
            descripcion_general="Número redondo",
            estado="Confirmado",
            anulado=False,
            creado_por=self.user,
        )

        EmpresaTransaccion.objects.create(
            asiento=asiento_redondo,
            cuenta=self.empresa_bancos,
            detalle_linea="Monto redondo",
            debe=Decimal("50000.00"),  # Múltiplo exacto de 1000
            haber=Decimal("0.00"),
            creado_por=self.user,
        )

        EmpresaTransaccion.objects.create(
            asiento=asiento_redondo,
            cuenta=self.empresa_ventas,
            detalle_linea="Venta redonda",
            debe=Decimal("0.00"),
            haber=Decimal("50000.00"),
            creado_por=self.user,
        )

        # 3. Anomalía de PATRÓN: duplicados
        for _ in range(2):
            asiento_dup = EmpresaAsiento.objects.create(
                empresa=self.empresa,
                numero_asiento=2002 + _,
                fecha=fecha_base + timedelta(days=2),
                descripcion_general="Duplicado",
                estado="Confirmado",
                anulado=False,
                creado_por=self.user,
            )

            # Mismo monto, misma cuenta, mismo día
            EmpresaTransaccion.objects.create(
                asiento=asiento_dup,
                cuenta=self.empresa_gastos,
                detalle_linea="Gasto duplicado",
                debe=Decimal("500.00"),
                haber=Decimal("0.00"),
                creado_por=self.user,
            )

            EmpresaTransaccion.objects.create(
                asiento=asiento_dup,
                cuenta=self.empresa_caja,
                detalle_linea="Pago duplicado",
                debe=Decimal("0.00"),
                haber=Decimal("500.00"),
                creado_por=self.user,
            )

    def test_detectar_anomalias_monto(self):
        """Test: detectar anomalías de monto con Isolation Forest."""
        service = AnomalyService(self.empresa)

        resultado = service.detectar_anomalias_monto(
            dias_historicos=180, contamination=0.1, guardar=False
        )

        # Verificar éxito
        self.assertTrue(resultado["success"])

        # Verificar que se detectaron anomalías
        self.assertGreater(resultado["anomalias_detectadas"], 0)

        # Verificar estructura de respuesta
        self.assertIn("total_transacciones", resultado)
        self.assertIn("porcentaje_anomalias", resultado)
        self.assertIn("estadisticas", resultado)
        self.assertIn("anomalias_detalle", resultado)

    def test_detectar_anomalias_frecuencia(self):
        """Test: detectar anomalías de frecuencia."""
        service = AnomalyService(self.empresa)

        resultado = service.detectar_anomalias_frecuencia(
            dias_historicos=180, umbral_desviaciones=2.0, guardar=False
        )

        # Verificar éxito
        self.assertTrue(resultado["success"])

        # Verificar estructura
        self.assertIn("anomalias_detectadas", resultado)
        self.assertIn("total_cuentas_analizadas", resultado)
        self.assertIn("estadisticas", resultado)

    def test_detectar_anomalias_temporales(self):
        """Test: detectar anomalías temporales."""
        service = AnomalyService(self.empresa)

        resultado = service.detectar_anomalias_temporales(dias_historicos=180, guardar=False)

        # Verificar éxito
        self.assertTrue(resultado["success"])

        # Verificar estructura
        self.assertIn("anomalias_detectadas", resultado)
        self.assertIn("total_asientos_analizados", resultado)

    def test_detectar_anomalias_patrones(self):
        """Test: detectar anomalías de patrón."""
        service = AnomalyService(self.empresa)

        resultado = service.detectar_anomalias_patrones(dias_historicos=180, guardar=False)

        # Verificar éxito
        self.assertTrue(resultado["success"])

        # Debería detectar números redondos y duplicados
        self.assertGreater(resultado["anomalias_detectadas"], 0)

        # Verificar estructura
        self.assertIn("anomalias_detalle", resultado)

    def test_detectar_todas_anomalias(self):
        """Test: detectar todos los tipos de anomalías."""
        service = AnomalyService(self.empresa)

        resultado = service.detectar_todas_anomalias(dias_historicos=180, guardar=False)

        # Verificar éxito general
        self.assertTrue(resultado["success"])

        # Verificar que se ejecutaron todos los tipos
        self.assertIn("resultados_por_tipo", resultado)
        resultados = resultado["resultados_por_tipo"]

        self.assertIn("monto", resultados)
        self.assertIn("frecuencia", resultados)
        self.assertIn("temporal", resultados)
        self.assertIn("patron", resultados)

        # Verificar totales
        self.assertIn("total_anomalias_detectadas", resultado)
        self.assertGreater(resultado["total_anomalias_detectadas"], 0)

    def test_guardar_anomalias_monto(self):
        """Test: guardar anomalías de monto en la base de datos."""
        service = AnomalyService(self.empresa)

        # Limpiar anomalías previas
        AnomaliaDetectada.objects.filter(empresa=self.empresa).delete()

        resultado = service.detectar_anomalias_monto(
            dias_historicos=180, contamination=0.1, guardar=True
        )

        # Verificar que se guardaron
        self.assertTrue(resultado["success"])
        self.assertIsNotNone(resultado["anomalias_guardadas"])
        self.assertGreater(resultado["anomalias_guardadas"], 0)

        # Verificar en la base de datos
        anomalias_bd = AnomaliaDetectada.objects.filter(empresa=self.empresa, tipo_anomalia="MONTO")
        self.assertGreater(anomalias_bd.count(), 0)

        # Verificar campos de la primera anomalía
        primera = anomalias_bd.first()
        self.assertEqual(primera.algoritmo_usado, "IsolationForest")
        self.assertIsNotNone(primera.transaccion_id)
        self.assertIsNotNone(primera.score_anomalia)
        self.assertIn(primera.severidad, ["BAJA", "MEDIA", "ALTA", "CRITICA"])

    def test_obtener_anomalias_sin_revisar(self):
        """Test: obtener anomalías sin revisar."""
        service = AnomalyService(self.empresa)

        # Crear algunas anomalías
        AnomaliaDetectada.objects.filter(empresa=self.empresa).delete()
        service.detectar_anomalias_monto(dias_historicos=180, guardar=True)

        # Obtener sin revisar
        anomalias = service.obtener_anomalias_sin_revisar(limit=10)

        # Verificar que se obtuvieron
        self.assertGreater(len(anomalias), 0)

        # Todas deben estar sin revisar
        for anomalia in anomalias:
            self.assertFalse(anomalia.revisada)

    def test_marcar_como_revisada(self):
        """Test: marcar anomalía como revisada."""
        service = AnomalyService(self.empresa)

        # Crear anomalía
        AnomaliaDetectada.objects.filter(empresa=self.empresa).delete()
        service.detectar_anomalias_monto(dias_historicos=180, guardar=True)

        anomalia = AnomaliaDetectada.objects.filter(empresa=self.empresa).first()
        self.assertIsNotNone(anomalia)

        # Marcar como revisada
        exito = service.marcar_como_revisada(
            anomalia_id=anomalia.id,
            es_falso_positivo=False,
            notas="Revisado en test",
            usuario=self.user,
        )

        self.assertTrue(exito)

        # Verificar que se marcó
        anomalia.refresh_from_db()
        self.assertTrue(anomalia.revisada)
        self.assertFalse(anomalia.es_falso_positivo)
        self.assertEqual(anomalia.notas_revision, "Revisado en test")
        self.assertEqual(anomalia.revisada_por, self.user)
        self.assertIsNotNone(anomalia.fecha_revision)

    def test_marcar_como_falso_positivo(self):
        """Test: marcar anomalía como falso positivo."""
        service = AnomalyService(self.empresa)

        # Crear anomalía
        AnomaliaDetectada.objects.filter(empresa=self.empresa).delete()
        service.detectar_anomalias_monto(dias_historicos=180, guardar=True)

        anomalia = AnomaliaDetectada.objects.filter(empresa=self.empresa).first()

        # Marcar como falso positivo
        exito = service.marcar_como_revisada(
            anomalia_id=anomalia.id,
            es_falso_positivo=True,
            notas="Es normal para esta empresa",
        )

        self.assertTrue(exito)

        # Verificar
        anomalia.refresh_from_db()
        self.assertTrue(anomalia.revisada)
        self.assertTrue(anomalia.es_falso_positivo)

    def test_datos_insuficientes(self):
        """Test: error cuando no hay suficientes datos."""
        # Crear empresa vacía
        empresa_vacia = Empresa.objects.create(
            nombre="Empresa Vacía",
            nit="999999999",
            grupo=self.grupo,
            creado_por=self.user,
        )

        service = AnomalyService(empresa_vacia)

        resultado = service.detectar_anomalias_monto(dias_historicos=180, guardar=False)

        # Debe fallar por falta de datos
        self.assertFalse(resultado["success"])
        self.assertIn("error", resultado)

    def test_estadisticas_anomalias(self):
        """Test: cálculo de estadísticas de anomalías."""
        service = AnomalyService(self.empresa)

        resultado = service.detectar_anomalias_monto(
            dias_historicos=180, contamination=0.1, guardar=False
        )

        if resultado["success"] and resultado["anomalias_detectadas"] > 0:
            stats = resultado["estadisticas"]

            # Verificar que existen las métricas
            self.assertIn("monto_promedio_normal", stats)
            self.assertIn("monto_promedio_anomalo", stats)
            self.assertIn("score_promedio", stats)

            # Los montos anómalos deberían ser diferentes a los normales
            self.assertIsInstance(stats["monto_promedio_normal"], float)
            self.assertIsInstance(stats["monto_promedio_anomalo"], float)
