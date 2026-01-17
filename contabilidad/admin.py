from django.contrib import admin, messages

from .models import (
    Empresa,
    EmpresaAsiento,
    EmpresaCierrePeriodo,
    EmpresaComment,
    EmpresaPlanCuenta,
    EmpresaSupervisor,
    EmpresaTercero,
    EmpresaTransaccion,
    MovimientoKardex,
    PeriodoContable,
    PlanDeCuentas,
    ProductoInventario,
)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre",
        "owner",
        "is_template",
        "visible_to_supervisor",
        "join_code",
        "created_at",
    )
    search_fields = ("nombre", "owner__username", "join_code")
    list_filter = ("is_template", "visible_to_supervisor", "created_at")
    raw_id_fields = ("owner", "original")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(EmpresaPlanCuenta)
class EmpresaPlanCuentaAdmin(admin.ModelAdmin):
    list_display = (
        "empresa",
        "codigo",
        "descripcion",
        "tipo",
        "naturaleza",
        "es_auxiliar",
        "activa",
    )
    search_fields = ("codigo", "descripcion", "empresa__nombre")
    list_filter = ("tipo", "naturaleza", "es_auxiliar", "activa")
    raw_id_fields = ("empresa", "padre")


@admin.register(EmpresaAsiento)
class EmpresaAsientoAdmin(admin.ModelAdmin):
    list_display = ("id", "empresa", "fecha", "creado_por", "estado", "fecha_creacion")
    search_fields = ("descripcion_general", "empresa__nombre")
    list_filter = ("estado", "fecha")
    raw_id_fields = ("empresa", "creado_por")
    readonly_fields = ("fecha_creacion", "fecha_modificacion")
    date_hierarchy = "fecha"


@admin.register(EmpresaTransaccion)
class EmpresaTransaccionAdmin(admin.ModelAdmin):
    list_display = ("asiento", "cuenta", "detalle_linea", "debe", "haber")
    search_fields = ("detalle_linea", "asiento__empresa__nombre")
    raw_id_fields = ("asiento", "cuenta")
    list_filter = ("asiento__estado",)


@admin.register(EmpresaSupervisor)
class EmpresaSupervisorAdmin(admin.ModelAdmin):
    list_display = ("empresa", "docente", "created_at")
    search_fields = ("empresa__nombre", "docente__username")
    raw_id_fields = ("empresa", "docente")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(PeriodoContable)
class PeriodoContableAdmin(admin.ModelAdmin):
    list_display = ("empresa", "anio", "mes", "estado", "fecha_cierre", "cerrado_por")
    search_fields = ("empresa__nombre",)
    list_filter = ("estado", "anio", "mes")
    raw_id_fields = ("empresa", "cerrado_por")
    readonly_fields = ("fecha_cierre",)
    date_hierarchy = "fecha_cierre"

    def has_delete_permission(self, request, obj=None):
        # No permitir eliminar periodos cerrados
        if obj and obj.estado == PeriodoContable.EstadoPeriodo.CERRADO:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(EmpresaComment)
class EmpresaCommentAdmin(admin.ModelAdmin):
    list_display = ("empresa", "section", "author", "created_at")
    search_fields = ("content", "empresa__nombre", "author__username")
    list_filter = ("section", "created_at")
    raw_id_fields = ("empresa", "author")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


# --- Admin para PlanDeCuentas ---
# Lo registramos de forma estándar, pero con mejoras de UI.
@admin.register(PlanDeCuentas)
class PlanDeCuentasAdmin(admin.ModelAdmin):
    list_display = ("codigo", "descripcion", "tipo", "naturaleza", "es_auxiliar", "padre")
    list_filter = ("tipo", "naturaleza", "es_auxiliar")
    search_fields = ("codigo", "descripcion")
    raw_id_fields = ("padre",)


# --- Admin para EmpresaTercero (Clientes, Proveedores, etc) ---
@admin.register(EmpresaTercero)
class EmpresaTerceroAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "numero_identificacion",
        "tipo",
        "empresa",
        "activo",
        "fecha_creacion",
    )
    search_fields = ("nombre", "numero_identificacion", "empresa__nombre")
    list_filter = ("tipo", "activo", "empresa", "fecha_creacion")
    readonly_fields = ("fecha_creacion", "fecha_modificacion", "creado_por")
    raw_id_fields = ("empresa", "creado_por")
    fieldsets = (
        (
            "Información General",
            {"fields": ("empresa", "tipo", "nombre", "numero_identificacion", "activo")},
        ),
        ("Contacto", {"fields": ("email", "telefono", "direccion"), "classes": ("collapse",)}),
        (
            "Auditoría",
            {
                "fields": ("creado_por", "fecha_creacion", "fecha_modificacion"),
                "classes": ("collapse",),
            },
        ),
    )


