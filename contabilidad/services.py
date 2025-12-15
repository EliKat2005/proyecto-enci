"""
Servicios de lógica de negocio para el módulo contable.
Implementa las mejores prácticas contables y validaciones.
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q, F
from decimal import Decimal
from datetime import date
from typing import Dict, List, Optional, Tuple

from .models import (
    EmpresaPlanCuenta,
    EmpresaAsiento,
    EmpresaTransaccion,
    Empresa,
    EmpresaTercero,
    TipoCuenta,
    NaturalezaCuenta,
    EstadoAsiento
)


class AsientoService:
    """Servicio para creación y validación de asientos contables."""
    
    # Monto límite para bancarización (en USD)
    LIMITE_BANCARIZACION = Decimal('1000.00')
    
    # Códigos de cuentas especiales (ajustar según plan de cuentas)
    CODIGO_CAJA_PATTERN = '1.1.01'  # Patrón para identificar cuentas de Caja
    CODIGO_BANCO_PATTERN = '1.1.02'  # Patrón para identificar cuentas de Bancos
    
    @classmethod
    @transaction.atomic
    def crear_asiento(
        cls,
        empresa: Empresa,
        fecha: date,
        descripcion: str,
        lineas: List[Dict],
        creado_por,
        auto_confirmar: bool = False
    ) -> EmpresaAsiento:
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
            EmpresaAsiento creado
        
        Raises:
            ValidationError: Si las validaciones fallan
        """
        # 1. Validar partida doble
        total_debe = sum(Decimal(str(l.get('debe', 0))) for l in lineas)
        total_haber = sum(Decimal(str(l.get('haber', 0))) for l in lineas)
        
        if total_debe != total_haber:
            raise ValidationError(
                f'El asiento no está balanceado. Debe: {total_debe}, Haber: {total_haber}. '
                f'Diferencia: {abs(total_debe - total_haber)}'
            )
        
        if total_debe == 0:
            raise ValidationError('El asiento no puede tener monto cero.')
        
        # 2. Validar periodo contable abierto
        cls._validar_periodo_abierto(empresa, fecha)
        
        # 3. Validar bancarización
        cls._validar_bancarizacion(empresa, lineas, total_debe)
        
        # 3. Crear asiento
        asiento = EmpresaAsiento(
            empresa=empresa,
            fecha=fecha,
            descripcion_general=descripcion,
            creado_por=creado_por,
            estado=EstadoAsiento.CONFIRMADO if auto_confirmar else EstadoAsiento.BORRADOR
        )
        asiento.save()
        
        # 4. Crear líneas
        for linea_data in lineas:
            cuenta = EmpresaPlanCuenta.objects.get(
                id=linea_data['cuenta_id'],
                empresa=empresa
            )

            # Tercero opcional
            tercero = None
            tercero_id = linea_data.get('tercero_id')
            if tercero_id:
                try:
                    tercero = EmpresaTercero.objects.get(id=tercero_id, empresa=empresa)
                except EmpresaTercero.DoesNotExist:
                    raise ValidationError(
                        f'El tercero con id {tercero_id} no pertenece a la empresa.'
                    )
            
            # Validar que la cuenta pueda recibir transacciones
            if not cuenta.puede_recibir_transacciones:
                raise ValidationError(
                    f'La cuenta {cuenta.codigo} - {cuenta.descripcion} no puede recibir transacciones. '
                    f'Debe ser auxiliar, sin cuentas hijas y estar activa.'
                )
            
            EmpresaTransaccion.objects.create(
                asiento=asiento,
                cuenta=cuenta,
                detalle_linea=linea_data.get('detalle', ''),
                debe=Decimal(str(linea_data.get('debe', 0))),
                haber=Decimal(str(linea_data.get('haber', 0))),
                tercero=tercero
            )
        
        # 5. Verificar balance final
        if not asiento.esta_balanceado:
            raise ValidationError('Error interno: el asiento no quedó balanceado.')
        
        return asiento
    
    @classmethod
    def _validar_periodo_abierto(cls, empresa: Empresa, fecha: date):
        """
        Valida que el periodo contable esté abierto para la fecha del asiento.
        
        Raises:
            ValidationError: Si el periodo está cerrado o bloqueado
        """
        from .models import PeriodoContable
        
        # Buscar periodo para el mes/año del asiento
        periodo = PeriodoContable.objects.filter(
            empresa=empresa,
            anio=fecha.year,
            mes=fecha.month
        ).first()
        
        if periodo and periodo.estado != PeriodoContable.EstadoPeriodo.ABIERTO:
            raise ValidationError(
                f'El periodo {fecha.month}/{fecha.year} está {periodo.estado}. '
                f'No se pueden crear asientos en periodos cerrados.'
            )
    
    @classmethod
    def _validar_bancarizacion(cls, empresa: Empresa, lineas: List[Dict], monto_total: Decimal):
        """
        Valida la regla de bancarización: operaciones > $1,000 deben usar banco, no caja.
        
        Raises:
            ValidationError: Si se viola la regla de bancarización
        """
        if monto_total <= cls.LIMITE_BANCARIZACION:
            return  # No aplica bancarización
        
        # Buscar si se usa cuenta de caja (más flexible)
        cuenta_ids = [l['cuenta_id'] for l in lineas]
        cuentas = EmpresaPlanCuenta.objects.filter(
            id__in=cuenta_ids,
            empresa=empresa
        ).select_related('padre')
        
        # Verificar múltiples formas de identificar caja
        for cuenta in cuentas:
            es_caja = (
                cls.CODIGO_CAJA_PATTERN in cuenta.codigo or  # Por código
                'caja' in cuenta.descripcion.lower() or      # Por descripción
                (cuenta.padre and 'caja' in cuenta.padre.descripcion.lower())  # Por padre
            )
            
            if es_caja:
                raise ValidationError(
                    f'ALERTA DE BANCARIZACIÓN: El monto total (${monto_total}) supera los '
                    f'${cls.LIMITE_BANCARIZACION}. La cuenta "{cuenta.codigo} - {cuenta.descripcion}" '
                    f'parece ser de caja. Debe usar una cuenta bancaria en lugar de caja. '
                    f'Esto es requerido por normativas tributarias.'
                )
    
    @classmethod
    @transaction.atomic
    def confirmar_asiento(cls, asiento: EmpresaAsiento) -> None:
        """
        Confirma un asiento en borrador.
        
        Raises:
            ValidationError: Si no puede confirmarse
        """
        if asiento.estado != EstadoAsiento.BORRADOR:
            raise ValidationError('Solo se pueden confirmar asientos en borrador.')
        
        if not asiento.esta_balanceado:
            raise ValidationError('No se puede confirmar un asiento desbalanceado.')
        
        if not asiento.lineas.exists():
            raise ValidationError('El asiento no tiene líneas de detalle.')
        
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
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        incluir_borradores: bool = False
    ) -> Dict:
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
        filtro = Q(cuenta=cuenta)
        
        # Estados permitidos
        if incluir_borradores:
            filtro &= Q(asiento__estado__in=[EstadoAsiento.BORRADOR, EstadoAsiento.CONFIRMADO])
        else:
            filtro &= Q(asiento__estado=EstadoAsiento.CONFIRMADO)
        
        # Calcular saldo inicial (antes de fecha_inicio)
        saldo_inicial = Decimal('0.00')
        if fecha_inicio:
            transacciones_anteriores = EmpresaTransaccion.objects.filter(
                filtro & Q(asiento__fecha__lt=fecha_inicio)
            ).aggregate(
                debe=Sum('debe'),
                haber=Sum('haber')
            )
            debe_ant = transacciones_anteriores['debe'] or Decimal('0.00')
            haber_ant = transacciones_anteriores['haber'] or Decimal('0.00')
            
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
        movimientos = EmpresaTransaccion.objects.filter(filtro).select_related(
            'asiento', 'cuenta'
        ).order_by('asiento__fecha', 'asiento__numero_asiento')
        
        totales = movimientos.aggregate(
            debe=Sum('debe'),
            haber=Sum('haber')
        )
        debe_periodo = totales['debe'] or Decimal('0.00')
        haber_periodo = totales['haber'] or Decimal('0.00')
        
        # Calcular saldo final
        if cuenta.naturaleza == NaturalezaCuenta.DEUDORA:
            saldo_final = saldo_inicial + debe_periodo - haber_periodo
        else:  # Acreedora
            saldo_final = saldo_inicial + haber_periodo - debe_periodo
        
        return {
            'cuenta': cuenta,
            'saldo_inicial': saldo_inicial,
            'debe': debe_periodo,
            'haber': haber_periodo,
            'saldo_final': saldo_final,
            'movimientos': movimientos,
            'naturaleza': cuenta.naturaleza
        }
    
    @classmethod
    def balance_de_comprobacion(
        cls,
        empresa: Empresa,
        fecha: Optional[date] = None,
        solo_auxiliares: bool = True
    ) -> List[Dict]:
        """
        Genera el Balance de Comprobación (todas las cuentas con sus saldos).
        
        Args:
            empresa: Empresa a analizar
            fecha: Fecha de corte (None = hoy)
            solo_auxiliares: Si solo muestra cuentas auxiliares (con movimiento)
        
        Returns:
            Lista de diccionarios con saldos por cuenta
        """
        cuentas = empresa.cuentas.filter(es_auxiliar=True) if solo_auxiliares else empresa.cuentas.all()
        
        resultado = []
        for cuenta in cuentas.select_related('padre').order_by('codigo'):
            saldos = cls.calcular_saldos_cuenta(cuenta, fecha_fin=fecha)
            
            # Omitir cuentas sin movimiento si solo_auxiliares=True
            if solo_auxiliares and saldos['debe'] == 0 and saldos['haber'] == 0:
                continue
            
            resultado.append({
                'cuenta': cuenta,
                'codigo': cuenta.codigo,
                'descripcion': cuenta.descripcion,
                'tipo': cuenta.tipo,
                'naturaleza': cuenta.naturaleza,
                'debe': saldos['debe'],
                'haber': saldos['haber'],
                'saldo_deudor': saldos['saldo_final'] if saldos['saldo_final'] > 0 and cuenta.naturaleza == NaturalezaCuenta.DEUDORA else Decimal('0.00'),
                'saldo_acreedor': saldos['saldo_final'] if saldos['saldo_final'] > 0 and cuenta.naturaleza == NaturalezaCuenta.ACREEDORA else Decimal('0.00'),
            })
        
        return resultado


