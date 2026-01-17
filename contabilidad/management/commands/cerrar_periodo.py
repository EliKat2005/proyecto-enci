"""
Management command para cerrar un periodo contable (año fiscal completo) y generar el asiento de cierre.

Ejecuta el cierre de un ejercicio fiscal completo:
1. Calcula el Estado de Resultados del año
2. Genera un asiento que cancela todas las cuentas de resultado
3. Traslada la utilidad/pérdida a Patrimonio (Resultados del Ejercicio)
4. Crea un registro EmpresaCierrePeriodo que bloquea el año

Uso:
    python manage.py cerrar_periodo --empresa-id=1 --anio=2025 --usuario=admin

    Opcional: agregar --desbloquear para reabrir un periodo cerrado
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from contabilidad.models import Empresa, EmpresaCierrePeriodo
from contabilidad.services import EstadosFinancierosService

User = get_user_model()


class Command(BaseCommand):
    help = "Cierra un periodo contable anual y genera el asiento de cierre del ejercicio"

    def add_arguments(self, parser):
        parser.add_argument(
            "--empresa-id", type=int, required=True, help="ID de la empresa a cerrar"
        )
        parser.add_argument(
            "--anio", type=int, required=True, help="Año fiscal a cerrar (ej: 2025)"
        )
        parser.add_argument(
            "--usuario",
            type=str,
            default="admin",
            help="Username del usuario que ejecuta el cierre",
        )
        parser.add_argument(
            "--desbloquear",
            action="store_true",
            help="Reabrir un periodo cerrado (elimina el bloqueo)",
        )

    def handle(self, *args, **options):
        empresa_id = options["empresa_id"]
        anio = options["anio"]
        username = options["usuario"]
        desbloquear = options["desbloquear"]

        # Validar empresa
        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            raise CommandError(f"❌ Empresa id={empresa_id} no existe")

        # Validar usuario
        try:
            usuario = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'❌ Usuario "{username}" no existe')

        # ===== MODO DESBLOQUEO =====
        if desbloquear:
            try:
                cierre = EmpresaCierrePeriodo.objects.get(empresa=empresa, periodo=anio)
                cierre.bloqueado = False
                cierre.save(update_fields=["bloqueado"])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Periodo {anio} DESBLOQUEADO para {empresa.nombre}. "
                        f"Ahora se pueden crear/editar asientos."
                    )
                )
                return
            except EmpresaCierrePeriodo.DoesNotExist:
                raise CommandError(f"❌ No existe cierre para el periodo {anio}")

        # ===== MODO CIERRE =====

        # Verificar si ya existe un cierre
        if EmpresaCierrePeriodo.objects.filter(empresa=empresa, periodo=anio).exists():
            raise CommandError(
                f"❌ El periodo {anio} ya fue cerrado para {empresa.nombre}. "
                f"Use --desbloquear para reabrir el periodo."
            )

        # Fecha de cierre: último día del año
        fecha_cierre = date(anio, 12, 31)

        # Calcular Estado de Resultados del año completo
        inicio_ejercicio = date(anio, 1, 1)
        self.stdout.write(f"📊 Calculando Estado de Resultados de {empresa.nombre}...")
        self.stdout.write(f"   Periodo: {inicio_ejercicio} a {fecha_cierre}")

        try:
            resultados = EstadosFinancierosService.estado_de_resultados(
                empresa, inicio_ejercicio, fecha_cierre
            )
        except Exception as e:
            raise CommandError(f"❌ Error al calcular Estado de Resultados: {str(e)}")

        # Mostrar resumen financiero
        self.stdout.write(self.style.WARNING("\n📈 Resumen Financiero del Ejercicio:"))
        self.stdout.write(f"   Ingresos:      ${resultados['ingresos']:>15,.2f}")
        self.stdout.write(f"   Costos:        ${resultados['costos']:>15,.2f}")
        self.stdout.write(f"   Gastos:        ${resultados['gastos']:>15,.2f}")
        self.stdout.write(f"   {'─' * 40}")
        utilidad_color = (
            self.style.SUCCESS if resultados["utilidad_neta"] >= 0 else self.style.ERROR
        )
        utilidad_text = f"${resultados['utilidad_neta']:>15,.2f}"
        self.stdout.write(f"   Utilidad Neta: {utilidad_color(utilidad_text)}\n")

        # Confirmar cierre
        warning_msg = (
            f"⚠️  ¿Desea cerrar el periodo {anio}? "
            f"Esto generará un asiento de cierre y bloqueará el año."
        )
        self.stdout.write(self.style.WARNING(warning_msg))

        # En modo batch (non-interactive), auto-confirmar
        if options.get("verbosity", 1) > 0:
            respuesta = input("Escriba 'SI' para continuar: ").strip().upper()
            if respuesta != "SI":
                self.stdout.write(self.style.ERROR("✗ Cierre cancelado por el usuario"))
                return

        # Ejecutar cierre en transacción atómica
        self.stdout.write(self.style.WARNING("\n🔒 Ejecutando cierre de periodo..."))

        try:
            with transaction.atomic():
                # 1. Generar asiento de cierre
                asiento = EstadosFinancierosService.asiento_de_cierre(
                    empresa, fecha_cierre, usuario
                )

                # 2. Crear registro de cierre
                cierre = EmpresaCierrePeriodo.objects.create(
                    empresa=empresa,
                    periodo=anio,
                    fecha_cierre=fecha_cierre,
                    asiento_cierre=asiento,
                    cerrado_por=usuario,
                    utilidad_neta=resultados["utilidad_neta"],
                    total_ingresos=resultados["ingresos"],
                    total_costos=resultados["costos"],
                    total_gastos=resultados["gastos"],
                    bloqueado=True,
                    notas="Cierre automático generado por comando management",
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✓ Cierre completado exitosamente:\n"
                        f"   • Periodo: {anio}\n"
                        f"   • Asiento de cierre: #{asiento.numero_asiento}\n"
                        f"   • Fecha de cierre: {fecha_cierre}\n"
                        f"   • Estado: BLOQUEADO\n"
                        f"   • Cerrado por: {usuario.get_full_name() or usuario.username}\n"
                    )
                )

        except Exception as e:
            raise CommandError(f"❌ Error al ejecutar el cierre: {str(e)}")

        self.stdout.write(
            self.style.WARNING(
                f"\n⚠️  IMPORTANTE: El periodo {anio} ahora está BLOQUEADO. "
                f"No se podrán crear nuevos asientos para este año."
            )
        )
        self.stdout.write(
            f"   Para reabrir: python manage.py cerrar_periodo --empresa-id={empresa_id} "
            f"--anio={anio} --desbloquear\n"
        )
