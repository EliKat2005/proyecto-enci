"""
Comando para detectar anomalías en transacciones contables.
"""

from django.core.management.base import BaseCommand, CommandError

from contabilidad.ml_anomalies import AnomalyService
from contabilidad.models import Empresa


class Command(BaseCommand):
    help = "Detecta anomalías en transacciones contables usando ML"

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa-id", type=int, required=True, help="ID de la empresa a analizar"
        )
        parser.add_argument(
            "--tipo",
            type=str,
            choices=["MONTO", "FRECUENCIA", "TEMPORAL", "PATRON", "TODOS"],
            default="TODOS",
            help="Tipo de anomalía a detectar (default: TODOS)",
        )
        parser.add_argument(
            "--dias-historicos",
            type=int,
            default=180,
            help="Días históricos para analizar (default: 180)",
        )
        parser.add_argument(
            "--no-guardar",
            action="store_true",
            help="No guardar anomalías en BD (solo mostrar)",
        )
        parser.add_argument(
            "--contamination",
            type=float,
            default=0.05,
            help="Proporción esperada de outliers para Isolation Forest (default: 0.05)",
        )

    def handle(self, *args, **options):
        empresa_id = options["empresa_id"]
        tipo = options["tipo"]
        dias_historicos = options["dias_historicos"]
        guardar = not options["no_guardar"]
        contamination = options["contamination"]

        # Validar empresa
        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            raise CommandError(f"No existe empresa con ID {empresa_id}")

        self.stdout.write(self.style.SUCCESS(f'\n{"=" * 80}'))
        self.stdout.write(self.style.SUCCESS("DETECCIÓN DE ANOMALÍAS EN TRANSACCIONES"))
        self.stdout.write(self.style.SUCCESS(f'{"=" * 80}'))
        self.stdout.write(f"Empresa: {empresa.nombre} (ID: {empresa.id})")
        self.stdout.write(f"Tipo: {tipo}")
        self.stdout.write(f"Días históricos: {dias_historicos}")
        self.stdout.write(f"Guardar en BD: {'Sí' if guardar else 'No'}")
        self.stdout.write("")

        # Inicializar servicio
        service = AnomalyService(empresa)

        # Ejecutar detección según el tipo
        if tipo == "TODOS":
            self.stdout.write("Ejecutando detección completa de anomalías...\n")
            resultado = service.detectar_todas_anomalias(
                dias_historicos=dias_historicos, guardar=guardar
            )
            self._mostrar_resultado_completo(resultado)

        elif tipo == "MONTO":
            self.stdout.write("Detectando anomalías de monto (Isolation Forest)...\n")
            resultado = service.detectar_anomalias_monto(
                dias_historicos=dias_historicos,
                contamination=contamination,
                guardar=guardar,
            )
            self._mostrar_resultado_individual(resultado, "Monto")

        elif tipo == "FRECUENCIA":
            self.stdout.write("Detectando anomalías de frecuencia...\n")
            resultado = service.detectar_anomalias_frecuencia(
                dias_historicos=dias_historicos, guardar=guardar
            )
            self._mostrar_resultado_individual(resultado, "Frecuencia")

        elif tipo == "TEMPORAL":
            self.stdout.write("Detectando anomalías temporales...\n")
            resultado = service.detectar_anomalias_temporales(
                dias_historicos=dias_historicos, guardar=guardar
            )
            self._mostrar_resultado_individual(resultado, "Temporal")

        elif tipo == "PATRON":
            self.stdout.write("Detectando anomalías de patrón...\n")
            resultado = service.detectar_anomalias_patrones(
                dias_historicos=dias_historicos, guardar=guardar
            )
            self._mostrar_resultado_individual(resultado, "Patrón")

        self.stdout.write("")

    def _mostrar_resultado_completo(self, resultado):
        """Muestra resultado de detección completa."""
        if not resultado.get("success"):
            self.stdout.write(self.style.ERROR(f"Error: {resultado.get('error', 'Desconocido')}"))
            return

        self.stdout.write(self.style.SUCCESS(f'{"=" * 80}'))
        self.stdout.write(self.style.SUCCESS("RESUMEN GENERAL"))
        self.stdout.write(self.style.SUCCESS(f'{"=" * 80}'))
        self.stdout.write(f"Total anomalías detectadas: {resultado['total_anomalias_detectadas']}")

        if resultado.get("total_anomalias_guardadas") is not None:
            self.stdout.write(
                f"Total anomalías guardadas: {resultado['total_anomalias_guardadas']}"
            )

        # Mostrar resultados por tipo
        for tipo_nombre, tipo_resultado in resultado["resultados_por_tipo"].items():
            self.stdout.write(f"\n{'-' * 80}")
            self._mostrar_resultado_individual(tipo_resultado, tipo_nombre.capitalize())

    def _mostrar_resultado_individual(self, resultado, tipo_nombre):
        """Muestra resultado de un tipo específico de detección."""
        if not resultado.get("success"):
            self.stdout.write(
                self.style.ERROR(f"✗ {tipo_nombre}: {resultado.get('error', 'Error desconocido')}")
            )
            return

        self.stdout.write(self.style.SUCCESS(f"✓ {tipo_nombre.upper()}"))
        self.stdout.write(f"  Anomalías detectadas: {resultado['anomalias_detectadas']}")

        # Información específica según el tipo
        if "total_transacciones" in resultado:
            total = resultado["total_transacciones"]
            porcentaje = resultado.get("porcentaje_anomalias", 0)
            self.stdout.write(f"  Total transacciones: {total}")
            self.stdout.write(f"  Porcentaje anómalo: {porcentaje:.2f}%")

        if "total_cuentas_analizadas" in resultado:
            self.stdout.write(
                f"  Total cuentas analizadas: {resultado['total_cuentas_analizadas']}"
            )

        if "total_asientos_analizados" in resultado:
            self.stdout.write(
                f"  Total asientos analizados: {resultado['total_asientos_analizados']}"
            )

        # Estadísticas adicionales
        if "estadisticas" in resultado:
            self.stdout.write("\n  Estadísticas:")
            stats = resultado["estadisticas"]

            if "monto_promedio_normal" in stats:
                self.stdout.write(
                    f"    Monto promedio normal: ${stats['monto_promedio_normal']:,.2f}"
                )
            if "monto_promedio_anomalo" in stats:
                self.stdout.write(
                    f"    Monto promedio anómalo: ${stats['monto_promedio_anomalo']:,.2f}"
                )
            if "frecuencia_media" in stats:
                self.stdout.write(
                    f"    Frecuencia media: {stats['frecuencia_media']:.1f} transacciones"
                )
            if "umbral_superior" in stats:
                self.stdout.write(f"    Umbral superior: {stats['umbral_superior']:.1f}")

        # Mostrar algunas anomalías detectadas
        if resultado.get("anomalias_detalle"):
            self.stdout.write("\n  Ejemplos de anomalías detectadas:")
            detalles = resultado["anomalias_detalle"][:5]

            for i, detalle in enumerate(detalles, 1):
                linea = f"    {i}. "

                if "transaccion_id" in detalle:
                    linea += f"Transacción {detalle['transaccion_id']}: "
                if "asiento_id" in detalle:
                    linea += f"Asiento {detalle['asiento_id']}: "

                if "monto" in detalle:
                    linea += f"${detalle['monto']:,.2f}"
                if "cuenta_codigo" in detalle:
                    linea += f" - Cuenta {detalle['cuenta_codigo']}"
                if "num_transacciones" in detalle:
                    linea += f"{detalle['num_transacciones']} transacciones"
                if "z_score" in detalle:
                    linea += f" (Z={detalle['z_score']:.2f})"
                if "score" in detalle:
                    linea += f" (Score={detalle['score']:.4f})"
                if "motivo" in detalle:
                    linea += f" - {detalle['motivo']}"

                self.stdout.write(linea)

            if len(resultado["anomalias_detalle"]) > 5:
                self.stdout.write(f"    ... y {len(resultado['anomalias_detalle']) - 5} más")

        if resultado.get("anomalias_guardadas") is not None:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n  ✓ {resultado['anomalias_guardadas']} anomalías guardadas en BD"
                )
            )
