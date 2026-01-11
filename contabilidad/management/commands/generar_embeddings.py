"""
Comando para generar embeddings de cuentas contables en batch.
"""

from django.core.management.base import BaseCommand, CommandError

from contabilidad.ml_embeddings import EmbeddingService
from contabilidad.models import Empresa, EmpresaCuentaEmbedding, EmpresaPlanCuenta


class Command(BaseCommand):
    help = "Genera embeddings vectoriales para cuentas contables"

    def add_arguments(self, parser):
        parser.add_argument("--empresa-id", type=int, help="ID de empresa específica a procesar")
        parser.add_argument(
            "--empresa-nombre", type=str, help="Nombre de empresa a procesar (búsqueda parcial)"
        )
        parser.add_argument("--todas", action="store_true", help="Procesar todas las empresas")
        parser.add_argument("--force", action="store_true", help="Regenerar embeddings existentes")
        parser.add_argument(
            "--modelo",
            type=str,
            default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            help="Modelo de sentence-transformers a usar",
        )

    def handle(self, *args, **options):
        empresa_id = options.get("empresa_id")
        empresa_nombre = options.get("empresa_nombre")
        todas = options.get("todas")
        force = options.get("force")
        modelo = options.get("modelo")

        # Validar argumentos
        if not (empresa_id or empresa_nombre or todas):
            raise CommandError("Debe especificar --empresa-id, --empresa-nombre o --todas")

        # Inicializar servicio
        self.stdout.write(
            self.style.SUCCESS(f"Inicializando EmbeddingService con modelo: {modelo}")
        )
        service = EmbeddingService(model_name=modelo)

        # Obtener empresas a procesar
        if empresa_id:
            empresas = Empresa.objects.filter(id=empresa_id)
            if not empresas.exists():
                raise CommandError(f"No existe empresa con ID {empresa_id}")
        elif empresa_nombre:
            empresas = Empresa.objects.filter(nombre__icontains=empresa_nombre)
            if not empresas.exists():
                raise CommandError(f'No se encontraron empresas con nombre "{empresa_nombre}"')
        else:
            empresas = Empresa.objects.all()

        total_empresas = empresas.count()
        self.stdout.write(self.style.SUCCESS(f"Procesando {total_empresas} empresa(s)..."))

        # Estadísticas globales
        global_stats = {
            "empresas_procesadas": 0,
            "cuentas_procesadas": 0,
            "embeddings_nuevos": 0,
            "embeddings_actualizados": 0,
            "errores": 0,
        }

        # Procesar cada empresa
        for idx, empresa in enumerate(empresas, 1):
            self.stdout.write(
                self.style.WARNING(
                    f"\n[{idx}/{total_empresas}] Procesando empresa: {empresa.nombre} (ID: {empresa.id})"
                )
            )

            # Contar cuentas
            num_cuentas = EmpresaPlanCuenta.objects.filter(empresa=empresa).count()
            self.stdout.write(f"  - Total de cuentas: {num_cuentas}")

            # Contar embeddings existentes
            num_embeddings_existentes = EmpresaCuentaEmbedding.objects.filter(
                cuenta__empresa=empresa, modelo_usado=modelo
            ).count()
            self.stdout.write(f"  - Embeddings existentes: {num_embeddings_existentes}")

            if num_cuentas == 0:
                self.stdout.write(self.style.WARNING("  ⚠ No hay cuentas para procesar"))
                continue

            try:
                # Generar embeddings
                stats = service.generar_embeddings_empresa(empresa=empresa, force_regenerate=force)

                # Mostrar resultados
                self.stdout.write(self.style.SUCCESS("  ✓ Procesamiento completado:"))
                self.stdout.write(f'    - Cuentas procesadas: {stats["procesadas"]}')
                self.stdout.write(f'    - Embeddings nuevos: {stats["nuevas"]}')
                self.stdout.write(f'    - Embeddings actualizados: {stats["actualizadas"]}')

                # Actualizar estadísticas globales
                global_stats["empresas_procesadas"] += 1
                global_stats["cuentas_procesadas"] += stats["procesadas"]
                global_stats["embeddings_nuevos"] += stats["nuevas"]
                global_stats["embeddings_actualizados"] += stats["actualizadas"]

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error procesando empresa: {str(e)}"))
                global_stats["errores"] += 1
                continue

        # Resumen final
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("RESUMEN FINAL"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(
            f'Empresas procesadas: {global_stats["empresas_procesadas"]}/{total_empresas}'
        )
        self.stdout.write(f'Cuentas procesadas: {global_stats["cuentas_procesadas"]}')
        self.stdout.write(f'Embeddings nuevos: {global_stats["embeddings_nuevos"]}')
        self.stdout.write(f'Embeddings actualizados: {global_stats["embeddings_actualizados"]}')

        if global_stats["errores"] > 0:
            self.stdout.write(self.style.WARNING(f'Errores encontrados: {global_stats["errores"]}'))

        self.stdout.write(self.style.SUCCESS("\n✓ Proceso completado exitosamente"))