class EstadosFinancierosService:
    """Servicio para generar Estados Financieros."""
    
    @classmethod
    def estado_de_resultados(
        cls,
        empresa: Empresa,
        fecha_inicio: date,
        fecha_fin: date
    ) -> Dict:
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
        # Obtener cuentas de resultado
        cuentas_ingreso = empresa.cuentas.filter(tipo=TipoCuenta.INGRESO, es_auxiliar=True)
        cuentas_costo = empresa.cuentas.filter(tipo=TipoCuenta.COSTO, es_auxiliar=True)
        cuentas_gasto = empresa.cuentas.filter(tipo=TipoCuenta.GASTO, es_auxiliar=True)
        
        # Calcular ingresos (naturaleza acreedora, el haber suma)
        ingresos_detalle = []
        total_ingresos = Decimal('0.00')
        for cuenta in cuentas_ingreso:
            saldos = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_inicio, fecha_fin)
            monto = saldos['haber'] - saldos['debe']  # Para ingresos (acreedora)
            if monto != 0:
                ingresos_detalle.append({
                    'cuenta': cuenta,
                    'monto': monto
                })
                total_ingresos += monto
        
        # Calcular costos (naturaleza deudora, el debe suma)
        costos_detalle = []
        total_costos = Decimal('0.00')
        for cuenta in cuentas_costo:
            saldos = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_inicio, fecha_fin)
            monto = saldos['debe'] - saldos['haber']  # Para costos (deudora)
            if monto != 0:
                costos_detalle.append({
                    'cuenta': cuenta,
                    'monto': monto
                })
                total_costos += monto
        
        # Calcular gastos (naturaleza deudora)
        gastos_detalle = []
        total_gastos = Decimal('0.00')
        for cuenta in cuentas_gasto:
            saldos = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_inicio, fecha_fin)
            monto = saldos['debe'] - saldos['haber']  # Para gastos (deudora)
            if monto != 0:
                gastos_detalle.append({
                    'cuenta': cuenta,
                    'monto': monto
                })
                total_gastos += monto
        
        utilidad_bruta = total_ingresos - total_costos
        utilidad_neta = utilidad_bruta - total_gastos
        
        return {
            'ingresos': total_ingresos,
            'costos': total_costos,
            'gastos': total_gastos,
            'utilidad_bruta': utilidad_bruta,
            'utilidad_neta': utilidad_neta,
            'detalle_ingresos': ingresos_detalle,
            'detalle_costos': costos_detalle,
            'detalle_gastos': gastos_detalle,
            'periodo': f'{fecha_inicio.strftime("%d/%m/%Y")} - {fecha_fin.strftime("%d/%m/%Y")}'
        }
    
    @classmethod
    def balance_general(
        cls,
        empresa: Empresa,
        fecha_corte: date
    ) -> Dict:
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
        # Obtener cuentas de balance
        cuentas_activo = empresa.cuentas.filter(tipo=TipoCuenta.ACTIVO, es_auxiliar=True)
        cuentas_pasivo = empresa.cuentas.filter(tipo=TipoCuenta.PASIVO, es_auxiliar=True)
        cuentas_patrimonio = empresa.cuentas.filter(tipo=TipoCuenta.PATRIMONIO, es_auxiliar=True)
        
        # Calcular activos (naturaleza deudora)
        activos_detalle = []
        total_activos = Decimal('0.00')
        for cuenta in cuentas_activo:
            saldos = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_fin=fecha_corte)
            if saldos['saldo_final'] != 0:
                activos_detalle.append({
                    'cuenta': cuenta,
                    'saldo': saldos['saldo_final']
                })
                total_activos += saldos['saldo_final']
        
        # Calcular pasivos (naturaleza acreedora)
        pasivos_detalle = []
        total_pasivos = Decimal('0.00')
        for cuenta in cuentas_pasivo:
            saldos = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_fin=fecha_corte)
            if saldos['saldo_final'] != 0:
                pasivos_detalle.append({
                    'cuenta': cuenta,
                    'saldo': saldos['saldo_final']
                })
                total_pasivos += saldos['saldo_final']
        
        # Calcular patrimonio (naturaleza acreedora)
        patrimonio_detalle = []
        total_patrimonio = Decimal('0.00')
        for cuenta in cuentas_patrimonio:
            saldos = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_fin=fecha_corte)
            if saldos['saldo_final'] != 0:
                patrimonio_detalle.append({
                    'cuenta': cuenta,
                    'saldo': saldos['saldo_final']
                })
                total_patrimonio += saldos['saldo_final']
        
        balanceado = abs(total_activos - (total_pasivos + total_patrimonio)) < Decimal('0.01')
        
        return {
            'activos': total_activos,
            'pasivos': total_pasivos,
            'patrimonio': total_patrimonio,
            'detalle_activos': activos_detalle,
            'detalle_pasivos': pasivos_detalle,
            'detalle_patrimonio': patrimonio_detalle,
            'balanceado': balanceado,
            'fecha_corte': fecha_corte.strftime("%d/%m/%Y"),
            'diferencia': total_activos - (total_pasivos + total_patrimonio)
        }
    
    @classmethod
    @transaction.atomic
    def asiento_de_cierre(
        cls,
        empresa: Empresa,
        fecha_cierre: date,
        usuario
    ) -> EmpresaAsiento:
        """
        Genera el asiento de cierre del ejercicio.
        Cancela todas las cuentas de resultado (Ingresos, Costos, Gastos)
        y lleva la utilidad/pérdida a Patrimonio.
        
        Returns:
            EmpresaAsiento de cierre creado
        """
        from datetime import datetime
        inicio_ejercicio = date(fecha_cierre.year, 1, 1)
        
        # Calcular estado de resultados
        resultados = cls.estado_de_resultados(empresa, inicio_ejercicio, fecha_cierre)
        
        # Buscar cuenta de "Resultados del Ejercicio" o similar (ajustar código)
        try:
            cuenta_resultados = empresa.cuentas.get(
                descripcion__icontains='Resultados del Ejercicio',
                tipo=TipoCuenta.PATRIMONIO,
                es_auxiliar=True
            )
        except EmpresaPlanCuenta.DoesNotExist:
            # Crear automáticamente bajo patrimonio si no existe
            try:
                cuenta_patrimonio = empresa.cuentas.get(codigo='3')
            except EmpresaPlanCuenta.DoesNotExist:
                raise ValidationError('No existe cuenta Patrimonio (3) en el plan de cuentas')
            cuenta_resultados = EmpresaPlanCuenta.objects.create(
                empresa=empresa,
                codigo='3.2',
                descripcion='Resultados del Ejercicio',
                tipo=TipoCuenta.PATRIMONIO,
                naturaleza=NaturalezaCuenta.ACREEDORA,
                es_auxiliar=True,
                estado_situacion=True,
                padre=cuenta_patrimonio,
                activa=True
            )
        
        # Preparar líneas del asiento de cierre
        lineas = []
        
        # Cerrar ingresos (Debe para cancelar saldo acreedor)
        for detalle in resultados['detalle_ingresos']:
            if detalle['monto'] > 0:
                lineas.append({
                    'cuenta_id': detalle['cuenta'].id,
                    'detalle': 'Cierre de ingresos del ejercicio',
                    'debe': detalle['monto'],
                    'haber': Decimal('0.00')
                })
        
        # Cerrar costos y gastos (Haber para cancelar saldo deudor)
        for detalle in resultados['detalle_costos'] + resultados['detalle_gastos']:
            if detalle['monto'] > 0:
                lineas.append({
                    'cuenta_id': detalle['cuenta'].id,
                    'detalle': 'Cierre de costos/gastos del ejercicio',
                    'debe': Decimal('0.00'),
                    'haber': detalle['monto']
                })
        
        # Línea de resultado (utilidad o pérdida)
        utilidad_neta = resultados['utilidad_neta']
        if utilidad_neta > 0:
            # Utilidad: Haber en patrimonio
            lineas.append({
                'cuenta_id': cuenta_resultados.id,
                'detalle': f'Utilidad del ejercicio {fecha_cierre.year}',
                'debe': Decimal('0.00'),
                'haber': utilidad_neta
            })
        elif utilidad_neta < 0:
            # Pérdida: Debe en patrimonio
            lineas.append({
                'cuenta_id': cuenta_resultados.id,
                'detalle': f'Pérdida del ejercicio {fecha_cierre.year}',
                'debe': abs(utilidad_neta),
                'haber': Decimal('0.00')
            })
        
        # Crear asiento de cierre
        asiento_cierre = AsientoService.crear_asiento(
            empresa=empresa,
            fecha=fecha_cierre,
            descripcion=f'ASIENTO DE CIERRE DEL EJERCICIO {fecha_cierre.year}',
            lineas=lineas,
            creado_por=usuario,
            auto_confirmar=True
        )
        
        return asiento_cierre
