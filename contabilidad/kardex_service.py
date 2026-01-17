"""
Servicio de Control de Inventarios (Kardex).

Implementa los métodos de valoración de inventarios:
- PEPS (Primero en Entrar, Primero en Salir / FIFO)
- UEPS (Último en Entrar, Primero en Salir / LIFO)
- Promedio Ponderado

Gestiona las entradas y salidas de productos con integración contable automática.
"""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    EmpresaAsiento,
    MetodoValoracion,
    MovimientoKardex,
    ProductoInventario,
    TipoMovimientoKardex,
)
from .services import AsientoService


class KardexService:
    """Servicio para gestión de inventarios perpetuos (Kardex)."""

    @classmethod
    @transaction.atomic
    def registrar_entrada(
        cls,
        producto: ProductoInventario,
        fecha: date,
        cantidad: Decimal,
        costo_unitario: Decimal,
        tipo_movimiento: str = TipoMovimientoKardex.ENTRADA,
        documento_referencia: str = "",
        tercero=None,
        observaciones: str = "",
        creado_por=None,
        generar_asiento: bool = True,
    ) -> MovimientoKardex:
        """
        Registra una entrada de mercancía al inventario.

        Args:
            producto: Producto al que pertenece el movimiento
            fecha: Fecha del movimiento
            cantidad: Cantidad de unidades que ingresan (debe ser positiva)
            costo_unitario: Costo unitario de compra
            tipo_movimiento: Tipo de entrada (ENTRADA, AJUSTE_ENTRADA, DEVOLUCION_VENTA)
            documento_referencia: Número de factura, orden de compra, etc.
            tercero: Proveedor (opcional)
            observaciones: Notas adicionales
            creado_por: Usuario que registra el movimiento
            generar_asiento: Si debe crear el asiento contable automáticamente

        Returns:
            MovimientoKardex creado

        Raises:
            ValidationError: Si los datos son inválidos
        """
        # Validaciones
        if cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero.")
        if costo_unitario < 0:
            raise ValidationError("El costo unitario no puede ser negativo.")

        # Obtener último movimiento para calcular nuevo saldo
        ultimo = (
            MovimientoKardex.objects.filter(producto=producto).order_by("-fecha", "-id").first()
        )

        if ultimo:
            cantidad_anterior = ultimo.cantidad_saldo
            valor_anterior = ultimo.valor_total_saldo
        else:
            cantidad_anterior = Decimal("0.000")
            valor_anterior = Decimal("0.00")

        # Calcular nuevos valores
        cantidad_nueva = cantidad_anterior + cantidad
        valor_ingreso = cantidad * costo_unitario

        # Calcular costo promedio según método de valoración
        if producto.metodo_valoracion == MetodoValoracion.PROMEDIO:
            # Promedio Ponderado: (Valor anterior + Valor ingreso) / Cantidad nueva
            if cantidad_nueva > 0:
                costo_promedio_nuevo = (valor_anterior + valor_ingreso) / cantidad_nueva
            else:
                costo_promedio_nuevo = Decimal("0.00")
        elif producto.metodo_valoracion == MetodoValoracion.PEPS:
            # PEPS: Mantener costo promedio (las salidas afectan el costo)
            if cantidad_nueva > 0:
                costo_promedio_nuevo = (valor_anterior + valor_ingreso) / cantidad_nueva
            else:
                costo_promedio_nuevo = Decimal("0.00")
        elif producto.metodo_valoracion == MetodoValoracion.UEPS:
            # UEPS: Mantener costo promedio (las salidas afectan el costo)
            if cantidad_nueva > 0:
                costo_promedio_nuevo = (valor_anterior + valor_ingreso) / cantidad_nueva
            else:
                costo_promedio_nuevo = Decimal("0.00")
        else:
            costo_promedio_nuevo = costo_unitario

        valor_total_nuevo = cantidad_nueva * costo_promedio_nuevo

        # Crear movimiento Kardex
        asiento = None
        if generar_asiento:
            # Generar asiento contable automático
            # Debe: Inventario (Activo)
            # Haber: Caja/Banco o Cuentas por Pagar (según sea contado o crédito)
            asiento = cls._generar_asiento_entrada(
                producto=producto,
                fecha=fecha,
                cantidad=cantidad,
                costo_unitario=costo_unitario,
                valor_total=valor_ingreso,
                tercero=tercero,
                documento=documento_referencia,
                creado_por=creado_por,
            )

        movimiento = MovimientoKardex.objects.create(
            producto=producto,
            fecha=fecha,
            tipo_movimiento=tipo_movimiento,
            cantidad=cantidad,
            costo_unitario=costo_unitario,
            valor_total_movimiento=valor_ingreso,
            cantidad_saldo=cantidad_nueva,
            costo_promedio=costo_promedio_nuevo,
            valor_total_saldo=valor_total_nuevo,
            asiento=asiento,
            documento_referencia=documento_referencia,
            tercero=tercero,
            observaciones=observaciones,
            creado_por=creado_por,
        )

        return movimiento

    @classmethod
    @transaction.atomic
    def registrar_salida(
        cls,
        producto: ProductoInventario,
        fecha: date,
        cantidad: Decimal,
        tipo_movimiento: str = TipoMovimientoKardex.SALIDA,
        documento_referencia: str = "",
        tercero=None,
        observaciones: str = "",
        creado_por=None,
        generar_asiento: bool = True,
    ) -> MovimientoKardex:
        """
        Registra una salida de mercancía del inventario.

        Args:
            producto: Producto al que pertenece el movimiento
            fecha: Fecha del movimiento
            cantidad: Cantidad de unidades que salen (debe ser positiva)
            tipo_movimiento: Tipo de salida (SALIDA, AJUSTE_SALIDA, DEVOLUCION_COMPRA)
            documento_referencia: Número de factura, guía de despacho, etc.
            tercero: Cliente (opcional)
            observaciones: Notas adicionales
            creado_por: Usuario que registra el movimiento
            generar_asiento: Si debe crear el asiento contable automáticamente

        Returns:
            MovimientoKardex creado

        Raises:
            ValidationError: Si los datos son inválidos o hay stock insuficiente
        """
        # Validaciones
        if cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero.")

        # Obtener último movimiento
        ultimo = (
            MovimientoKardex.objects.filter(producto=producto).order_by("-fecha", "-id").first()
        )

        if not ultimo:
            raise ValidationError(
                f"No hay stock disponible del producto {producto.sku} - {producto.nombre}."
            )

        cantidad_anterior = ultimo.cantidad_saldo
        costo_promedio_anterior = ultimo.costo_promedio

        # Validar stock suficiente
        if cantidad_anterior < cantidad:
            raise ValidationError(
                f"Stock insuficiente. Disponible: {cantidad_anterior} {producto.unidad_medida}, "
                f"Solicitado: {cantidad} {producto.unidad_medida}."
            )

        # Calcular costo de salida según método de valoración
        if producto.metodo_valoracion == MetodoValoracion.PROMEDIO:
            # Promedio Ponderado: usar costo promedio actual
            costo_salida = costo_promedio_anterior
        elif producto.metodo_valoracion == MetodoValoracion.PEPS:
            # PEPS: En implementación simplificada, usar costo promedio
            # (implementación completa requeriría tabla de lotes)
            costo_salida = costo_promedio_anterior
        elif producto.metodo_valoracion == MetodoValoracion.UEPS:
            # UEPS: En implementación simplificada, usar costo promedio
            # (implementación completa requeriría tabla de lotes)
            costo_salida = costo_promedio_anterior
        else:
            costo_salida = costo_promedio_anterior

        # Calcular nuevos valores
        cantidad_nueva = cantidad_anterior - cantidad
        valor_salida = cantidad * costo_salida
        valor_total_nuevo = cantidad_nueva * costo_promedio_anterior

        # Crear movimiento Kardex
        asiento = None
        if generar_asiento:
            # Generar asiento contable automático
            # Debe: Costo de Ventas (Costo)
            # Haber: Inventario (Activo)
            asiento = cls._generar_asiento_salida(
                producto=producto,
                fecha=fecha,
                cantidad=cantidad,
                costo_unitario=costo_salida,
                valor_total=valor_salida,
                tercero=tercero,
                documento=documento_referencia,
                creado_por=creado_por,
            )

        movimiento = MovimientoKardex.objects.create(
            producto=producto,
            fecha=fecha,
            tipo_movimiento=tipo_movimiento,
            cantidad=cantidad,
            costo_unitario=costo_salida,
            valor_total_movimiento=valor_salida,
            cantidad_saldo=cantidad_nueva,
            costo_promedio=costo_promedio_anterior,
            valor_total_saldo=valor_total_nuevo,
            asiento=asiento,
            documento_referencia=documento_referencia,
            tercero=tercero,
            observaciones=observaciones,
            creado_por=creado_por,
        )

        return movimiento

    @classmethod
    def obtener_kardex_producto(
        cls, producto: ProductoInventario, fecha_inicio: date = None, fecha_fin: date = None
    ) -> dict:
        """
        Genera el reporte de Kardex de un producto.

        Args:
            producto: Producto a consultar
            fecha_inicio: Fecha inicial del reporte (opcional)
            fecha_fin: Fecha final del reporte (opcional)

        Returns:
            Dict con:
                - movimientos: QuerySet de MovimientoKardex
                - saldo_inicial: Saldo antes del periodo
                - saldo_final: Saldo al final del periodo
                - total_entradas: Cantidad total de entradas
                - total_salidas: Cantidad total de salidas
                - valor_inicial: Valor del inventario inicial
                - valor_final: Valor del inventario final
        """
        qs = MovimientoKardex.objects.filter(producto=producto).order_by("fecha", "id")

        # Calcular saldo inicial (antes del periodo)
        saldo_inicial = Decimal("0.000")
        valor_inicial = Decimal("0.00")
        if fecha_inicio:
            movimiento_anterior = (
                qs.filter(fecha__lt=fecha_inicio).order_by("-fecha", "-id").first()
            )
            if movimiento_anterior:
                saldo_inicial = movimiento_anterior.cantidad_saldo
                valor_inicial = movimiento_anterior.valor_total_saldo

        # Filtrar movimientos del periodo
        if fecha_inicio:
            qs = qs.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(fecha__lte=fecha_fin)

        movimientos = list(qs)

        # Calcular totales
        total_entradas = Decimal("0.000")
        total_salidas = Decimal("0.000")

        for mov in movimientos:
            if mov.es_entrada:
                total_entradas += mov.cantidad
            elif mov.es_salida:
                total_salidas += mov.cantidad

        # Saldo final
        ultimo = movimientos[-1] if movimientos else None
        if ultimo:
            saldo_final = ultimo.cantidad_saldo
            valor_final = ultimo.valor_total_saldo
        else:
            saldo_final = saldo_inicial
            valor_final = valor_inicial

        return {
            "producto": producto,
            "movimientos": movimientos,
            "saldo_inicial": saldo_inicial,
            "valor_inicial": valor_inicial,
            "total_entradas": total_entradas,
            "total_salidas": total_salidas,
            "saldo_final": saldo_final,
            "valor_final": valor_final,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
        }

    @classmethod
    def _generar_asiento_entrada(
        cls,
        producto: ProductoInventario,
        fecha: date,
        cantidad: Decimal,
        costo_unitario: Decimal,
        valor_total: Decimal,
        tercero,
        documento: str,
        creado_por,
    ) -> EmpresaAsiento:
        """
        Genera el asiento contable para una entrada de inventario.

        Debe: Inventario (Activo - cuenta_inventario del producto)
        Haber: Caja/Banco o Cuentas por Pagar
        """
        # Por simplicidad, asumimos pago de contado con caja
        # En implementación real, debería preguntar forma de pago
        try:
            cuenta_caja = producto.empresa.cuentas.filter(
                codigo__startswith="1.1.01", es_auxiliar=True, activa=True
            ).first()
        except Exception:
            cuenta_caja = None

        if not cuenta_caja:
            raise ValidationError(
                "No se encontró cuenta de Caja (1.1.01.x) para registrar el pago. "
                "Configure una cuenta de caja auxiliar en el plan de cuentas."
            )

        lineas = [
            {
                "cuenta_id": producto.cuenta_inventario.id,
                "detalle": f"Compra inventario: {producto.nombre} - {cantidad} {producto.unidad_medida} @ ${costo_unitario}",
                "debe": str(valor_total),
                "haber": "0",
                "tercero_id": tercero.id if tercero else None,
            },
            {
                "cuenta_id": cuenta_caja.id,
                "detalle": f"Pago compra {documento or 'S/N'}",
                "debe": "0",
                "haber": str(valor_total),
                "tercero_id": tercero.id if tercero else None,
            },
        ]

        asiento = AsientoService.crear_asiento(
            empresa=producto.empresa,
            fecha=fecha,
            descripcion=f"Entrada inventario: {producto.sku} - {documento or 'Sin documento'}",
            lineas=lineas,
            creado_por=creado_por,
            auto_confirmar=True,
        )

        return asiento

    @classmethod
    def _generar_asiento_salida(
        cls,
        producto: ProductoInventario,
        fecha: date,
        cantidad: Decimal,
        costo_unitario: Decimal,
        valor_total: Decimal,
        tercero,
        documento: str,
        creado_por,
    ) -> EmpresaAsiento:
        """
        Genera el asiento contable para una salida de inventario.

        Debe: Costo de Ventas (Costo - cuenta_costo_venta del producto)
        Haber: Inventario (Activo - cuenta_inventario del producto)
        """
        if not producto.cuenta_costo_venta:
            raise ValidationError(
                f"El producto {producto.sku} no tiene configurada una cuenta de Costo de Ventas. "
                f"Configure una en el maestro del producto."
            )

        lineas = [
            {
                "cuenta_id": producto.cuenta_costo_venta.id,
                "detalle": f"Costo venta: {producto.nombre} - {cantidad} {producto.unidad_medida} @ ${costo_unitario}",
                "debe": str(valor_total),
                "haber": "0",
                "tercero_id": tercero.id if tercero else None,
            },
            {
                "cuenta_id": producto.cuenta_inventario.id,
                "detalle": f"Salida inventario {documento or 'S/N'}",
                "debe": "0",
                "haber": str(valor_total),
                "tercero_id": tercero.id if tercero else None,
            },
        ]

        asiento = AsientoService.crear_asiento(
            empresa=producto.empresa,
            fecha=fecha,
            descripcion=f"Salida inventario: {producto.sku} - {documento or 'Sin documento'}",
            lineas=lineas,
            creado_por=creado_por,
            auto_confirmar=True,
        )

        return asiento
