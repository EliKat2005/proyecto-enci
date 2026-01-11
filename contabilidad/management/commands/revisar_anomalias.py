"""
Comando para revisar y gestionar anomalías detectadas.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from contabilidad.ml_anomalies import AnomalyService
from contabilidad.models import AnomaliaDetectada, Empresa

User = get_user_model()


class Command(BaseCommand):
    help = "Revisa y gestiona anomalías detectadas en transacciones"

    def add_arguments(self, parser):
        parser.add_argument("--empresa-id", type=int, required=True, help="ID de la empresa")
        parser.add_argument(
            "--listar",
            action="store_true",
            help="Listar anomalías sin revisar",
        )
        parser.add_argument(
            "--anomalia-id",
            type=int,
            help="ID de anomalía específica a revisar",
        )
        parser.add_argument(
            "--falso-positivo",
            action="store_true",
            help="Marcar como falso positivo",
        )
        parser.add_argument(
            "--notas",
            type=str,
            default="",
            help="Notas sobre la revisión",
        )
        parser.add_argument(
            "--limite",
            type=int,
            default=20,
            help="Número máximo de anomalías a listar (default: 20)",
        )
        parser.add_argument(
            "--tipo",
            type=str,
            choices=["MONTO", "FREQ", "PTRN", "CONT", "TEMP", "TODOS"],
            default="TODOS",
            help="Filtrar por tipo de anomalía",
        )
        parser.add_argument(
            "--severidad",
            type=str,
            choices=["BAJA", "MEDIA", "ALTA", "CRITICA"],
            help="Filtrar por severidad",
        )
        parser.add_argument(
            "--estadisticas",
            action="store_true",
            help="Mostrar estadísticas de anomalías",
        )

    def handle(self, *args, **options):
        empresa_id = options["empresa_id"]

        # Validar empresa
        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            raise CommandError(f"No existe empresa con ID {empresa_id}")

        self.stdout.write(self.style.SUCCESS(f'\n{"=" * 80}'))
        self.stdout.write(self.style.SUCCESS("REVISIÓN DE ANOMALÍAS"))
        self.stdout.write(self.style.SUCCESS(f'{"=" * 80}'))
        self.stdout.write(f"Empresa: {empresa.nombre} (ID: {empresa.id})")
        self.stdout.write("")

        # Inicializar servicio
        service = AnomalyService(empresa)

        # Ejecutar acción según parámetros
        if options["estadisticas"]:
            self._mostrar_estadisticas(empresa)

        elif options["listar"]:
            self._listar_anomalias(
                empresa,
                limite=options["limite"],
                tipo=options["tipo"],
                severidad=options["severidad"],
            )

        elif options["anomalia_id"]:
            self._revisar_anomalia(
                service,
                anomalia_id=options["anomalia_id"],
                es_falso_positivo=options["falso_positivo"],
                notas=options["notas"],
            )

        else:
            self.stdout.write(
                self.style.WARNING("Especifica --listar, --anomalia-id o --estadisticas")
            )
            self.stdout.write("\nEjemplos:")
            self.stdout.write(
                f"  python manage.py revisar_anomalias --empresa-id {empresa_id} --listar"
            )
            self.stdout.write(
                f"  python manage.py revisar_anomalias --empresa-id {empresa_id} "
                "--anomalia-id 123 --notas 'Revisado y válido'"
            )

        self.stdout.write("")

    def _mostrar_estadisticas(self, empresa):
        """Muestra estadísticas de anomalías."""
        self.stdout.write(self.style.SUCCESS("ESTADÍSTICAS DE ANOMALÍAS"))
        self.stdout.write(f'{"=" * 80}\n')

        # Total de anomalías
        total = AnomaliaDetectada.objects.filter(empresa=empresa).count()
        sin_revisar = AnomaliaDetectada.objects.filter(empresa=empresa, revisada=False).count()
        revisadas = total - sin_revisar
        falsos_positivos = AnomaliaDetectada.objects.filter(
            empresa=empresa, es_falso_positivo=True
        ).count()

        self.stdout.write(f"Total anomalías: {total}")
        self.stdout.write(f"Sin revisar: {sin_revisar}")
        self.stdout.write(f"Revisadas: {revisadas}")
        self.stdout.write(f"Falsos positivos: {falsos_positivos}")

        if total > 0:
            porcentaje_revisadas = (revisadas / total) * 100
            porcentaje_falsos = (falsos_positivos / total) * 100
            self.stdout.write(f"Porcentaje revisadas: {porcentaje_revisadas:.1f}%")
            self.stdout.write(f"Porcentaje falsos positivos: {porcentaje_falsos:.1f}%")

        # Por tipo
        self.stdout.write("\nPor tipo:")
        tipos = {
            "MONTO": "Monto Inusual",
            "FREQ": "Frecuencia Anormal",
            "PTRN": "Patrón Sospechoso",
            "CONT": "Inconsistencia Contable",
            "TEMP": "Temporal Atípica",
        }

        for tipo_code, tipo_nombre in tipos.items():
            count = AnomaliaDetectada.objects.filter(
                empresa=empresa, tipo_anomalia=tipo_code
            ).count()
            if count > 0:
                self.stdout.write(f"  {tipo_nombre}: {count}")

        # Por severidad
        self.stdout.write("\nPor severidad:")
        severidades = ["CRITICA", "ALTA", "MEDIA", "BAJA"]

        for sev in severidades:
            count = AnomaliaDetectada.objects.filter(empresa=empresa, severidad=sev).count()
            if count > 0:
                color = self._get_color_severidad(sev)
                self.stdout.write(color(f"  {sev}: {count}"))

        # Anomalías más recientes
        self.stdout.write("\nDetecciones recientes:")
        recientes = AnomaliaDetectada.objects.filter(empresa=empresa).order_by("-fecha_deteccion")[
            :5
        ]

        for anomalia in recientes:
            fecha = anomalia.fecha_deteccion.strftime("%Y-%m-%d %H:%M")
            color = self._get_color_severidad(anomalia.severidad)
            self.stdout.write(
                f"  {fecha} - {color(anomalia.severidad)} - "
                f"{anomalia.get_tipo_anomalia_display()}"
            )

    def _listar_anomalias(self, empresa, limite, tipo, severidad):
        """Lista anomalías sin revisar."""
        # Construir query
        queryset = AnomaliaDetectada.objects.filter(empresa=empresa, revisada=False)

        if tipo != "TODOS":
            queryset = queryset.filter(tipo_anomalia=tipo)

        if severidad:
            queryset = queryset.filter(severidad=severidad)

        queryset = queryset.order_by("-severidad", "-fecha_deteccion")[:limite]

        anomalias = list(queryset)

        if not anomalias:
            self.stdout.write(self.style.WARNING("No hay anomalías sin revisar"))
            return

        self.stdout.write(self.style.SUCCESS(f"ANOMALÍAS SIN REVISAR ({len(anomalias)})"))
        self.stdout.write(f'{"=" * 80}\n')

        for i, anomalia in enumerate(anomalias, 1):
            color = self._get_color_severidad(anomalia.severidad)

            self.stdout.write(color(f"{i}. ID: {anomalia.id}"))
            self.stdout.write(
                f"   Tipo: {anomalia.get_tipo_anomalia_display()} | "
                f"Severidad: {color(anomalia.severidad)}"
            )
            self.stdout.write(
                f"   Detectada: {anomalia.fecha_deteccion.strftime('%Y-%m-%d %H:%M')}"
            )
            self.stdout.write(f"   Algoritmo: {anomalia.algoritmo_usado}")
            self.stdout.write(f"   Score: {anomalia.score_anomalia}")

            # Descripción (truncada si es muy larga)
            descripcion = anomalia.descripcion
            if len(descripcion) > 100:
                descripcion = descripcion[:97] + "..."
            self.stdout.write(f"   {descripcion}")

            # IDs relacionados
            if anomalia.transaccion_id:
                self.stdout.write(f"   Transacción ID: {anomalia.transaccion_id}")
            if anomalia.asiento_id:
                self.stdout.write(f"   Asiento ID: {anomalia.asiento_id}")

            self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"Mostrando {len(anomalias)} de {queryset.model.objects.filter(empresa=empresa, revisada=False).count()} anomalías sin revisar"
            )
        )

    def _revisar_anomalia(self, service, anomalia_id, es_falso_positivo, notas):
        """Marca una anomalía como revisada."""
        self.stdout.write(f"Revisando anomalía ID {anomalia_id}...")

        # Obtener anomalía para mostrar detalles
        try:
            anomalia = AnomaliaDetectada.objects.get(id=anomalia_id, empresa=service.empresa)
        except AnomaliaDetectada.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Anomalía {anomalia_id} no encontrada para esta empresa")
            )
            return

        # Mostrar detalles
        self.stdout.write("\nDetalles de la anomalía:")
        self.stdout.write(f"  Tipo: {anomalia.get_tipo_anomalia_display()}")
        self.stdout.write(f"  Severidad: {anomalia.severidad}")
        self.stdout.write(f"  Detectada: {anomalia.fecha_deteccion.strftime('%Y-%m-%d %H:%M')}")
        self.stdout.write(f"  Descripción: {anomalia.descripcion}")

        # Marcar como revisada
        exito = service.marcar_como_revisada(
            anomalia_id=anomalia_id,
            es_falso_positivo=es_falso_positivo,
            notas=notas,
            usuario=None,
        )

        if exito:
            if es_falso_positivo:
                self.stdout.write(self.style.SUCCESS("\n✓ Anomalía marcada como FALSO POSITIVO"))
            else:
                self.stdout.write(self.style.SUCCESS("\n✓ Anomalía marcada como REVISADA"))

            if notas:
                self.stdout.write(f"  Notas: {notas}")
        else:
            self.stdout.write(self.style.ERROR("\n✗ Error al marcar la anomalía"))

    def _get_color_severidad(self, severidad):
        """Retorna el estilo de color según la severidad."""
        colores = {
            "CRITICA": self.style.ERROR,
            "ALTA": self.style.WARNING,
            "MEDIA": self.style.NOTICE,
            "BAJA": self.style.SUCCESS,
        }
        return colores.get(severidad, self.style.SUCCESS)