# --- Admin para ProductoInventario (Kardex) ---
@admin.register(ProductoInventario)
class ProductoInventarioAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "nombre",
        "empresa",
        "categoria",
        "metodo_valoracion",
        "stock_actual_display",
        "costo_promedio_display",
        "activo",
    )
    search_fields = ("sku", "nombre", "descripcion", "empresa__nombre")
    list_filter = ("metodo_valoracion", "activo", "categoria", "empresa")
    readonly_fields = (
        "fecha_creacion",
        "fecha_actualizacion",
        "stock_actual_display",
        "costo_promedio_display",
        "valor_inventario_display",
    )
    raw_id_fields = ("empresa", "cuenta_inventario", "cuenta_costo_venta", "creado_por")

    fieldsets = (
        (
            "Información Básica",
            {
                "fields": (
                    "empresa",
                    "sku",
                    "nombre",
                    "descripcion",
                    "categoria",
                    "unidad_medida",
                    "activo",
                )
            },
        ),
        (
            "Valoración y Contabilidad",
            {
                "fields": (
                    "metodo_valoracion",
                    "cuenta_inventario",
                    "cuenta_costo_venta",
                )
            },
        ),
        (
            "Control de Stock",
            {
                "fields": (
                    "stock_minimo",
                    "stock_maximo",
                    "stock_actual_display",
                    "costo_promedio_display",
                    "valor_inventario_display",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Auditoría",
            {
                "fields": ("creado_por", "fecha_creacion", "fecha_actualizacion"),
                "classes": ("collapse",),
            },
        ),
    )

    def stock_actual_display(self, obj):
        return f"{obj.stock_actual} {obj.unidad_medida}"

    stock_actual_display.short_description = "Stock Actual"

    def costo_promedio_display(self, obj):
        return f"${obj.costo_promedio_actual:,.2f}"

    costo_promedio_display.short_description = "Costo Promedio"

    def valor_inventario_display(self, obj):
        return f"${obj.valor_inventario_actual:,.2f}"

    valor_inventario_display.short_description = "Valor Inventario"


# --- Admin para MovimientoKardex ---
@admin.register(MovimientoKardex)
class MovimientoKardexAdmin(admin.ModelAdmin):
    list_display = (
        "fecha",
        "producto",
        "tipo_movimiento",
        "cantidad",
        "costo_unitario",
        "cantidad_saldo",
        "costo_promedio",
    )
    search_fields = (
        "producto__sku",
        "producto__nombre",
        "documento_referencia",
        "observaciones",
    )
    list_filter = ("tipo_movimiento", "fecha", "producto__empresa")
    readonly_fields = (
        "cantidad_saldo",
        "costo_promedio",
        "valor_total_saldo",
        "valor_total_movimiento",
        "fecha_registro",
    )
    raw_id_fields = ("producto", "asiento", "tercero", "creado_por")
    date_hierarchy = "fecha"

    fieldsets = (
        (
            "Información del Movimiento",
            {
                "fields": (
                    "producto",
                    "fecha",
                    "tipo_movimiento",
                    "cantidad",
                    "costo_unitario",
                    "valor_total_movimiento",
                )
            },
        ),
        (
            "Referencias",
            {
                "fields": (
                    "documento_referencia",
                    "tercero",
                    "asiento",
                    "observaciones",
                )
            },
        ),
        (
            "Saldos Calculados (Solo Lectura)",
            {
                "fields": (
                    "cantidad_saldo",
                    "costo_promedio",
                    "valor_total_saldo",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Auditoría",
            {
                "fields": ("creado_por", "fecha_creacion"),
                "classes": ("collapse",),
            },
        ),
    )

    def has_delete_permission(self, request, obj=None):
        # Advertencia: Eliminar movimientos puede descuadrar el Kardex
        # Solo superusuarios pueden eliminar
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        # Si es un nuevo movimiento, usar KardexService para mantener consistencia
        if not change and not obj.pk:
            messages.warning(
                request,
                "⚠️ ADVERTENCIA: Se recomienda usar KardexService.registrar_entrada() "
                "o registrar_salida() para mantener la consistencia del Kardex. "
                "Crear movimientos manualmente puede descuadrar los saldos.",
            )
        super().save_model(request, obj, form, change)


# --- Admin para EmpresaCierrePeriodo ---
@admin.register(EmpresaCierrePeriodo)
class EmpresaCierrePeriodoAdmin(admin.ModelAdmin):
    list_display = (
        "empresa",
        "periodo",
        "fecha_cierre",
        "utilidad_neta",
        "bloqueado",
        "cerrado_por",
    )
    search_fields = ("empresa__nombre",)
    list_filter = ("bloqueado", "periodo", "fecha_cierre")
    readonly_fields = (
        "fecha_cierre",
        "total_ingresos",
        "total_costos",
        "total_gastos",
        "utilidad_neta",
    )
    raw_id_fields = ("empresa", "asiento_cierre", "cerrado_por")
    date_hierarchy = "fecha_cierre"

    fieldsets = (
        (
            "Información del Cierre",
            {
                "fields": (
                    "empresa",
                    "periodo",
                    "fecha_cierre",
                    "bloqueado",
                    "asiento_cierre",
                )
            },
        ),
        (
            "Resumen Financiero",
            {
                "fields": (
                    "total_ingresos",
                    "total_costos",
                    "total_gastos",
                    "utilidad_neta",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Auditoría",
            {"fields": ("cerrado_por",), "classes": ("collapse",)},
        ),
    )

    def has_delete_permission(self, request, obj=None):
        # No permitir eliminar cierres de periodo desde el admin
        # Usar comando cerrar_periodo --desbloquear en su lugar
        return False
