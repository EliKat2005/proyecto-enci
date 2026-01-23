"""
Servicios de lógica de negocio para el módulo contable.
Implementa las mejores prácticas contables y validaciones.
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef, Q, Sum

from .models import (
    Empresa,
    EmpresaAsiento,
    EmpresaPlanCuenta,
    EmpresaTercero,
    EmpresaTransaccion,
    EstadoAsiento,
    NaturalezaCuenta,
    TipoCuenta,
)


class AsientoService:
    """Servicio para creación y validación de asientos contables."""

    # Monto límite para bancarización (en USD)
    LIMITE_BANCARIZACION = Decimal("1000.00")

    # Códigos de cuentas especiales (ajustar según plan de cuentas)
    CODIGO_CAJA_PATTERN = "1.1.1.01"  # Patrón para identificar cuentas de Caja/Efectivo
    CODIGO_BANCO_PATTERN = "1.1.1.03"  # Patrón para identificar cuentas de Bancos

    @classmethod
    @transaction.atomic
    def crear_asiento(
        cls,
        empresa: Empresa,
        fecha: date,
        descripcion: str,
        lineas: list[dict],
        creado_por,
        auto_confirmar: bool = False,
    ) -> tuple[EmpresaAsiento, list[str]]:
        """
        Crea un asiento contable con validaciones completas.

        Args:
            empresa: Empresa a la que pertenece el asiento
            fecha: Fecha del asiento
            descripcion: Descripción general
            lineas: Lista de diccionarios con estructura:
                [
                    {
                        'cuenta_id': int,
                        'detalle': str,
                        'debe': Decimal,
                        'haber': Decimal,
                        'tercero_id': Optional[int]
                    },
                    ...
                ]
            creado_por: Usuario que crea el asiento
            auto_confirmar: Si debe confirmarse automáticamente

        Returns:
            tuple: (EmpresaAsiento creado, lista de advertencias)

        Raises:
            ValidationError: Si las validaciones fallan
        """
        if not lineas:
            raise ValidationError("El asiento debe tener al menos una línea.")

        # 1. Validar y normalizar líneas + partida doble
        total_debe = Decimal("0.00")
        total_haber = Decimal("0.00")
        cuenta_ids: list[int] = []
        tercero_ids: list[int] = []
        lineas_norm: list[dict] = []

        for linea in lineas:
            if "cuenta_id" not in linea:
                raise ValidationError("Cada línea debe incluir cuenta_id.")

            try:
                cuenta_id = int(linea["cuenta_id"])
            except (TypeError, ValueError):
                raise ValidationError("cuenta_id inválido.")

            debe = Decimal(str(linea.get("debe", 0)))
            haber = Decimal(str(linea.get("haber", 0)))

            if debe < 0 or haber < 0:
                raise ValidationError("Los montos no pueden ser negativos.")
            if debe > 0 and haber > 0:
                raise ValidationError(
                    "Una línea no puede tener valores tanto en debe como en haber. Use líneas separadas."
                )
            if debe == 0 and haber == 0:
                raise ValidationError("Debe o Haber debe ser mayor a cero.")

            tercero_id = linea.get("tercero_id")
            if tercero_id:
                try:
                    tercero_ids.append(int(tercero_id))
                except (TypeError, ValueError):
                    raise ValidationError("tercero_id inválido.")

            cuenta_ids.append(cuenta_id)
            total_debe += debe
            total_haber += haber

            lineas_norm.append(
                {
                    "cuenta_id": cuenta_id,
                    "detalle": linea.get("detalle", ""),
                    "debe": debe,
                    "haber": haber,
                    "tercero_id": int(tercero_id) if tercero_id else None,
                }
            )

        if total_debe != total_haber:
            raise ValidationError(
                f"El asiento no está balanceado. Debe: {total_debe}, Haber: {total_haber}. "
                f"Diferencia: {abs(total_debe - total_haber)}"
            )

        if total_debe == 0:
            raise ValidationError("El asiento no puede tener monto cero.")

        # 2. Validar periodo contable abierto
        cls._validar_periodo_abierto(empresa, fecha)

        # 3. Validar bancarización (retorna advertencias, no bloquea)
        advertencias = cls._validar_bancarizacion(empresa, lineas, total_debe)

        # 3. Crear asiento
        asiento = EmpresaAsiento(
            empresa=empresa,
            fecha=fecha,
            descripcion_general=descripcion,
            creado_por=creado_por,
            estado=EstadoAsiento.CONFIRMADO if auto_confirmar else EstadoAsiento.BORRADOR,
        )
        asiento.save()

        # 4. Resolver cuentas/terceros en bloque (evita N+1) y validar cuentas hoja
        cuentas_qs = EmpresaPlanCuenta.objects.filter(id__in=cuenta_ids, empresa=empresa).annotate(
            _has_children=Exists(EmpresaPlanCuenta.objects.filter(padre=OuterRef("pk")))
        )
        cuentas_by_id = {c.id: c for c in cuentas_qs}
        if len(cuentas_by_id) != len(set(cuenta_ids)):
            raise ValidationError("Una o más cuentas no existen o no pertenecen a la empresa.")

        terceros_by_id = {}
        if tercero_ids:
            terceros_qs = EmpresaTercero.objects.filter(id__in=set(tercero_ids), empresa=empresa)
            terceros_by_id = {t.id: t for t in terceros_qs}
            if len(terceros_by_id) != len(set(tercero_ids)):
                raise ValidationError("Uno o más terceros no pertenecen a la empresa.")

        transacciones = []
        for linea_data in lineas_norm:
            cuenta = cuentas_by_id[linea_data["cuenta_id"]]

            # Validar que sea cuenta transaccional, activa y sin hijos
            tiene_hijos = bool(getattr(cuenta, "_has_children", False))
            puede_recibir = bool(cuenta.es_auxiliar) and bool(cuenta.activa) and not tiene_hijos

            if not puede_recibir:
                if not cuenta.es_auxiliar:
                    raise ValidationError(
                        f"La cuenta {cuenta.codigo} - {cuenta.descripcion} no es transaccional. "
                        f"Solo las cuentas marcadas como transaccionales pueden recibir movimientos."
                    )
                elif tiene_hijos:
                    raise ValidationError(
                        f"La cuenta {cuenta.codigo} - {cuenta.descripcion} no puede recibir transacciones "
                        f"porque tiene subcuentas. Use una cuenta hoja (sin subcuentas)."
                    )
                else:
                    raise ValidationError(
                        f"La cuenta {cuenta.codigo} - {cuenta.descripcion} está inactiva y no puede recibir transacciones."
                    )

            tercero = None
            tercero_id = linea_data.get("tercero_id")
            if tercero_id:
                tercero = terceros_by_id.get(tercero_id)

            transacciones.append(
                EmpresaTransaccion(
                    asiento=asiento,
                    cuenta=cuenta,
                    detalle_linea=linea_data.get("detalle", ""),
                    debe=linea_data["debe"],
                    haber=linea_data["haber"],
                    tercero=tercero,
                    creado_por=creado_por,
                )
            )

        # Bulk insert (las validaciones ya se realizaron arriba)
        EmpresaTransaccion.objects.bulk_create(transacciones, batch_size=1000)

        # 5. Verificar balance final
        if not asiento.esta_balanceado:
            raise ValidationError("Error interno: el asiento no quedó balanceado.")

        return asiento, advertencias

    @classmethod
    def _validar_periodo_abierto(cls, empresa: Empresa, fecha: date):
        """
        Valida que el periodo contable esté abierto para la fecha del asiento.

        Verifica si existe un cierre de periodo para el año del asiento.
        Si el periodo está cerrado y bloqueado, no se permiten nuevos asientos.

        Args:
            empresa: Empresa a validar
            fecha: Fecha del asiento a crear

        Raises:
            ValidationError: Si el periodo está cerrado y bloqueado
        """
        from .models import EmpresaCierrePeriodo

        # Buscar si existe un cierre para el año del asiento
        cierre = EmpresaCierrePeriodo.objects.filter(
            empresa=empresa, periodo=fecha.year, bloqueado=True
        ).first()

        if cierre:
            raise ValidationError(
                f"⛔ El periodo fiscal {fecha.year} está CERRADO. "
                f"No se pueden crear o modificar asientos en periodos cerrados. "
                f"Fecha de cierre: {cierre.fecha_cierre.strftime('%d/%m/%Y')}. "
                f"Cerrado por: {cierre.cerrado_por.get_full_name() if cierre.cerrado_por else 'Sistema'}."
            )

    @classmethod
    def _validar_bancarizacion(cls, empresa: Empresa, lineas: list[dict], monto_total: Decimal) -> list[str]:
        """
        Validación de bancarización desactivada.
        
        Anteriormente validaba que operaciones > $1,000 usen banco en lugar de caja.
        Esta validación ha sido desactivada para dar más flexibilidad operativa.

        Returns:
            list[str]: Lista vacía (validación desactivada)
        """
        # Validación desactivada - retornar lista vacía sin advertencias
        return []

    @classmethod
    @transaction.atomic
    def confirmar_asiento(cls, asiento: EmpresaAsiento) -> None:
        """
        Confirma un asiento en borrador.

        Raises:
            ValidationError: Si no puede confirmarse
        """
        if asiento.estado != EstadoAsiento.BORRADOR:
            raise ValidationError("Solo se pueden confirmar asientos en borrador.")

        if not asiento.esta_balanceado:
            raise ValidationError("No se puede confirmar un asiento desbalanceado.")

        if not asiento.lineas.exists():
            raise ValidationError("El asiento no tiene líneas de detalle.")

        asiento.estado = EstadoAsiento.CONFIRMADO
        asiento.save()

    @classmethod
    @transaction.atomic
    def anular_asiento(cls, asiento: EmpresaAsiento, usuario, motivo: str) -> EmpresaAsiento:
        """
        Anula un asiento confirmado creando un contra-asiento.

        Returns:
            EmpresaAsiento: El contra-asiento creado
        """
        return asiento.anular(usuario, motivo)


class LibroMayorService:
    """Servicio para cálculo del Libro Mayor (no persiste en BD)."""

    @classmethod
    def calcular_saldos_cuenta(
        cls,
        cuenta: EmpresaPlanCuenta,
        fecha_inicio: date | None = None,
        fecha_fin: date | None = None,
        incluir_borradores: bool = False,
    ) -> dict:
        """
        Calcula los saldos de una cuenta para un rango de fechas.

        Args:
            cuenta: Cuenta a analizar
            fecha_inicio: Fecha inicial (None = desde el principio)
            fecha_fin: Fecha final (None = hasta hoy)
            incluir_borradores: Si incluye asientos en borrador

        Returns:
            Dict con:
                - saldo_inicial: Decimal
                - debe: Decimal
                - haber: Decimal
                - saldo_final: Decimal
                - movimientos: QuerySet de transacciones
        """
        # Filtro base de transacciones
        # Si es cuenta padre (no auxiliar), incluir todas sus cuentas hijas
        if cuenta.es_auxiliar:
            # Cuenta auxiliar: solo sus propias transacciones
            filtro = Q(cuenta=cuenta)
        else:
            # Cuenta padre: incluir transacciones de todas las cuentas que empiezan con su código
            # Esto incluye la cuenta misma y todas sus subcuentas
            cuentas_relacionadas = EmpresaPlanCuenta.objects.filter(
                empresa=cuenta.empresa,
                codigo__startswith=cuenta.codigo
            )
            filtro = Q(cuenta__in=cuentas_relacionadas)

        # Estados permitidos (excluir anulados)
        if incluir_borradores:
            filtro &= Q(asiento__estado__in=[EstadoAsiento.BORRADOR, EstadoAsiento.CONFIRMADO])
        else:
            filtro &= Q(asiento__estado=EstadoAsiento.CONFIRMADO)
        
        # Siempre excluir asientos anulados y contra-asientos (asientos que anulan a otros)
        filtro &= Q(asiento__anulado=False) & Q(asiento__anula_a__isnull=True)

        # Calcular saldo inicial (antes de fecha_inicio)
        saldo_inicial = Decimal("0.00")
        if fecha_inicio:
            transacciones_anteriores = EmpresaTransaccion.objects.filter(
                filtro & Q(asiento__fecha__lt=fecha_inicio)
            ).aggregate(debe=Sum("debe"), haber=Sum("haber"))
            debe_ant = transacciones_anteriores["debe"] or Decimal("0.00")
            haber_ant = transacciones_anteriores["haber"] or Decimal("0.00")

            # Calcular según naturaleza de la cuenta
            if cuenta.naturaleza == NaturalezaCuenta.DEUDORA:
                saldo_inicial = debe_ant - haber_ant
            else:  # Acreedora
                saldo_inicial = haber_ant - debe_ant

        # Filtrar movimientos del período
        if fecha_inicio:
            filtro &= Q(asiento__fecha__gte=fecha_inicio)
        if fecha_fin:
            filtro &= Q(asiento__fecha__lte=fecha_fin)

        # Obtener movimientos y totales
        movimientos = (
            EmpresaTransaccion.objects.filter(filtro)
            .select_related("asiento", "cuenta")
            .order_by("asiento__fecha", "asiento__numero_asiento")
        )

        totales = movimientos.aggregate(debe=Sum("debe"), haber=Sum("haber"))
        debe_periodo = totales["debe"] or Decimal("0.00")
        haber_periodo = totales["haber"] or Decimal("0.00")

        # Calcular saldo final
        if cuenta.naturaleza == NaturalezaCuenta.DEUDORA:
            saldo_final = saldo_inicial + debe_periodo - haber_periodo
        else:  # Acreedora
            saldo_final = saldo_inicial + haber_periodo - debe_periodo

        return {
            "cuenta": cuenta,
            "saldo_inicial": saldo_inicial,
            "debe": debe_periodo,
            "haber": haber_periodo,
            "saldo_final": saldo_final,
            "movimientos": movimientos,
            "naturaleza": cuenta.naturaleza,
        }

    @classmethod
    def balance_de_comprobacion(
        cls, empresa: Empresa, fecha: date | None = None, solo_auxiliares: bool = True
    ) -> list[dict]:
        """
        Genera el Balance de Comprobación (todas las cuentas con sus saldos).

        Args:
            empresa: Empresa a analizar
            fecha: Fecha de corte (None = hoy)
            solo_auxiliares: Si solo muestra cuentas transaccionales (con movimiento)

        Returns:
            Lista de diccionarios con saldos por cuenta
        """
        cuentas = (
            empresa.cuentas.filter(es_auxiliar=True) if solo_auxiliares else empresa.cuentas.all()
        )

        resultado = []
        for cuenta in cuentas.select_related("padre").order_by("codigo"):
            saldos = cls.calcular_saldos_cuenta(cuenta, fecha_fin=fecha)

            # Omitir cuentas sin movimiento si solo_auxiliares=True
            if solo_auxiliares and saldos["debe"] == 0 and saldos["haber"] == 0:
                continue

            resultado.append(
                {
                    "cuenta": cuenta,
                    "codigo": cuenta.codigo,
                    "descripcion": cuenta.descripcion,
                    "tipo": cuenta.tipo,
                    "naturaleza": cuenta.naturaleza,
                    "debe": saldos["debe"],
                    "haber": saldos["haber"],
                    "saldo_deudor": saldos["saldo_final"]
                    if saldos["saldo_final"] > 0 and cuenta.naturaleza == NaturalezaCuenta.DEUDORA
                    else Decimal("0.00"),
                    "saldo_acreedor": saldos["saldo_final"]
                    if saldos["saldo_final"] > 0 and cuenta.naturaleza == NaturalezaCuenta.ACREEDORA
                    else Decimal("0.00"),
                }
            )

        return resultado


class EstadosFinancierosService:
    """Servicio para generar Estados Financieros."""

    @staticmethod
    def _agrupar_por_cuenta_padre(detalle_cuentas):
        """
        Agrupa cuentas auxiliares por su cuenta padre.
        
        Args:
            detalle_cuentas: Lista de dict con 'cuenta' y 'monto' o 'saldo'
            
        Returns:
            Lista de dict con:
                - cuenta_padre: EmpresaPlanCuenta
                - total: Decimal
                - cuentas_hijas: List[Dict]
        """
        from collections import defaultdict
        
        grupos = defaultdict(lambda: {'cuentas_hijas': [], 'total': Decimal('0.00'), 'cuenta_padre': None})
        
        for item in detalle_cuentas:
            cuenta = item['cuenta']
            monto = item.get('monto') or item.get('saldo', Decimal('0.00'))
            cuenta_padre = cuenta.get_grupo_principal()
            
            key = cuenta_padre.id
            
            if grupos[key]['cuenta_padre'] is None:
                grupos[key]['cuenta_padre'] = cuenta_padre
            
            grupos[key]['cuentas_hijas'].append({
                'cuenta': cuenta,
                'monto': monto
            })
            grupos[key]['total'] += monto
        
        # Convertir a lista y ordenar por código de cuenta padre
        resultado = sorted(
            grupos.values(),
            key=lambda x: x['cuenta_padre'].codigo
        )
        
        return resultado

    @classmethod
    def estado_de_resultados(cls, empresa: Empresa, fecha_inicio: date, fecha_fin: date) -> dict:
        """
        Genera el Estado de Resultados (Ingresos - Costos - Gastos).

        Returns:
            Dict con:
                - ingresos: Decimal
                - costos: Decimal
                - gastos: Decimal
                - utilidad_bruta: Decimal (Ingresos - Costos)
                - utilidad_neta: Decimal (Utilidad Bruta - Gastos)
                - detalle_ingresos: List[Dict]
                - detalle_costos: List[Dict]
                - detalle_gastos: List[Dict]
        """
        # Estrategia: Obtener cuentas con transacciones en el periodo
        # EXCLUIR asientos de cierre (que afectan cuentas 3.1.4 - Resultados)
        from django.db.models import Q, Sum, Exists, OuterRef
        
        # Identificar asientos de cierre: tienen transacciones en cuentas de Resultados (3.1.4)
        asientos_cierre_ids = EmpresaTransaccion.objects.filter(
            asiento__empresa=empresa,
            asiento__fecha__gte=fecha_inicio,
            asiento__fecha__lte=fecha_fin,
            asiento__estado=EstadoAsiento.CONFIRMADO,
            asiento__anulado=False,
            cuenta__codigo__startswith='3.1.4'
        ).values_list('asiento_id', flat=True)
        
        # Filtro de transacciones del periodo (excluyendo cierres)
        filtro_periodo = Q(
            empresatransaccion__asiento__fecha__gte=fecha_inicio,
            empresatransaccion__asiento__fecha__lte=fecha_fin,
            empresatransaccion__asiento__estado=EstadoAsiento.CONFIRMADO,
            empresatransaccion__asiento__anulado=False,
            empresatransaccion__asiento__anula_a__isnull=True
        ) & ~Q(empresatransaccion__asiento_id__in=asientos_cierre_ids)
        
        # Obtener cuentas que tienen transacciones en el periodo (sin cierres)
        cuentas_ingreso = empresa.cuentas.filter(tipo=TipoCuenta.INGRESO).filter(filtro_periodo).distinct()
        cuentas_costo = empresa.cuentas.filter(tipo=TipoCuenta.COSTO).filter(filtro_periodo).distinct()
        cuentas_gasto = empresa.cuentas.filter(tipo=TipoCuenta.GASTO).filter(filtro_periodo).distinct()

        # Calcular ingresos (naturaleza acreedora, el haber suma)
        ingresos_detalle = []
        total_ingresos = Decimal("0.00")
        
        for cuenta in cuentas_ingreso:
            # Calcular excluyendo asientos de cierre
            transacciones = EmpresaTransaccion.objects.filter(
                cuenta=cuenta,
                asiento__fecha__gte=fecha_inicio,
                asiento__fecha__lte=fecha_fin,
                asiento__estado=EstadoAsiento.CONFIRMADO,
                asiento__anulado=False,
                asiento__anula_a__isnull=True
            ).exclude(asiento_id__in=asientos_cierre_ids).aggregate(
                debe=Sum("debe"),
                haber=Sum("haber")
            )
            debe = transacciones["debe"] or Decimal("0.00")
            haber = transacciones["haber"] or Decimal("0.00")
            monto = haber - debe  # Para ingresos (acreedora)
            
            if abs(monto) > Decimal("0.01"):
                ingresos_detalle.append({"cuenta": cuenta, "monto": abs(monto)})
                total_ingresos += abs(monto)

        # Calcular costos (naturaleza deudora, el debe suma)
        costos_detalle = []
        total_costos = Decimal("0.00")
        
        for cuenta in cuentas_costo:
            transacciones = EmpresaTransaccion.objects.filter(
                cuenta=cuenta,
                asiento__fecha__gte=fecha_inicio,
                asiento__fecha__lte=fecha_fin,
                asiento__estado=EstadoAsiento.CONFIRMADO,
                asiento__anulado=False,
                asiento__anula_a__isnull=True
            ).exclude(asiento_id__in=asientos_cierre_ids).aggregate(
                debe=Sum("debe"),
                haber=Sum("haber")
            )
            debe = transacciones["debe"] or Decimal("0.00")
            haber = transacciones["haber"] or Decimal("0.00")
            monto = debe - haber  # Para costos (deudora)
            
            if abs(monto) > Decimal("0.01"):
                costos_detalle.append({"cuenta": cuenta, "monto": abs(monto)})
                total_costos += abs(monto)

        # Calcular gastos (naturaleza deudora)
        gastos_detalle = []
        total_gastos = Decimal("0.00")
        
        for cuenta in cuentas_gasto:
            transacciones = EmpresaTransaccion.objects.filter(
                cuenta=cuenta,
                asiento__fecha__gte=fecha_inicio,
                asiento__fecha__lte=fecha_fin,
                asiento__estado=EstadoAsiento.CONFIRMADO,
                asiento__anulado=False,
                asiento__anula_a__isnull=True
            ).exclude(asiento_id__in=asientos_cierre_ids).aggregate(
                debe=Sum("debe"),
                haber=Sum("haber")
            )
            debe = transacciones["debe"] or Decimal("0.00")
            haber = transacciones["haber"] or Decimal("0.00")
            monto = debe - haber  # Para gastos (deudora)
            
            if abs(monto) > Decimal("0.01"):
                gastos_detalle.append({"cuenta": cuenta, "monto": abs(monto)})
                total_gastos += abs(monto)

        utilidad_bruta = total_ingresos - total_costos
        utilidad_neta = utilidad_bruta - total_gastos

        # Agrupar por cuenta padre
        ingresos_agrupados = cls._agrupar_por_cuenta_padre(ingresos_detalle)
        costos_agrupados = cls._agrupar_por_cuenta_padre(costos_detalle)
        gastos_agrupados = cls._agrupar_por_cuenta_padre(gastos_detalle)

        return {
            "ingresos": total_ingresos,
            "costos": total_costos,
            "gastos": total_gastos,
            "utilidad_bruta": utilidad_bruta,
            "utilidad_neta": utilidad_neta,
            "detalle_ingresos": ingresos_detalle,
            "detalle_costos": costos_detalle,
            "detalle_gastos": gastos_detalle,
            "ingresos_agrupados": ingresos_agrupados,
            "costos_agrupados": costos_agrupados,
            "gastos_agrupados": gastos_agrupados,
            "periodo": f"{fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')}",
        }

    @classmethod
    def balance_general(cls, empresa: Empresa, fecha_corte: date) -> dict:
        """
        Genera el Balance General (Activo = Pasivo + Patrimonio).

        Returns:
            Dict con:
                - activos: Decimal
                - pasivos: Decimal
                - patrimonio: Decimal
                - detalle_activos: List[Dict]
                - detalle_pasivos: List[Dict]
                - detalle_patrimonio: List[Dict]
                - balanceado: bool
        """
        # Obtener solo cuentas auxiliares de balance (no cambiar, funciona correctamente)
        cuentas_activo = empresa.cuentas.filter(tipo=TipoCuenta.ACTIVO, es_auxiliar=True)
        cuentas_pasivo = empresa.cuentas.filter(tipo=TipoCuenta.PASIVO, es_auxiliar=True)
        cuentas_patrimonio = empresa.cuentas.filter(tipo=TipoCuenta.PATRIMONIO, es_auxiliar=True)

        # Calcular activos (naturaleza deudora)
        activos_detalle = []
        total_activos = Decimal("0.00")
        for cuenta in cuentas_activo:
            saldos = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_fin=fecha_corte)
            if saldos["saldo_final"] != 0:
                activos_detalle.append({"cuenta": cuenta, "saldo": saldos["saldo_final"]})
                total_activos += saldos["saldo_final"]

        # Calcular pasivos (naturaleza acreedora)
        pasivos_detalle = []
        total_pasivos = Decimal("0.00")
        for cuenta in cuentas_pasivo:
            saldos = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_fin=fecha_corte)
            if saldos["saldo_final"] != 0:
                pasivos_detalle.append({"cuenta": cuenta, "saldo": saldos["saldo_final"]})
                total_pasivos += saldos["saldo_final"]

        # Calcular patrimonio (naturaleza acreedora)
        patrimonio_detalle = []
        total_patrimonio = Decimal("0.00")
        for cuenta in cuentas_patrimonio:
            saldos = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_fin=fecha_corte)
            if saldos["saldo_final"] != 0:
                patrimonio_detalle.append({"cuenta": cuenta, "saldo": saldos["saldo_final"]})
                total_patrimonio += saldos["saldo_final"]

        # Calcular diferencia y validación de ecuación contable
        pasivos_mas_patrimonio = total_pasivos + total_patrimonio
        diferencia = total_activos - pasivos_mas_patrimonio
        balanceado = abs(diferencia) < Decimal("0.01")

        # Mensaje de advertencia si no cuadra
        mensaje_balance = None
        if not balanceado:
            mensaje_balance = (
                f"⚠️ ADVERTENCIA: El Balance General NO cuadra. "
                f"Diferencia: {diferencia:,.2f} "
                f"(Activos: {total_activos:,.2f} ≠ Pasivos + Patrimonio: {pasivos_mas_patrimonio:,.2f}). "
                f"Revise los asientos contables y corrija los errores."
            )

        # Agrupar por cuenta padre
        activos_agrupados = cls._agrupar_por_cuenta_padre(activos_detalle)
        pasivos_agrupados = cls._agrupar_por_cuenta_padre(pasivos_detalle)
        patrimonio_agrupados = cls._agrupar_por_cuenta_padre(patrimonio_detalle)

        return {
            "activos": total_activos,
            "pasivos": total_pasivos,
            "patrimonio": total_patrimonio,
            "pasivos_mas_patrimonio": pasivos_mas_patrimonio,
            "detalle_activos": activos_detalle,
            "detalle_pasivos": pasivos_detalle,
            "detalle_patrimonio": patrimonio_detalle,
            "activos_agrupados": activos_agrupados,
            "pasivos_agrupados": pasivos_agrupados,
            "patrimonio_agrupados": patrimonio_agrupados,
            "balanceado": balanceado,
            "fecha_corte": fecha_corte.strftime("%d/%m/%Y"),
            "diferencia": diferencia,
            "mensaje_balance": mensaje_balance,
        }

    @classmethod
    @transaction.atomic
    def asiento_de_cierre(cls, empresa: Empresa, fecha_cierre: date, usuario) -> EmpresaAsiento:
        """
        Genera el asiento de cierre del ejercicio.
        Cancela todas las cuentas de resultado (Ingresos, Costos, Gastos)
        y lleva la utilidad/pérdida a Patrimonio.

        Returns:
            EmpresaAsiento de cierre creado
        """
        inicio_ejercicio = date(fecha_cierre.year, 1, 1)

        # Calcular estado de resultados
        resultados = cls.estado_de_resultados(empresa, inicio_ejercicio, fecha_cierre)

        # Buscar cuenta de "Resultados del Ejercicio" o similar (ajustar código)
        try:
            cuenta_resultados = empresa.cuentas.get(
                descripcion__icontains="Resultados del Ejercicio",
                tipo=TipoCuenta.PATRIMONIO,
                es_auxiliar=True,
            )
        except EmpresaPlanCuenta.DoesNotExist:
            # Crear automáticamente bajo patrimonio si no existe
            try:
                cuenta_patrimonio = empresa.cuentas.get(codigo="3")
            except EmpresaPlanCuenta.DoesNotExist:
                raise ValidationError("No existe cuenta Patrimonio (3) en el plan de cuentas")
            cuenta_resultados = EmpresaPlanCuenta.objects.create(
                empresa=empresa,
                codigo="3.2",
                descripcion="Resultados del Ejercicio",
                tipo=TipoCuenta.PATRIMONIO,
                naturaleza=NaturalezaCuenta.ACREEDORA,
                es_auxiliar=True,
                padre=cuenta_patrimonio,
                activa=True,
            )

        # Preparar líneas del asiento de cierre
        lineas = []

        # Cerrar ingresos (Debe para cancelar saldo acreedor)
        for detalle in resultados["detalle_ingresos"]:
            if detalle["monto"] > 0:
                lineas.append(
                    {
                        "cuenta_id": detalle["cuenta"].id,
                        "detalle": "Cierre de ingresos del ejercicio",
                        "debe": detalle["monto"],
                        "haber": Decimal("0.00"),
                    }
                )

        # Cerrar costos y gastos (Haber para cancelar saldo deudor)
        for detalle in resultados["detalle_costos"] + resultados["detalle_gastos"]:
            if detalle["monto"] > 0:
                lineas.append(
                    {
                        "cuenta_id": detalle["cuenta"].id,
                        "detalle": "Cierre de costos/gastos del ejercicio",
                        "debe": Decimal("0.00"),
                        "haber": detalle["monto"],
                    }
                )

        # Línea de resultado (utilidad o pérdida)
        utilidad_neta = resultados["utilidad_neta"]
        if utilidad_neta > 0:
            # Utilidad: Haber en patrimonio
            lineas.append(
                {
                    "cuenta_id": cuenta_resultados.id,
                    "detalle": f"Utilidad del ejercicio {fecha_cierre.year}",
                    "debe": Decimal("0.00"),
                    "haber": utilidad_neta,
                }
            )
        elif utilidad_neta < 0:
            # Pérdida: Debe en patrimonio
            lineas.append(
                {
                    "cuenta_id": cuenta_resultados.id,
                    "detalle": f"Pérdida del ejercicio {fecha_cierre.year}",
                    "debe": abs(utilidad_neta),
                    "haber": Decimal("0.00"),
                }
            )

        # Crear asiento de cierre
        asiento_cierre, _ = AsientoService.crear_asiento(
            empresa=empresa,
            fecha=fecha_cierre,
            descripcion=f"ASIENTO DE CIERRE DEL EJERCICIO {fecha_cierre.year}",
            lineas=lineas,
            creado_por=usuario,
            auto_confirmar=True,
        )

        return asiento_cierre
