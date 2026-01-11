#!/usr/bin/env python
"""
Script para probar todos los endpoints de ML/AI.
Ejecutar después de iniciar el servidor: python manage.py runserver
"""

import sys

import requests
from rich.console import Console
from rich.table import Table

console = Console()

# Configuración
BASE_URL = "http://localhost:8000"
USERNAME = "admin"  # Cambiar por tu usuario
PASSWORD = "admin"  # Cambiar por tu contraseña
EMPRESA_ID = 1  # Cambiar por el ID de tu empresa


class MLAPITester:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.session = requests.Session()
        self.empresa_id = None

        # Iniciar sesión
        self.login(username, password)

    def login(self, username, password):
        """Autenticarse en Django."""
        console.print(f"\n[bold blue]🔐 Iniciando sesión como {username}...[/bold blue]")

        # Obtener CSRF token
        response = self.session.get(f"{self.base_url}/admin/login/")
        csrf_token = response.cookies.get("csrftoken")

        # Login
        response = self.session.post(
            f"{self.base_url}/admin/login/",
            data={
                "username": username,
                "password": password,
                "csrfmiddlewaretoken": csrf_token,
                "next": "/admin/",
            },
            headers={"Referer": f"{self.base_url}/admin/login/"},
        )

        if response.status_code == 200 and "sessionid" in self.session.cookies:
            console.print("[green]✓ Sesión iniciada correctamente[/green]")
        else:
            console.print("[red]✗ Error al iniciar sesión[/red]")
            sys.exit(1)

    def test_endpoint(self, method, endpoint, description, data=None, params=None):
        """Prueba un endpoint y muestra el resultado."""
        url = f"{self.base_url}{endpoint}"

        try:
            console.print(f"\n[bold cyan]→ {method} {endpoint}[/bold cyan]")
            console.print(f"  {description}")

            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Método no soportado: {method}")

            if response.status_code in [200, 201]:
                console.print(f"[green]✓ Status: {response.status_code}[/green]")

                # Mostrar parte de la respuesta
                try:
                    result = response.json()
                    if isinstance(result, dict):
                        console.print(f"  Keys: {list(result.keys())[:5]}")
                    elif isinstance(result, list):
                        console.print(f"  Items: {len(result)}")
                except Exception:
                    pass

                return True, response
            else:
                console.print(f"[red]✗ Status: {response.status_code}[/red]")
                try:
                    console.print(f"  Error: {response.json()}")
                except Exception:
                    console.print(f"  Error: {response.text[:200]}")
                return False, response

        except Exception as e:
            console.print(f"[red]✗ Exception: {e}[/red]")
            return False, None

    def test_analytics(self):
        """Prueba endpoints de Analytics."""
        console.print("\n[bold yellow]📊 === ANALYTICS ===[/bold yellow]")

        tests = [
            (
                "GET",
                f"/api/ml/analytics/metricas/{self.empresa_id}/",
                "Calcular métricas financieras",
                None,
                None,
            ),
            (
                "GET",
                f"/api/ml/analytics/tendencias/{self.empresa_id}/",
                "Obtener tendencias de ingresos/gastos",
                None,
                {"meses": 6},
            ),
            (
                "GET",
                f"/api/ml/analytics/top-cuentas/{self.empresa_id}/",
                "Top cuentas por movimiento",
                None,
                {"limit": 10},
            ),
            (
                "GET",
                f"/api/ml/analytics/composicion/{self.empresa_id}/",
                "Composición patrimonial",
                None,
                None,
            ),
            (
                "GET",
                f"/api/ml/analytics/jerarquico/{self.empresa_id}/",
                "Análisis jerárquico de cuentas",
                None,
                {"nivel_max": 3},
            ),
        ]

        results = []
        for method, endpoint, description, data, params in tests:
            success, _ = self.test_endpoint(method, endpoint, description, data, params)
            results.append((description, "✓" if success else "✗"))

        return results

    def test_embeddings(self):
        """Prueba endpoints de Embeddings."""
        console.print("\n[bold yellow]🧠 === EMBEDDINGS ===[/bold yellow]")

        tests = [
            (
                "POST",
                f"/api/ml/embeddings/generar/{self.empresa_id}/",
                "Generar embeddings",
                {"force": False},
                None,
            ),
            (
                "POST",
                f"/api/ml/embeddings/buscar/{self.empresa_id}/",
                "Búsqueda semántica",
                {"texto": "gastos de oficina", "limit": 5, "min_similarity": 0.6},
                None,
            ),
            (
                "POST",
                f"/api/ml/embeddings/recomendar/{self.empresa_id}/",
                "Recomendar cuentas",
                {"descripcion_transaccion": "Pago de servicios básicos", "top_k": 3},
                None,
            ),
            (
                "GET",
                f"/api/ml/embeddings/clusters/{self.empresa_id}/",
                "Obtener clusters",
                None,
                {"n_clusters": 5},
            ),
            ("GET", "/api/ml/embeddings/", "Listar embeddings", None, None),
        ]

        results = []
        for method, endpoint, description, data, params in tests:
            success, _ = self.test_endpoint(method, endpoint, description, data, params)
            results.append((description, "✓" if success else "✗"))

        return results

    def test_predictions(self):
        """Prueba endpoints de Predictions."""
        console.print("\n[bold yellow]🔮 === PREDICTIONS ===[/bold yellow]")

        tests = [
            (
                "POST",
                f"/api/ml/predictions/generar/{self.empresa_id}/",
                "Generar predicciones de ingresos",
                {"tipo_prediccion": "INGRESOS", "dias_historicos": 30, "dias_futuros": 7},
                None,
            ),
            (
                "GET",
                f"/api/ml/predictions/tendencia/{self.empresa_id}/",
                "Análisis de tendencia",
                None,
                {"tipo": "INGRESOS", "dias": 30},
            ),
            ("GET", "/api/ml/predictions/", "Listar predicciones", None, None),
        ]

        results = []
        for method, endpoint, description, data, params in tests:
            success, _ = self.test_endpoint(method, endpoint, description, data, params)
            results.append((description, "✓" if success else "✗"))

        return results

    def test_anomalies(self):
        """Prueba endpoints de Anomalies."""
        console.print("\n[bold yellow]🚨 === ANOMALIES ===[/bold yellow]")

        tests = [
            (
                "POST",
                f"/api/ml/anomalies/detectar/{self.empresa_id}/",
                "Detectar anomalías de monto",
                {"tipo": "MONTO", "dias_historicos": 30, "contamination": 0.1},
                None,
            ),
            (
                "GET",
                f"/api/ml/anomalies/estadisticas/{self.empresa_id}/",
                "Estadísticas de anomalías",
                None,
                None,
            ),
            (
                "GET",
                "/api/ml/anomalies/",
                "Listar anomalías",
                None,
                {"severidad": "ALTA", "revisada": "false"},
            ),
        ]

        results = []
        for method, endpoint, description, data, params in tests:
            success, _ = self.test_endpoint(method, endpoint, description, data, params)
            results.append((description, "✓" if success else "✗"))

        return results

    def test_documentation(self):
        """Verifica que la documentación esté disponible."""
        console.print("\n[bold yellow]📚 === DOCUMENTATION ===[/bold yellow]")

        tests = [
            ("GET", "/api/schema/", "OpenAPI Schema"),
            ("GET", "/api/docs/", "Swagger UI"),
            ("GET", "/api/redoc/", "ReDoc"),
        ]

        results = []
        for _method, endpoint, description in tests:
            url = f"{self.base_url}{endpoint}"
            try:
                response = self.session.get(url)
                success = response.status_code == 200
                console.print(f"\n[bold cyan]→ {endpoint}[/bold cyan]")
                console.print(f"  {description}: {'✓' if success else '✗'}")
                results.append((description, "✓" if success else "✗"))
            except Exception as e:
                console.print(f"[red]✗ Error: {e}[/red]")
                results.append((description, "✗"))

        return results

    def run_all_tests(self, empresa_id):
        """Ejecuta todos los tests."""
        self.empresa_id = empresa_id

        console.print("\n[bold magenta]" + "=" * 60 + "[/bold magenta]")
        console.print(
            "[bold magenta]  PRUEBA DE APIs DE MACHINE LEARNING E INTELIGENCIA ARTIFICIAL[/bold magenta]"
        )
        console.print(f"[bold magenta]  Empresa ID: {empresa_id}[/bold magenta]")
        console.print("[bold magenta]" + "=" * 60 + "[/bold magenta]")

        # Ejecutar tests
        all_results = []
        all_results.extend(self.test_analytics())
        all_results.extend(self.test_embeddings())
        all_results.extend(self.test_predictions())
        all_results.extend(self.test_anomalies())
        all_results.extend(self.test_documentation())

        # Resumen final
        console.print("\n[bold magenta]" + "=" * 60 + "[/bold magenta]")
        console.print("[bold magenta]  RESUMEN DE RESULTADOS[/bold magenta]")
        console.print("[bold magenta]" + "=" * 60 + "[/bold magenta]")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Endpoint", style="dim", width=50)
        table.add_column("Estado", justify="center", width=10)

        success_count = 0
        for description, status in all_results:
            color = "green" if status == "✓" else "red"
            table.add_row(description, f"[{color}]{status}[/{color}]")
            if status == "✓":
                success_count += 1

        console.print(table)

        total = len(all_results)
        percentage = (success_count / total * 100) if total > 0 else 0

        console.print(f"\n[bold]Total: {success_count}/{total} ({percentage:.1f}%)[/bold]")

        if percentage == 100:
            console.print("\n[bold green]🎉 ¡Todos los tests pasaron exitosamente![/bold green]")
        elif percentage >= 80:
            console.print("\n[bold yellow]⚠️  La mayoría de los tests pasaron.[/bold yellow]")
        else:
            console.print("\n[bold red]❌ Muchos tests fallaron. Revisar configuración.[/bold red]")

        console.print("\n[bold blue]📖 Documentación disponible en:[/bold blue]")
        console.print(f"  • Swagger UI: {self.base_url}/api/docs/")
        console.print(f"  • ReDoc:      {self.base_url}/api/redoc/")
        console.print(f"  • Schema:     {self.base_url}/api/schema/")


def main():
    """Función principal."""
    console.print(
        "\n[bold]Script de prueba de APIs de ML/AI para ENCI[/bold]",
        style="bold blue",
    )

    # Verificar que el servidor esté corriendo
    try:
        response = requests.get(BASE_URL, timeout=2)
    except requests.exceptions.ConnectionError:
        console.print(f"\n[bold red]❌ Error: No se puede conectar a {BASE_URL}[/bold red]")
        console.print("[yellow]Asegúrate de que el servidor esté corriendo:[/yellow]")
        console.print("[yellow]  python manage.py runserver[/yellow]")
        sys.exit(1)

    # Crear tester y ejecutar
    tester = MLAPITester(BASE_URL, USERNAME, PASSWORD)
    tester.run_all_tests(EMPRESA_ID)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Prueba interrumpida por el usuario.[/yellow]")
        sys.exit(0)
