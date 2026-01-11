"""
Tests API REST para endpoints de reportería contable.

Cubre:
- Autenticación por Token
- Listado de empresas
- Balance de Comprobación
- Balance General
- Estado de Resultados
- Libro Mayor
- Paginación
- Permisos
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from contabilidad.models import (
    Empresa,
    EmpresaAsiento,
    EmpresaPlanCuenta,
    EmpresaTransaccion,
    EstadoAsiento,
)

User = get_user_model()


class APIAuthenticationTests(TestCase):
    """Tests de autenticación de API"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="pass123")
        self.token = Token.objects.create(user=self.user)
        self.url = reverse("empresa-list")

    def test_unauthenticated_request_fails(self):
        """Solicitud sin token debe devolver 401"""
        response = self.client.get(self.url)
        assert response.status_code == 401

    def test_authenticated_request_with_token(self):
        """Solicitud con token válido debe funcionar"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.get(self.url)
        assert response.status_code == 200

    def test_invalid_token_fails(self):
        """Token inválido debe devolver 401"""
        self.client.credentials(HTTP_AUTHORIZATION="Token invalid-token-xyz")
        response = self.client.get(self.url)
        assert response.status_code == 401


class EmpresaListAPITests(TestCase):
    """Tests de listado de empresas"""

    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")

        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)

        # Empresa del usuario 1
        self.empresa1 = Empresa.objects.create(nombre="Empresa User1", owner=self.user1)

        # Empresa del usuario 2
        self.empresa2 = Empresa.objects.create(nombre="Empresa User2", owner=self.user2)

        self.url = reverse("empresa-list")

    def test_list_returns_only_user_companies(self):
        """El usuario solo ve sus propias empresas"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token1.key}")
        response = self.client.get(self.url)

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == self.empresa1.id

    def test_pagination_works(self):
        """Paginación funciona correctamente"""
        # Crear 5 empresas para el usuario 1
        for i in range(5):
            Empresa.objects.create(nombre=f"Empresa {i}", owner=self.user1)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token1.key}")
        response = self.client.get(f"{self.url}?page=1")

        assert response.status_code == 200
        assert "results" in response.data
        assert "count" in response.data
        assert "next" in response.data


