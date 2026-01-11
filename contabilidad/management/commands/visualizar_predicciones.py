"""
Comando para visualizar predicciones financieras guardadas.
"""

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError

from contabilidad.models import Empresa, PrediccionFinanciera


class Command(BaseCommand):
    help = "Visualiza predicciones financieras guardadas"

    def add_arguments(self, parser):
        parser.add_argument("--empresa-id", type=int, required=True, help="ID de la empresa")
        parser.add_argument(
            "--tipo",
            type=str,
            choices=["INGR", "GAST", "FLUJ", "UTIL"],
            required=True,
            help="Tipo de predicción a visualizar",
        )
        parser.add_argument(
            "--dias", type=int, default=30, help="Días de predicción a mostrar (default: 30)"
        )
        parser.add_argument("--grafico", action="store_true", help="Mostrar gráfico ASCII simple")

    def handle(self, *args, **options):
        empresa_id = options["empresa_id"]
        tipo = options["tipo"]
        dias = options["dias"]
        mostrar_grafico = options["grafico"]

        # Validar empresa
        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            raise CommandError(f"No existe empresa con ID {empresa_id}")

        self.stdout.write(self.style.SUCCESS(f'\n{"=" * 80}'))
        self.stdout.write(self.style.SUCCESS("PREDICCIONES FINANCIERAS"))
        self.stdout.write(self.style.SUCCESS(f'{"=" * 80}'))
        self.stdout.write(f"Empresa: {empresa.nombre} (ID: {empresa.id})")
        self.stdout.write(f"Tipo: {tipo}")
        self.stdout.write("")

        # Obtener predicciones
        fecha_inicio = datetime.now().date()
        fecha_fin = fecha_inicio + timedelta(days=dias)

        predicciones = PrediccionFinanciera.objects.filter(
            empresa=empresa,
            tipo_prediccion=tipo,
            fecha_prediccion__gte=fecha_inicio,
            fecha_prediccion__lte=fecha_fin,
        ).order_by("fecha_prediccion")

        if not predicciones.exists():
            self.stdout.write(
                self.style.WARNING(f"No hay predicciones guardadas para {tipo} en este periodo")
            )
            self.stdout.write(
                f"Usa: python manage.py generar_predicciones --empresa-id {empresa_id} --tipo {tipo}"
            )
            return

        # Mostrar información del modelo
        primera = predicciones.first()
        self.stdout.write("Información del modelo:")
        self.stdout.write(f"  Modelo usado: {primera.modelo_usado}")
        self.stdout.write(f"  Confianza: {primera.confianza * 100:.1f}%")

        if primera.metricas_modelo:
            self.stdout.write("\n  Métricas:")
            for key, value in primera.metricas_modelo.items():
                if isinstance(value, int | float):
                    self.stdout.write(f"    {key}: {value:.2f}")
                else:
                    self.stdout.write(f"    {key}: {value}")

        # Mostrar predicciones
        self.stdout.write(self.style.SUCCESS(f'\n{"=" * 80}'))
        self.stdout.write(self.style.SUCCESS("PREDICCIONES"))
        self.stdout.write(self.style.SUCCESS(f'{"=" * 80}'))

        valores = []
        for pred in predicciones:
            fecha_str = pred.fecha_prediccion.strftime("%Y-%m-%d")
            valor = pred.valor_predicho
            lower = pred.limite_inferior
            upper = pred.limite_superior

            self.stdout.write(
                f"{fecha_str}  ${valor:>12,.2f}  " f"[${lower:>12,.2f} - ${upper:>12,.2f}]"
            )
            valores.append(valor)

        # Estadísticas
        if valores:
            self.stdout.write(self.style.SUCCESS(f'\n{"=" * 80}'))
            self.stdout.write(self.style.SUCCESS("ESTADÍSTICAS"))
            self.stdout.write(self.style.SUCCESS(f'{"=" * 80}'))
            self.stdout.write(f"Total predicciones: {len(valores)}")
            self.stdout.write(f"Valor promedio:     ${sum(valores) / len(valores):,.2f}")
            self.stdout.write(f"Valor mínimo:       ${min(valores):,.2f}")
            self.stdout.write(f"Valor máximo:       ${max(valores):,.2f}")

            # Calcular tendencia
            if len(valores) >= 2:
                primera_mitad = sum(valores[: len(valores) // 2]) / (len(valores) // 2)
                segunda_mitad = sum(valores[len(valores) // 2 :]) / (
                    len(valores) - len(valores) // 2
                )
                cambio = (
                    (segunda_mitad - primera_mitad) / primera_mitad * 100
                    if primera_mitad != 0
                    else 0
                )

                if cambio > 5:
                    tendencia = f"Creciente (+{cambio:.1f}%)"
                    color = self.style.SUCCESS
                elif cambio < -5:
                    tendencia = f"Decreciente ({cambio:.1f}%)"
                    color = self.style.WARNING
                else:
                    tendencia = f"Estable ({cambio:+.1f}%)"
                    color = self.style.NOTICE

                self.stdout.write(f"Tendencia:          {color(tendencia)}")

        # Gráfico ASCII (opcional)
        if mostrar_grafico and valores:
            self.stdout.write(self.style.SUCCESS(f'\n{"=" * 80}'))
            self.stdout.write(self.style.SUCCESS("GRÁFICO"))
            self.stdout.write(self.style.SUCCESS(f'{"=" * 80}\n'))
            self._mostrar_grafico_ascii(valores, predicciones)

        self.stdout.write("")

    def _mostrar_grafico_ascii(self, valores, predicciones):
        """Muestra un gráfico ASCII simple de las predicciones."""
        if not valores:
            return

        # Normalizar valores para el gráfico
        min_val = min(valores)
        max_val = max(valores)
        rango = max_val - min_val if max_val != min_val else 1

        altura = 15  # Altura del gráfico en líneas
        ancho = min(len(valores), 60)  # Ancho máximo

        # Escalar valores
        valores_escalados = [int((v - min_val) / rango * (altura - 1)) for v in valores[:ancho]]

        # Dibujar gráfico
        for i in range(altura - 1, -1, -1):
            # Valor del eje Y
            valor_y = min_val + (i / (altura - 1)) * rango
            linea = f"${valor_y:>10,.0f} │"

            # Dibujar barras
            for val_escalado in valores_escalados:
                if val_escalado >= i:
                    linea += "█"
                else:
                    linea += " "

            self.stdout.write(linea)

        # Eje X
        self.stdout.write(" " * 12 + "└" + "─" * ancho)

        # Fechas
        if predicciones:
            primera_fecha = predicciones[0].fecha_prediccion.strftime("%d/%m")
            ultima_fecha = predicciones[
                min(ancho - 1, len(predicciones) - 1)
            ].fecha_prediccion.strftime("%d/%m")
            espacios = ancho - len(primera_fecha) - len(ultima_fecha)
            self.stdout.write(" " * 13 + primera_fecha + " " * espacios + ultima_fecha)
