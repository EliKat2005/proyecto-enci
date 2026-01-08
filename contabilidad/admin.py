from django.contrib import admin

from .models import (
    Empresa,
    EmpresaAsiento,
    EmpresaComment,
    EmpresaPlanCuenta,
    EmpresaSupervisor,
    EmpresaTercero,
    EmpresaTransaccion,
    PeriodoContable,
    PlanDeCuentas,
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
    list_filter = ("tipo", "naturaleza", "es_auxiliar", "estado_situacion", "activa")
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
    list_filter = ("tipo", "naturaleza", "es_auxiliar", "estado_situacion")
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