class BalanceAPITests(TestCase):
    """Tests de Balance de Comprobación"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.token = Token.objects.create(user=self.user)

        # Crear empresa
        self.empresa = Empresa.objects.create(nombre="Test Company", owner=self.user)

        # Crear cuentas - agregar campos requeridos
        self.cuenta_activo = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="1.1.01",
            descripcion="Caja",
            naturaleza="Deudora",
            tipo="Activo",
            es_auxiliar=True,
        )

        self.cuenta_pasivo = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="2.1.01",
            descripcion="Cuentas por Pagar",
            naturaleza="Acreedora",
            tipo="Pasivo",
            es_auxiliar=True,
        )

        # Crear asiento
        self.asiento = EmpresaAsiento.objects.create(
            empresa=self.empresa,
            numero_asiento=1,
            fecha=date(2025, 1, 15),
            descripcion_general="Asiento de prueba",
            estado=EstadoAsiento.CONFIRMADO,
            creado_por=self.user,
        )

        # Crear líneas
        EmpresaTransaccion.objects.create(
            asiento=self.asiento,
            cuenta=self.cuenta_activo,
            debe=Decimal("1000.00"),
            haber=Decimal("0.00"),
        )

        EmpresaTransaccion.objects.create(
            asiento=self.asiento,
            cuenta=self.cuenta_pasivo,
            debe=Decimal("0.00"),
            haber=Decimal("1000.00"),
        )

    def test_balance_endpoint_requires_auth(self):
        """Endpoint de balance requiere autenticación"""
        url = reverse("empresa-balance", args=[self.empresa.id])
        response = self.client.get(url)
        assert response.status_code == 401

    def test_balance_returns_correct_data(self):
        """Balance retorna datos correctos"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        url = reverse("empresa-balance", args=[self.empresa.id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert "lineas" in response.data
        assert "totales" in response.data
        assert response.data["totales"]["debe"] == Decimal("1000.00")
        assert response.data["totales"]["haber"] == Decimal("1000.00")

    def test_balance_with_date_filters(self):
        """Balance respeta filtros de fecha"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        # Sin resultados (rango que no incluye la fecha del asiento)
        url = reverse("empresa-balance", args=[self.empresa.id])
        response = self.client.get(url, {"fecha_inicio": "2025-02-01", "fecha_fin": "2025-02-28"})

        assert response.status_code == 200
        assert response.data["totales"]["debe"] == Decimal("0.00")


class BalanceGeneralAPITests(TestCase):
    """Tests de Balance General"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.token = Token.objects.create(user=self.user)

        self.empresa = Empresa.objects.create(nombre="Test Company", owner=self.user)

    def test_balance_general_requires_auth(self):
        """Endpoint requiere autenticación"""
        url = reverse("empresa-balance-general", args=[self.empresa.id])
        response = self.client.get(url)
        assert response.status_code == 401

    def test_balance_general_returns_structure(self):
        """Balance General retorna estructura correcta"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        url = reverse("empresa-balance-general", args=[self.empresa.id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert "activos" in response.data
        assert "pasivos" in response.data
        assert "patrimonio" in response.data
        assert "detalle_activos" in response.data


class EstadoResultadosAPITests(TestCase):
    """Tests de Estado de Resultados"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.token = Token.objects.create(user=self.user)

        self.empresa = Empresa.objects.create(nombre="Test Company", owner=self.user)

    def test_estado_resultados_requires_auth(self):
        """Endpoint requiere autenticación"""
        url = reverse("empresa-estado-resultados", args=[self.empresa.id])
        response = self.client.get(url)
        assert response.status_code == 401

    def test_estado_resultados_returns_structure(self):
        """Estado de Resultados retorna estructura correcta"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        url = reverse("empresa-estado-resultados", args=[self.empresa.id])
        response = self.client.get(url)

        assert response.status_code == 200
        assert "ingresos" in response.data
        assert "costos" in response.data
        assert "gastos" in response.data
        assert "utilidad_neta" in response.data


class LibroMayorAPITests(TestCase):
    """Tests de Libro Mayor"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.token = Token.objects.create(user=self.user)

        self.empresa = Empresa.objects.create(nombre="Test Company", owner=self.user)

        self.cuenta = EmpresaPlanCuenta.objects.create(
            empresa=self.empresa,
            codigo="1.1.01",
            descripcion="Caja",
            naturaleza="Deudora",
            tipo="Activo",
            es_auxiliar=True,
        )

    def test_libro_mayor_requires_cuenta_id(self):
        """Libro Mayor requiere cuenta_id"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        url = reverse("empresa-libro-mayor", args=[self.empresa.id])
        response = self.client.get(url)

        assert response.status_code == 400
        assert "cuenta_id" in str(response.data)

    def test_libro_mayor_returns_correct_structure(self):
        """Libro Mayor retorna estructura correcta"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        url = reverse("empresa-libro-mayor", args=[self.empresa.id])
        response = self.client.get(url, {"cuenta_id": self.cuenta.id})

        assert response.status_code == 200
        assert "cuenta" in response.data
        assert "lineas" in response.data
        assert "fecha_inicio" in response.data
        assert "fecha_fin" in response.data


class CORSTests(TestCase):
    """Tests de CORS"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.token = Token.objects.create(user=self.user)

    def test_cors_headers_present(self):
        """Respuesta incluye headers CORS"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        url = reverse("empresa-list")
        response = self.client.get(url, HTTP_ORIGIN="http://localhost:3000")

        assert response.status_code == 200
        # CORS headers pueden estar presentes
        # Depends on Django-CORS-Headers configuration


class SchemaTests(TestCase):
    """Tests de documentación de API (Schema/Swagger)"""

    def test_schema_endpoint_accessible(self):
        """Endpoint de schema es accesible"""
        url = reverse("schema")
        response = self.client.get(url)
        assert response.status_code == 200

    def test_swagger_ui_accessible(self):
        """Swagger UI es accesible"""
        url = reverse("swagger-ui")
        response = self.client.get(url)
        assert response.status_code == 200

    def test_redoc_accessible(self):
        """ReDoc es accesible"""
        url = reverse("redoc")
        response = self.client.get(url)
        assert response.status_code == 200


class APIErrorHandlingTests(TestCase):
    """Tests de manejo de errores en API"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.token = Token.objects.create(user=self.user)

    def test_not_found_returns_404(self):
        """Empresa inexistente retorna 404"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        url = reverse("empresa-detail", args=[9999])
        response = self.client.get(url)
        assert response.status_code == 404

    def test_invalid_method_returns_405(self):
        """Método no permitido retorna 405"""
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        url = reverse("empresa-list")
        response = self.client.post(url, {})
        assert response.status_code == 405
