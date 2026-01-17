"""
Servicio de exportación consolidada de Excel.
Genera un archivo Excel completo con toda la información de la empresa.
"""

import io
from datetime import date, datetime
from decimal import Decimal

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .ml_services import MLAnalyticsService
from .services import EstadosFinancierosService, LibroMayorService


class ExcelExportService:
    """Servicio para generar exportaciones Excel consolidadas."""

    # Estilos predefinidos
    HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
    TITLE_FONT = Font(size=14, bold=True, color="1F4E78")
    SUBTITLE_FONT = Font(size=11, bold=True, color="4472C4")
    TOTAL_FILL = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
    TOTAL_FONT = Font(bold=True, size=10)

    BORDER_THIN = Border(
        left=Side(style="thin", color="D0CECE"),
        right=Side(style="thin", color="D0CECE"),
        top=Side(style="thin", color="D0CECE"),
        bottom=Side(style="thin", color="D0CECE"),
    )

    def __init__(self, empresa, fecha_inicio=None, fecha_fin=None):
        """
        Inicializa el servicio de exportación.

        Args:
            empresa: Instancia de Empresa
            fecha_inicio: Fecha de inicio para reportes (default: inicio del año)
            fecha_fin: Fecha de fin para reportes (default: hoy)
        """
        self.empresa = empresa
        hoy = date.today()
        self.fecha_inicio = fecha_inicio or date(hoy.year, 1, 1)
        self.fecha_fin = fecha_fin or hoy
        self.fecha_corte = fecha_fin or hoy

    def generar_excel_completo(self) -> bytes:
        """
        Genera un archivo Excel completo con toda la información de la empresa.

        Returns:
            bytes: Contenido del archivo Excel
        """
        wb = openpyxl.Workbook()
        # Eliminar la hoja por defecto
        wb.remove(wb.active)

        # Crear todas las hojas
        self._crear_hoja_portada(wb)
        self._crear_hoja_plan_cuentas(wb)
        self._crear_hoja_balance_comprobacion(wb)
        self._crear_hoja_balance_general(wb)
        self._crear_hoja_estado_resultados(wb)
        self._crear_hoja_metricas_financieras(wb)
        self._crear_hoja_tendencias(wb)
        self._crear_hoja_top_cuentas(wb)

        # Guardar en memoria
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    def _aplicar_estilo_header(self, ws, row, col_start, col_end):
        """Aplica estilo a las celdas de encabezado."""
        for col in range(col_start, col_end + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = self.HEADER_FILL
            cell.font = self.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = self.BORDER_THIN

    def _aplicar_estilo_titulo(self, cell):
        """Aplica estilo de título."""
        cell.font = self.TITLE_FONT
        cell.alignment = Alignment(horizontal="left", vertical="center")

    def _aplicar_estilo_subtitulo(self, cell):
        """Aplica estilo de subtítulo."""
        cell.font = self.SUBTITLE_FONT
        cell.alignment = Alignment(horizontal="left", vertical="center")

    def _aplicar_estilo_total(self, ws, row, col_start, col_end):
        """Aplica estilo a las celdas de total."""
        for col in range(col_start, col_end + 1):
            cell = ws.cell(row=row, column=col)
            cell.fill = self.TOTAL_FILL
            cell.font = self.TOTAL_FONT
            cell.border = self.BORDER_THIN

    def _autoajustar_columnas(self, ws):
        """Ajusta el ancho de las columnas automáticamente."""
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except Exception:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

    def _crear_hoja_portada(self, wb):
        """Crea la hoja de portada con información general."""
        ws = wb.create_sheet("Portada")

        # Título principal
        ws["B2"] = "REPORTE CONTABLE COMPLETO"
        ws["B2"].font = Font(size=18, bold=True, color="1F4E78")

        # Información de la empresa
        ws["B4"] = "Empresa:"
        ws["B4"].font = Font(bold=True, size=12)
        ws["C4"] = self.empresa.nombre
        ws["C4"].font = Font(size=12)

        ws["B5"] = "RUC/ID:"
        ws["B5"].font = Font(bold=True, size=11)
        ws["C5"] = f"Empresa #{self.empresa.id}"

        ws["B6"] = "Propietario:"
        ws["B6"].font = Font(bold=True, size=11)
        ws["C6"] = self.empresa.owner.get_full_name() or self.empresa.owner.username

        # Periodo del reporte
        ws["B8"] = "Periodo del Reporte:"
        ws["B8"].font = Font(bold=True, size=12, color="1F4E78")

        ws["B9"] = "Fecha Inicio:"
        ws["B9"].font = Font(bold=True)
        ws["C9"] = self.fecha_inicio.strftime("%d/%m/%Y")

        ws["B10"] = "Fecha Fin:"
        ws["B10"].font = Font(bold=True)
        ws["C10"] = self.fecha_fin.strftime("%d/%m/%Y")

        ws["B11"] = "Fecha de Generación:"
        ws["B11"].font = Font(bold=True)
        ws["C11"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Índice de contenidos
        ws["B13"] = "CONTENIDO DEL REPORTE"
        ws["B13"].font = Font(size=14, bold=True, color="1F4E78")

        contenido = [
            "1. Plan de Cuentas - Estructura jerárquica completa",
            "2. Balance de Comprobación - Movimientos del periodo",
            "3. Balance General - Situación financiera al corte",
            "4. Estado de Resultados - Utilidad del periodo",
            "5. Métricas Financieras - Ratios e indicadores",
            "6. Tendencias - Análisis temporal (ML)",
            "7. Top Cuentas - Cuentas más activas",
        ]

        for idx, item in enumerate(contenido, start=14):
            ws[f"B{idx}"] = item
            ws[f"B{idx}"].font = Font(size=10)

        # Ajustar anchos
        ws.column_dimensions["B"].width = 30
        ws.column_dimensions["C"].width = 40

    def _crear_hoja_plan_cuentas(self, wb):
        """Crea la hoja del plan de cuentas."""
        ws = wb.create_sheet("Plan de Cuentas")

        # Título
        ws["A1"] = "PLAN DE CUENTAS"
        self._aplicar_estilo_titulo(ws["A1"])
        ws["A2"] = f"Empresa: {self.empresa.nombre}"

        # Encabezados
        headers = ["Código", "Descripción", "Tipo", "Naturaleza", "Auxiliar", "Activa"]
        ws.append([])  # Fila vacía
        row_header = ws.max_row + 1
        for col, header in enumerate(headers, start=1):
            ws.cell(row=row_header, column=col, value=header)

        self._aplicar_estilo_header(ws, row_header, 1, len(headers))

        # Obtener cuentas ordenadas jerárquicamente
        cuentas = self.empresa.cuentas.all().select_related("padre").order_by("codigo")

        for cuenta in cuentas:
            # Calcular nivel de indentación
            nivel = cuenta.codigo.count(".")
            descripcion = "  " * nivel + cuenta.descripcion

            ws.append(
                [
                    cuenta.codigo,
                    descripcion,
                    cuenta.get_tipo_display(),
                    cuenta.get_naturaleza_display(),
                    "Sí" if cuenta.es_auxiliar else "No",
                    "Sí" if cuenta.activa else "No",
                ]
            )

            # Aplicar color según nivel
            row = ws.max_row
            if nivel == 0:  # Elemento
                for col in range(1, 7):
                    ws.cell(row=row, column=col).font = Font(bold=True, size=11)
            elif nivel == 1:  # Grupo
                for col in range(1, 7):
                    ws.cell(row=row, column=col).font = Font(bold=True, size=10)

        self._autoajustar_columnas(ws)

    def _crear_hoja_balance_comprobacion(self, wb):
        """Crea la hoja del balance de comprobación."""
        ws = wb.create_sheet("Balance de Comprobación")

        # Título
        ws["A1"] = "BALANCE DE COMPROBACIÓN"
        self._aplicar_estilo_titulo(ws["A1"])
        ws["A2"] = f"Empresa: {self.empresa.nombre}"
        ws["A3"] = (
            f"Periodo: {self.fecha_inicio.strftime('%d/%m/%Y')} - {self.fecha_fin.strftime('%d/%m/%Y')}"
        )

        # Encabezados
        headers = [
            "Código",
            "Cuenta",
            "Saldo Inicial Deudor",
            "Saldo Inicial Acreedor",
            "Debe",
            "Haber",
            "Saldo Final Deudor",
            "Saldo Final Acreedor",
        ]
        ws.append([])  # Fila vacía
        row_header = ws.max_row + 1
        for col, header in enumerate(headers, start=1):
            ws.cell(row=row_header, column=col, value=header)

        self._aplicar_estilo_header(ws, row_header, 1, len(headers))

        # Datos
        cuentas = self.empresa.cuentas.filter(es_auxiliar=True).order_by("codigo")

        total_si_deudor = Decimal("0")
        total_si_acreedor = Decimal("0")
        total_debe = Decimal("0")
        total_haber = Decimal("0")
        total_sf_deudor = Decimal("0")
        total_sf_acreedor = Decimal("0")

        for cuenta in cuentas:
            saldos = LibroMayorService.calcular_saldos_cuenta(
                cuenta=cuenta, fecha_inicio=self.fecha_inicio, fecha_fin=self.fecha_fin
            )

            # Solo incluir cuentas con movimientos
            if (
                saldos["saldo_inicial"] != 0
                or saldos["debe"] != 0
                or saldos["haber"] != 0
                or saldos["saldo_final"] != 0
            ):
                si_d = saldos["saldo_inicial"] if saldos["saldo_inicial"] > 0 else Decimal("0")
                si_a = abs(saldos["saldo_inicial"]) if saldos["saldo_inicial"] < 0 else Decimal("0")
                sf_d = saldos["saldo_final"] if saldos["saldo_final"] > 0 else Decimal("0")
                sf_a = abs(saldos["saldo_final"]) if saldos["saldo_final"] < 0 else Decimal("0")

                ws.append(
                    [
                        cuenta.codigo,
                        cuenta.descripcion,
                        float(si_d),
                        float(si_a),
                        float(saldos["debe"]),
                        float(saldos["haber"]),
                        float(sf_d),
                        float(sf_a),
                    ]
                )

                # Acumular totales
                total_si_deudor += si_d
                total_si_acreedor += si_a
                total_debe += saldos["debe"]
                total_haber += saldos["haber"]
                total_sf_deudor += sf_d
                total_sf_acreedor += sf_a

        # Fila de totales
        ws.append([])
        row_total = ws.max_row + 1
        ws.append(
            [
                "",
                "TOTALES",
                float(total_si_deudor),
                float(total_si_acreedor),
                float(total_debe),
                float(total_haber),
                float(total_sf_deudor),
                float(total_sf_acreedor),
            ]
        )

        self._aplicar_estilo_total(ws, row_total, 1, len(headers))

        # Formatear números
        for row in ws.iter_rows(min_row=row_header + 1, max_row=ws.max_row, min_col=3, max_col=8):
            for cell in row:
                if cell.value and isinstance(cell.value, int | float):
                    cell.number_format = "#,##0.00"

        self._autoajustar_columnas(ws)

    def _crear_hoja_balance_general(self, wb):
        """Crea la hoja del balance general."""
        ws = wb.create_sheet("Balance General")

        # Título
        ws["A1"] = "BALANCE GENERAL"
        self._aplicar_estilo_titulo(ws["A1"])
        ws["A2"] = f"Empresa: {self.empresa.nombre}"
        ws["A3"] = f"Al: {self.fecha_corte.strftime('%d/%m/%Y')}"

        bg = EstadosFinancierosService.balance_general(self.empresa, self.fecha_corte)

        # Encabezados
        headers = ["Sección", "Código", "Cuenta", "Saldo"]
        ws.append([])
        row_header = ws.max_row + 1
        for col, header in enumerate(headers, start=1):
            ws.cell(row=row_header, column=col, value=header)

        self._aplicar_estilo_header(ws, row_header, 1, len(headers))

        # ACTIVOS
        ws.append(["ACTIVO", "", "", ""])
        ws.cell(row=ws.max_row, column=1).font = self.SUBTITLE_FONT

        for det in bg["detalle_activos"]:
            ws.append(
                ["ACTIVO", det["cuenta"].codigo, det["cuenta"].descripcion, float(det["saldo"])]
            )

        # Total Activos
        row_total = ws.max_row + 1
        ws.append(["TOTAL ACTIVO", "", "", float(bg["activos"])])
        self._aplicar_estilo_total(ws, row_total, 1, 4)

        ws.append([])

        # PASIVOS
        ws.append(["PASIVO", "", "", ""])
        ws.cell(row=ws.max_row, column=1).font = self.SUBTITLE_FONT

        for det in bg["detalle_pasivos"]:
            ws.append(
                ["PASIVO", det["cuenta"].codigo, det["cuenta"].descripcion, float(det["saldo"])]
            )

        # Total Pasivos
        row_total = ws.max_row + 1
        ws.append(["TOTAL PASIVO", "", "", float(bg["pasivos"])])
        self._aplicar_estilo_total(ws, row_total, 1, 4)

        ws.append([])

        # PATRIMONIO
        ws.append(["PATRIMONIO", "", "", ""])
        ws.cell(row=ws.max_row, column=1).font = self.SUBTITLE_FONT

        for det in bg["detalle_patrimonio"]:
            ws.append(
                [
                    "PATRIMONIO",
                    det["cuenta"].codigo,
                    det["cuenta"].descripcion,
                    float(det["saldo"]),
                ]
            )

        # Total Patrimonio
        row_total = ws.max_row + 1
        ws.append(["TOTAL PATRIMONIO", "", "", float(bg["patrimonio"])])
        self._aplicar_estilo_total(ws, row_total, 1, 4)

        ws.append([])
        ws.append([])

        # Verificación
        row_verif = ws.max_row + 1
        ws.append(["VERIFICACIÓN", "", "", "SI ✓" if bg["balanceado"] else "NO ✗ (Descuadre)"])
        ws.cell(row=row_verif, column=1).font = Font(bold=True, color="FF0000")

        # Formatear números
        for row in ws.iter_rows(min_row=row_header + 1, max_row=ws.max_row, min_col=4, max_col=4):
            for cell in row:
                if cell.value and isinstance(cell.value, int | float):
                    cell.number_format = "#,##0.00"

        self._autoajustar_columnas(ws)

    def _crear_hoja_estado_resultados(self, wb):
        """Crea la hoja del estado de resultados."""
        ws = wb.create_sheet("Estado de Resultados")

        # Título
        ws["A1"] = "ESTADO DE RESULTADOS"
        self._aplicar_estilo_titulo(ws["A1"])
        ws["A2"] = f"Empresa: {self.empresa.nombre}"
        ws["A3"] = (
            f"Periodo: {self.fecha_inicio.strftime('%d/%m/%Y')} - {self.fecha_fin.strftime('%d/%m/%Y')}"
        )

        er = EstadosFinancierosService.estado_de_resultados(
            self.empresa, self.fecha_inicio, self.fecha_fin
        )

        # Encabezados
        headers = ["Sección", "Código", "Cuenta", "Monto"]
        ws.append([])
        row_header = ws.max_row + 1
        for col, header in enumerate(headers, start=1):
            ws.cell(row=row_header, column=col, value=header)

        self._aplicar_estilo_header(ws, row_header, 1, len(headers))

        # INGRESOS
        ws.append(["INGRESOS", "", "", ""])
        ws.cell(row=ws.max_row, column=1).font = self.SUBTITLE_FONT

        for det in er["detalle_ingresos"]:
            ws.append(
                ["INGRESOS", det["cuenta"].codigo, det["cuenta"].descripcion, float(det["monto"])]
            )

        row_total = ws.max_row + 1
        ws.append(["TOTAL INGRESOS", "", "", float(er["ingresos"])])
        self._aplicar_estilo_total(ws, row_total, 1, 4)

        ws.append([])

        # COSTOS
        ws.append(["COSTOS", "", "", ""])
        ws.cell(row=ws.max_row, column=1).font = self.SUBTITLE_FONT

        for det in er["detalle_costos"]:
            ws.append(
                ["COSTOS", det["cuenta"].codigo, det["cuenta"].descripcion, float(det["monto"])]
            )

        row_total = ws.max_row + 1
        ws.append(["TOTAL COSTOS", "", "", float(er["costos"])])
        self._aplicar_estilo_total(ws, row_total, 1, 4)

        ws.append([])

        # UTILIDAD BRUTA
        row_util_bruta = ws.max_row + 1
        ws.append(["UTILIDAD BRUTA", "", "", float(er["utilidad_bruta"])])
        ws.cell(row=row_util_bruta, column=1).font = Font(bold=True, size=11, color="1F4E78")
        ws.cell(row=row_util_bruta, column=4).font = Font(bold=True, size=11)

        ws.append([])

        # GASTOS
        ws.append(["GASTOS", "", "", ""])
        ws.cell(row=ws.max_row, column=1).font = self.SUBTITLE_FONT

        for det in er["detalle_gastos"]:
            ws.append(
                ["GASTOS", det["cuenta"].codigo, det["cuenta"].descripcion, float(det["monto"])]
            )

        row_total = ws.max_row + 1
        ws.append(["TOTAL GASTOS", "", "", float(er["gastos"])])
        self._aplicar_estilo_total(ws, row_total, 1, 4)

        ws.append([])
        ws.append([])

        # UTILIDAD NETA
        row_util_neta = ws.max_row + 1
        ws.append(["UTILIDAD NETA", "", "", float(er["utilidad_neta"])])
        ws.cell(row=row_util_neta, column=1).font = Font(bold=True, size=12, color="1F4E78")
        ws.cell(row=row_util_neta, column=4).font = Font(bold=True, size=12, color="1F4E78")
        ws.cell(row=row_util_neta, column=4).fill = PatternFill(
            start_color="E7E6E6", end_color="E7E6E6", fill_type="solid"
        )

        # Formatear números
        for row in ws.iter_rows(min_row=row_header + 1, max_row=ws.max_row, min_col=4, max_col=4):
            for cell in row:
                if cell.value and isinstance(cell.value, int | float):
                    cell.number_format = "#,##0.00"

        self._autoajustar_columnas(ws)

    def _crear_hoja_metricas_financieras(self, wb):
        """Crea la hoja de métricas financieras (ML)."""
        ws = wb.create_sheet("Métricas Financieras")

        # Título
        ws["A1"] = "MÉTRICAS FINANCIERAS Y RATIOS"
        self._aplicar_estilo_titulo(ws["A1"])
        ws["A2"] = f"Empresa: {self.empresa.nombre}"
        ws["A3"] = "Generado con Machine Learning / Analytics"

        try:
            ml_service = MLAnalyticsService(self.empresa)
            metrics = ml_service.get_dashboard_metrics()

            # Métricas principales
            ws.append([])
            ws["A5"] = "INDICADORES PRINCIPALES"
            ws["A5"].font = self.SUBTITLE_FONT

            ws.append([])
            ws.append(["Indicador", "Valor", "Interpretación"])
            self._aplicar_estilo_header(ws, 7, 1, 3)

            metricas_data = [
                ("Liquidez Corriente", f"{metrics['liquidez']:.2f}", "Capacidad de pago"),
                ("ROA (Rentabilidad Activos)", f"{metrics['roa']:.2f}%", "Eficiencia activos"),
                (
                    "Endeudamiento",
                    f"{metrics['endeudamiento']:.2f}%",
                    "Nivel de endeudamiento",
                ),
                ("Margen Neto", f"{metrics['margen_neto']:.2f}%", "Rentabilidad neta"),
            ]

            for metrica in metricas_data:
                ws.append(metrica)

            ws.append([])
            ws["A13"] = "COMPOSICIÓN PATRIMONIAL"
            ws["A13"].font = self.SUBTITLE_FONT

            ws.append([])
            ws.append(["Concepto", "Monto", "Porcentaje"])
            self._aplicar_estilo_header(ws, 15, 1, 3)

            total_patrimonio = metrics["activos"] + metrics["pasivos"] + metrics["patrimonio"] or 1

            composicion = [
                (
                    "Activos",
                    f"${metrics['activos']:,.2f}",
                    f"{(metrics['activos'] / total_patrimonio * 100):.2f}%",
                ),
                (
                    "Pasivos",
                    f"${metrics['pasivos']:,.2f}",
                    f"{(metrics['pasivos'] / total_patrimonio * 100):.2f}%",
                ),
                (
                    "Patrimonio",
                    f"${metrics['patrimonio']:,.2f}",
                    f"{(metrics['patrimonio'] / total_patrimonio * 100):.2f}%",
                ),
            ]

            for comp in composicion:
                ws.append(comp)

            ws.append([])
            ws["A20"] = "RESULTADOS DEL PERIODO"
            ws["A20"].font = self.SUBTITLE_FONT

            ws.append([])
            ws.append(["Concepto", "Monto"])
            self._aplicar_estilo_header(ws, 22, 1, 2)

            resultados = [
                ("Ingresos Totales", f"${metrics['ingresos']:,.2f}"),
                ("Costos Totales", f"${metrics['costos']:,.2f}"),
                ("Gastos Totales", f"${metrics['gastos']:,.2f}"),
                ("Utilidad Neta", f"${metrics['utilidad_neta']:,.2f}"),
            ]

            for res in resultados:
                ws.append(res)

        except Exception as e:
            ws.append([])
            ws.append([f"Error al calcular métricas: {str(e)}"])

        self._autoajustar_columnas(ws)

    def _crear_hoja_tendencias(self, wb):
        """Crea la hoja de análisis de tendencias (ML)."""
        ws = wb.create_sheet("Tendencias ML")

        # Título
        ws["A1"] = "ANÁLISIS DE TENDENCIAS (Machine Learning)"
        self._aplicar_estilo_titulo(ws["A1"])
        ws["A2"] = f"Empresa: {self.empresa.nombre}"
        ws["A3"] = "Serie temporal de ingresos y gastos - Últimos 12 meses"

        try:
            ml_service = MLAnalyticsService(self.empresa)
            data = ml_service.get_analytics_time_series(meses=12)

            ws.append([])
            ws.append(["Mes", "Ingresos", "Gastos", "Flujo Neto", "Tendencia Ingresos"])
            self._aplicar_estilo_header(ws, 5, 1, 5)

            if "series_mensuales" in data:
                for mes_data in data["series_mensuales"]:
                    flujo_neto = mes_data["ingresos"] - mes_data["gastos"]
                    ws.append(
                        [
                            mes_data["mes"],
                            float(mes_data["ingresos"]),
                            float(mes_data["gastos"]),
                            float(flujo_neto),
                            mes_data.get("tendencia", "N/A"),
                        ]
                    )

                # Formatear números
                for row in ws.iter_rows(min_row=6, max_row=ws.max_row, min_col=2, max_col=4):
                    for cell in row:
                        if cell.value and isinstance(cell.value, int | float):
                            cell.number_format = "#,##0.00"

        except Exception as e:
            ws.append([])
            ws.append([f"Error al generar tendencias: {str(e)}"])

        self._autoajustar_columnas(ws)

    def _crear_hoja_top_cuentas(self, wb):
        """Crea la hoja de top cuentas más activas."""
        ws = wb.create_sheet("Top Cuentas")

        # Título
        ws["A1"] = "TOP CUENTAS MÁS ACTIVAS"
        self._aplicar_estilo_titulo(ws["A1"])
        ws["A2"] = f"Empresa: {self.empresa.nombre}"
        ws["A3"] = (
            f"Periodo: {self.fecha_inicio.strftime('%d/%m/%Y')} - {self.fecha_fin.strftime('%d/%m/%Y')}"
        )

        # Obtener transacciones y agrupar por cuenta
        from django.db.models import Count, Sum

        from .models import EmpresaTransaccion, EstadoAsiento

        cuentas_activas = (
            EmpresaTransaccion.objects.filter(
                asiento__empresa=self.empresa,
                asiento__fecha__gte=self.fecha_inicio,
                asiento__fecha__lte=self.fecha_fin,
                asiento__estado=EstadoAsiento.CONFIRMADO,
            )
            .values("cuenta__codigo", "cuenta__descripcion", "cuenta__tipo")
            .annotate(
                num_transacciones=Count("id"),
                total_debe=Sum("debe"),
                total_haber=Sum("haber"),
            )
            .order_by("-num_transacciones")[:20]
        )

        ws.append([])
        ws.append(
            ["Ranking", "Código", "Cuenta", "Tipo", "# Transacciones", "Total Debe", "Total Haber"]
        )
        self._aplicar_estilo_header(ws, 5, 1, 7)

        for idx, cuenta in enumerate(cuentas_activas, start=1):
            ws.append(
                [
                    idx,
                    cuenta["cuenta__codigo"],
                    cuenta["cuenta__descripcion"],
                    cuenta["cuenta__tipo"],
                    cuenta["num_transacciones"],
                    float(cuenta["total_debe"] or 0),
                    float(cuenta["total_haber"] or 0),
                ]
            )

        # Formatear números
        for row in ws.iter_rows(min_row=6, max_row=ws.max_row, min_col=6, max_col=7):
            for cell in row:
                if cell.value and isinstance(cell.value, int | float):
                    cell.number_format = "#,##0.00"

        self._autoajustar_columnas(ws)
