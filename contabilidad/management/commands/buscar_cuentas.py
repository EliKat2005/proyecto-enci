"""
Comando para probar búsqueda semántica de cuentas contables.
"""

from django.core.management.base import BaseCommand, CommandError

from contabilidad.ml_embeddings import EmbeddingService
from contabilidad.models import Empresa, EmpresaPlanCuenta


class Command(BaseCommand):
    help = "Prueba la búsqueda semántica de cuentas contables"

    def add_arguments(self, parser):
        parser.add_argument(
            "texto_busqueda",
            type=str,
            help='Texto a buscar (ej: "gastos de personal", "ingresos por ventas")',
        )
        parser.add_argument(
            "--empresa-id", type=int, required=True, help="ID de la empresa en la que buscar"
        )
        parser.add_argument(
            "--limit", type=int, default=10, help="Número máximo de resultados (default: 10)"
        )
        parser.add_argument(
            "--min-similarity",
            type=float,
            default=0.3,
            help="Similaridad mínima 0-1 (default: 0.3)",
        )
        parser.add_argument(
            "--cuenta-codigo",
            type=str,
            help="Código de cuenta para buscar similares (en lugar de texto libre)",
        )

    def handle(self, *args, **options):
        texto_busqueda = options["texto_busqueda"]
        empresa_id = options["empresa_id"]
        limit = options["limit"]
        min_similarity = options["min_similarity"]
        cuenta_codigo = options.get("cuenta_codigo")

        # Validar empresa
        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            raise CommandError(f"No existe empresa con ID {empresa_id}")

        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        self.stdout.write(self.style.SUCCESS("BÚSQUEDA SEMÁNTICA DE CUENTAS"))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}'))
        self.stdout.write(f"Empresa: {empresa.nombre} (ID: {empresa.id})")

        # Inicializar servicio
        service = EmbeddingService()

        if cuenta_codigo:
            # Búsqueda de cuentas similares a una cuenta específica
            self.stdout.write(f'Búsqueda: Cuentas similares a código "{cuenta_codigo}"')

            try:
                cuenta = EmpresaPlanCuenta.objects.get(empresa=empresa, codigo=cuenta_codigo)
            except EmpresaPlanCuenta.DoesNotExist:
                raise CommandError(f"No existe cuenta con código {cuenta_codigo} en la empresa")

            self.stdout.write(f"Cuenta referencia: {cuenta.codigo} - {cuenta.descripcion}")
            self.stdout.write(f"Tipo: {cuenta.get_tipo_display()}")
            self.stdout.write("")

            resultados = service.buscar_cuentas_similares(
                cuenta=cuenta, empresa=empresa, limit=limit, min_similarity=min_similarity
            )

        else:
            # Búsqueda por texto libre
            self.stdout.write(f'Búsqueda: "{texto_busqueda}"')
            self.stdout.write(f"Límite: {limit} resultados")
            self.stdout.write(f"Similaridad mínima: {min_similarity}")
            self.stdout.write("")

            resultados = service.buscar_por_texto(
                texto_busqueda=texto_busqueda,
                empresa=empresa,
                limit=limit,
                min_similarity=min_similarity,
            )

        # Mostrar resultados
        if not resultados:
            self.stdout.write(
                self.style.WARNING("⚠ No se encontraron resultados con la similaridad especificada")
            )
            return

        self.stdout.write(self.style.SUCCESS(f'\n{"="*70}'))
        self.stdout.write(self.style.SUCCESS(f"RESULTADOS ({len(resultados)} encontrados)"))
        self.stdout.write(self.style.SUCCESS(f'{"="*70}\n'))

        for idx, resultado in enumerate(resultados, 1):
            # Barra de similaridad visual
            similarity_percent = resultado["similarity"] * 100
            bar_length = int(similarity_percent / 5)  # 20 caracteres = 100%
            bar = "█" * bar_length + "░" * (20 - bar_length)

            # Color según similaridad
            if similarity_percent >= 70:
                style = self.style.SUCCESS
            elif similarity_percent >= 50:
                style = self.style.WARNING
            else:
                style = self.style.NOTICE

            self.stdout.write(style(f"[{idx}] Similaridad: {similarity_percent:.1f}% {bar}"))
            self.stdout.write(f'    Código: {resultado["codigo"]}')
            self.stdout.write(f'    Descripción: {resultado["descripcion"]}')
            self.stdout.write(f'    Tipo: {resultado["tipo"]}')

            if "naturaleza" in resultado:
                self.stdout.write(f'    Naturaleza: {resultado["naturaleza"]}')

            if "texto_fuente" in resultado and len(resultado["texto_fuente"]) < 150:
                self.stdout.write(f'    Contexto: {resultado["texto_fuente"]}')

            self.stdout.write("")

        # Sugerencias
        self.stdout.write(self.style.SUCCESS("\n💡 SUGERENCIAS:"))
        self.stdout.write("  - Usa --min-similarity más bajo para más resultados")
        self.stdout.write("  - Usa --min-similarity más alto para mayor precisión")
        self.stdout.write("  - Prueba diferentes frases descriptivas para mejor contexto")
        self.stdout.write("")
