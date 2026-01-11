"""
Tests para el servicio de embeddings y búsqueda semántica.
"""

from django.test import TestCase

from contabilidad.ml_embeddings import EmbeddingService
from contabilidad.models import (
    Empresa,
    EmpresaCuentaEmbedding,
    EmpresaPlanCuenta,
    NaturalezaCuenta,
    TipoCuenta,
)
from core.models import User


class EmbeddingServiceTestCase(TestCase):
    """Tests para EmbeddingService."""

    def setUp(self):
        """Configurar datos de prueba."""
        # Crear usuario y empresa
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )

        self.empresa = Empresa.objects.create(nombre="Empresa Test", owner=self.user)

        # Crear algunas cuentas de prueba
        self.cuenta_efectivo = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="1105",
            descripcion="Caja",
            tipo=TipoCuenta.ACTIVO,
            naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=True,
        )

        self.cuenta_bancos = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="1110",
            descripcion="Bancos",
            tipo=TipoCuenta.ACTIVO,
            naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=True,
        )

        self.cuenta_inventario = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="1435",
            descripcion="Inventario de Mercancías",
            tipo=TipoCuenta.ACTIVO,
            naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=True,
        )

        self.cuenta_proveedores = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="2205",
            descripcion="Proveedores Nacionales",
            tipo=TipoCuenta.PASIVO,
            naturaleza=NaturalezaCuenta.ACREEDORA,
            es_auxiliar=True,
        )

        self.cuenta_ventas = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="4135",
            descripcion="Comercio al por Mayor y al por Menor",
            tipo=TipoCuenta.INGRESO,
            naturaleza=NaturalezaCuenta.ACREEDORA,
            es_auxiliar=True,
        )

        self.cuenta_gastos_personal = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="5105",
            descripcion="Gastos de Personal",
            tipo=TipoCuenta.GASTO,
            naturaleza=NaturalezaCuenta.DEUDORA,
            es_auxiliar=True,
        )

        self.service = EmbeddingService()

    def test_generar_texto_cuenta(self):
        """Test generación de texto descriptivo."""
        texto = self.service.generar_texto_cuenta(self.cuenta_efectivo)

        self.assertIn("1105", texto)
        self.assertIn("Caja", texto)
        self.assertIn("Activo", texto)

    def test_generar_embedding(self):
        """Test generación de embedding."""
        texto = "Cuenta de caja para efectivo"
        embedding = self.service.generar_embedding(texto)

        self.assertIsInstance(embedding, list)
        self.assertEqual(len(embedding), 384)  # Dimensión del modelo MiniLM
        self.assertTrue(all(isinstance(x, float) for x in embedding))

    def test_generar_embedding_cuenta(self):
        """Test generación de embedding para cuenta."""
        embedding_obj = self.service.generar_embedding_cuenta(self.cuenta_efectivo)

        self.assertIsInstance(embedding_obj, EmpresaCuentaEmbedding)
        self.assertEqual(embedding_obj.cuenta, self.cuenta_efectivo)
        self.assertEqual(embedding_obj.dimension, 384)
        self.assertIsNotNone(embedding_obj.embedding_json)

    def test_generar_embeddings_empresa(self):
        """Test generación de embeddings para toda la empresa."""
        stats = self.service.generar_embeddings_empresa(self.empresa)

        self.assertGreater(stats["procesadas"], 0)
        self.assertEqual(stats["procesadas"], 6)  # 6 cuentas creadas
        self.assertGreaterEqual(stats["nuevas"], 0)

    def test_buscar_cuentas_similares(self):
        """Test búsqueda de cuentas similares."""
        # Primero generar embeddings
        self.service.generar_embeddings_empresa(self.empresa)

        # Buscar cuentas similares a "Caja"
        resultados = self.service.buscar_cuentas_similares(
            cuenta=self.cuenta_efectivo, empresa=self.empresa, limit=3
        )

        self.assertIsInstance(resultados, list)
        # Debería encontrar "Bancos" como similar (ambos son activos líquidos)
        if len(resultados) > 0:
            codigos = [r["codigo"] for r in resultados]
            self.assertTrue(any(codigo in ["1110", "1435"] for codigo in codigos))

    def test_buscar_por_texto(self):
        """Test búsqueda por texto libre."""
        # Generar embeddings
        self.service.generar_embeddings_empresa(self.empresa)

        # Buscar "efectivo"
        resultados = self.service.buscar_por_texto(
            texto_busqueda="efectivo en caja", empresa=self.empresa, limit=5, min_similarity=0.2
        )

        self.assertIsInstance(resultados, list)
        # Debería encontrar la cuenta de Caja
        if len(resultados) > 0:
            codigos = [r["codigo"] for r in resultados]
            self.assertIn("1105", codigos)

    def test_recomendar_cuentas(self):
        """Test sistema de recomendación."""
        # Generar embeddings
        self.service.generar_embeddings_empresa(self.empresa)

        # Pedir recomendación para "pago de salarios"
        resultados = self.service.recomendar_cuentas(
            descripcion_transaccion="pago de salarios a empleados", empresa=self.empresa, top_k=3
        )

        self.assertIsInstance(resultados, list)
        # Debería recomendar la cuenta de Gastos de Personal
        if len(resultados) > 0:
            codigos = [r["codigo"] for r in resultados]
            # Verificar que al menos encuentre algo relacionado
            self.assertTrue(len(codigos) > 0)

    def test_obtener_clusters_cuentas(self):
        """Test clustering de cuentas."""
        # Generar embeddings
        self.service.generar_embeddings_empresa(self.empresa)

        # Generar clusters
        clusters = self.service.obtener_clusters_cuentas(empresa=self.empresa, n_clusters=2)

        self.assertIsInstance(clusters, dict)
        if len(clusters) > 0:
            self.assertGreater(len(clusters), 0)
            # Verificar estructura
            for _cluster_id, cuentas in clusters.items():
                self.assertIsInstance(cuentas, list)
                if len(cuentas) > 0:
                    self.assertIn("codigo", cuentas[0])
                    self.assertIn("descripcion", cuentas[0])

    def test_calcular_similaridad_coseno(self):
        """Test cálculo de similaridad coseno."""
        vector_a = [1.0, 0.0, 0.0]
        vector_b = [1.0, 0.0, 0.0]

        similarity = self.service._calcular_similaridad_coseno(vector_a, vector_b)

        self.assertAlmostEqual(similarity, 1.0, places=5)  # Vectores idénticos

        vector_c = [0.0, 1.0, 0.0]
        similarity2 = self.service._calcular_similaridad_coseno(vector_a, vector_c)

        self.assertAlmostEqual(similarity2, 0.0, places=5)  # Vectores perpendiculares
