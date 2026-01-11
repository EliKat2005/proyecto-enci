"""
Comando para generar predicciones financieras con Prophet.
"""

from django.core.management.base import BaseCommand, CommandError

from contabilidad.ml_predictions import PredictionService
from contabilidad.models import Empresa


class Command(BaseCommand):
    help = "Genera predicciones financieras usando Prophet"

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa-id", type=int, required=True, help="ID de la empresa a analizar"
        )
        parser.add_argument(
            "--tipo",
            type=str,
            choices=["INGR", "GAST", "FLUJ", "UTIL", "TODOS"],
            default="TODOS",
            help="Tipo de predicción (default: TODOS)",
        )
        parser.add_argument(
            "--dias-historicos",
            type=int,
            default=365,
            help="Días históricos para entrenar (default: 365)",
        )
        parser.add_argument(
            "--dias-futuros",
            type=int,
            default=30,
            help="Días a predecir (default: 30)",
        )
        parser.add_argument(
            "--no-guardar",
            action="store_true",
            help="No guardar predicciones en BD (solo mostrar)",
        )

    def handle(self, *args, **options):
        empresa_id = options["empresa_id"]
        tipo = options["tipo"]
        dias_historicos = options["dias_historicos"]
        dias_futuros = options["dias_futuros"]
        guardar = not options["no_guardar"]

        # Validar empresa
        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            raise CommandError(f"No existe empresa con ID {empresa_id}")

        self.stdout.write(self.style.SUCCESS(f'\n{"=" * 70}'))
        self.stdout.write(self.style.SUCCESS("GENERACIÓN DE PREDICCIONES FINANCIERAS"))
        self.stdout.write(self.style.SUCCESS(f'{"=" * 70}'))
        self.stdout.write(f"Empresa: {empresa.nombre} (ID: {empresa.id})")
        self.stdout.write(f"Días históricos: {dias_historicos}")
        self.stdout.write(f"Días a predecir: {dias_futuros}")
        self.stdout.write(f"Guardar en BD: {'Sí' if guardar else 'No'}")
        self.stdout.write("")

        # Inicializar servicio
        service = PredictionService(empresa)

        # Generar predicciones
        if tipo == "TODOS":
            self.stdout.write("Generando todas las predicciones...")
            resultados = service.generar_todas_predicciones(
                dias_historicos=dias_historicos, dias_futuros=dias_futuros
            )
        else:
            self.stdout.write(f"Generando predicciones para {tipo}...")
            resultado = service.generar_predicciones(
                tipo_prediccion=tipo,
                dias_historicos=dias_historicos,
                dias_futuros=dias_futuros,
                guardar=guardar,
            )
            resultados = {tipo: resultado}

        # Mostrar resultados
        self.stdout.write(self.style.SUCCESS(f'\n{"=" * 70}'))
        self.stdout.write(self.style.SUCCESS("RESULTADOS"))
        self.stdout.write(self.style.SUCCESS(f'{"=" * 70}\n'))

        tipos_nombres = {
            "INGR": "Ingresos",
            "GAST": "Gastos",
            "FLUJ": "Flujo de Efectivo",
            "UTIL": "Utilidad",
        }

        total_exitosos = 0
        total_fallidos = 0

        for tipo_codigo, resultado in resultados.items():
            tipo_nombre = tipos_nombres.get(tipo_codigo, tipo_codigo)

            if resultado.get("success"):
                total_exitosos += 1
                self.stdout.write(self.style.SUCCESS(f"\n✓ {tipo_nombre.upper()}"))
                self.stdout.write("-" * 70)

                # Información básica
                self.stdout.write(f"  Datos históricos: {resultado['dias_historicos']} días")
                self.stdout.write(f"  Predicciones generadas: {resultado['dias_predichos']} días")

                # Métricas del modelo
                metricas = resultado.get("metricas", {})
                self.stdout.write("\n  Métricas del modelo:")
                if metricas.get("mae") is not None:
                    self.stdout.write(f"    MAE:  {metricas['mae']:.2f}")
                if metricas.get("rmse") is not None:
                    self.stdout.write(f"    RMSE: {metricas['rmse']:.2f}")
                if metricas.get("mape") is not None:
                    self.stdout.write(f"    MAPE: {metricas['mape']:.2f}%")

                # Tendencia
                tendencia = resultado.get("tendencia", "N/A")
                self.stdout.write(f"\n  Tendencia: {tendencia}")

                # Mostrar algunas predicciones
                predicciones = resultado.get("predicciones", [])
                if predicciones:
                    self.stdout.write("\n  Primeras 5 predicciones:")
                    for pred in predicciones[:5]:
                        fecha = pred["ds"]
                        valor = pred["yhat"]
                        lower = pred["yhat_lower"]
                        upper = pred["yhat_upper"]
                        self.stdout.write(
                            f"    {fecha}: ${valor:,.2f} " f"[${lower:,.2f} - ${upper:,.2f}]"
                        )

                    if len(predicciones) > 5:
                        self.stdout.write(f"    ... y {len(predicciones) - 5} más")

            else:
                total_fallidos += 1
                error = resultado.get("error", "Error desconocido")
                self.stdout.write(self.style.ERROR(f"\n✗ {tipo_nombre.upper()}"))
                self.stdout.write(f"  Error: {error}")

        # Resumen final
        self.stdout.write(self.style.SUCCESS(f'\n{"=" * 70}'))
        self.stdout.write(self.style.SUCCESS("RESUMEN"))
        self.stdout.write(self.style.SUCCESS(f'{"=" * 70}'))
        self.stdout.write(f"Predicciones exitosas: {total_exitosos}")
        self.stdout.write(f"Predicciones fallidas: {total_fallidos}")

        if guardar and total_exitosos > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ {total_exitosos} predicción(es) guardada(s) en la base de datos"
                )
            )

        self.stdout.write("")
