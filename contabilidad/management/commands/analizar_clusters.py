"""
Comando para analizar clusters de cuentas similares.
"""

from django.core.management.base import BaseCommand, CommandError

from contabilidad.ml_embeddings import EmbeddingService
from contabilidad.models import Empresa


class Command(BaseCommand):
    help = "Analiza y agrupa cuentas contables en clusters semánticos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa-id", type=int, required=True, help="ID de la empresa a analizar"
        )
        parser.add_argument(
            "--n-clusters", type=int, default=5, help="Número de clusters a generar (default: 5)"
        )

    def handle(self, *args, **options):
        empresa_id = options["empresa_id"]
        n_clusters = options["n_clusters"]

        # Validar empresa
        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            raise CommandError(f"No existe empresa con ID {empresa_id}")

        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        self.stdout.write(self.style.SUCCESS("ANÁLISIS DE CLUSTERS DE CUENTAS"))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}'))
        self.stdout.write(f"Empresa: {empresa.nombre} (ID: {empresa.id})")
        self.stdout.write(f"Número de clusters: {n_clusters}")
        self.stdout.write("")

        # Inicializar servicio
        service = EmbeddingService()

        try:
            # Generar clusters
            self.stdout.write("Generando clusters...")
            clusters = service.obtener_clusters_cuentas(empresa=empresa, n_clusters=n_clusters)

            if not clusters:
                self.stdout.write(self.style.WARNING("⚠ No se pudieron generar clusters"))
                return

            # Mostrar resultados
            self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
            self.stdout.write(self.style.SUCCESS("RESULTADOS"))
            self.stdout.write(self.style.SUCCESS(f'{"="*70}\n'))

            for cluster_id in sorted(clusters.keys()):
                cuentas = clusters[cluster_id]
                self.stdout.write(
                    self.style.WARNING(f"\n📊 CLUSTER {cluster_id + 1} ({len(cuentas)} cuentas)")
                )
                self.stdout.write("-" * 70)

                # Analizar tipos de cuenta en el cluster
                tipos = {}
                for cuenta in cuentas:
                    tipo = cuenta["tipo"]
                    tipos[tipo] = tipos.get(tipo, 0) + 1

                self.stdout.write("Distribución por tipo:")
                for tipo, count in sorted(tipos.items(), key=lambda x: x[1], reverse=True):
                    porcentaje = (count / len(cuentas)) * 100
                    bar = "█" * int(porcentaje / 5)
                    self.stdout.write(f"  {tipo:12} : {count:3} ({porcentaje:5.1f}%) {bar}")

                # Mostrar algunas cuentas del cluster
                self.stdout.write("\nCuentas representativas:")
                for cuenta in cuentas[:5]:  # Mostrar primeras 5
                    self.stdout.write(f'  • {cuenta["codigo"]:10} - {cuenta["descripcion"][:50]}')

                if len(cuentas) > 5:
                    self.stdout.write(f"  ... y {len(cuentas) - 5} más")

            # Resumen
            total_cuentas = sum(len(cuentas) for cuentas in clusters.values())
            self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
            self.stdout.write(self.style.SUCCESS("RESUMEN"))
            self.stdout.write(self.style.SUCCESS(f'{"="*70}'))
            self.stdout.write(f"Total de clusters: {len(clusters)}")
            self.stdout.write(f"Total de cuentas: {total_cuentas}")
            self.stdout.write(f"Promedio por cluster: {total_cuentas / len(clusters):.1f}")

            # Cluster más grande y más pequeño
            cluster_sizes = {k: len(v) for k, v in clusters.items()}
            max_cluster = max(cluster_sizes.items(), key=lambda x: x[1])
            min_cluster = min(cluster_sizes.items(), key=lambda x: x[1])

            self.stdout.write(
                f"\nCluster más grande: Cluster {max_cluster[0] + 1} ({max_cluster[1]} cuentas)"
            )
            self.stdout.write(
                f"Cluster más pequeño: Cluster {min_cluster[0] + 1} ({min_cluster[1]} cuentas)"
            )

            self.stdout.write("")

        except Exception as e:
            raise CommandError(f"Error generando clusters: {str(e)}")
