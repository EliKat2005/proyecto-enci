from django.contrib import admin
from .models import (
    PlanDeCuentas, Asiento, Transaccion,
    Empresa, EmpresaPlanCuenta, EmpresaAsiento, EmpresaTransaccion, 
    EmpresaSupervisor, EmpresaComment
)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'owner', 'is_template', 'visible_to_supervisor', 'join_code', 'created_at')
    search_fields = ('nombre', 'owner__username', 'join_code')
    list_filter = ('is_template', 'visible_to_supervisor', 'created_at')
    raw_id_fields = ('owner', 'original')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(EmpresaPlanCuenta)
class EmpresaPlanCuentaAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'codigo', 'descripcion', 'tipo', 'naturaleza', 'es_auxiliar')
    search_fields = ('codigo', 'descripcion', 'empresa__nombre')
    list_filter = ('tipo', 'naturaleza', 'es_auxiliar', 'estado_situacion')
    raw_id_fields = ('empresa', 'padre')


@admin.register(EmpresaAsiento)
class EmpresaAsientoAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'fecha', 'creado_por', 'estado', 'fecha_creacion')
    search_fields = ('descripcion_general', 'empresa__nombre')
    list_filter = ('estado', 'fecha')
    raw_id_fields = ('empresa', 'creado_por')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')
    date_hierarchy = 'fecha'


@admin.register(EmpresaTransaccion)
class EmpresaTransaccionAdmin(admin.ModelAdmin):
    list_display = ('asiento', 'cuenta', 'parcial', 'debe', 'haber')
    search_fields = ('detalle_linea', 'asiento__empresa__nombre')
    raw_id_fields = ('asiento', 'cuenta')
    list_filter = ('asiento__estado',)


@admin.register(EmpresaSupervisor)
class EmpresaSupervisorAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'docente', 'created_at')
    search_fields = ('empresa__nombre', 'docente__username')
    raw_id_fields = ('empresa', 'docente')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(EmpresaComment)
class EmpresaCommentAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'section', 'author', 'created_at')
    search_fields = ('content', 'empresa__nombre', 'author__username')
    list_filter = ('section', 'created_at')
    raw_id_fields = ('empresa', 'author')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


# Register legacy accounting models for convenience
# --- Admin para Asiento y Transaccion (Cabecera/Detalle) ---
# Usamos un TabularInline para ver y editar las transacciones
# directamente "dentro" del formulario del Asiento.

class TransaccionInline(admin.TabularInline):
    model = Transaccion
    extra = 2  # Muestra 2 líneas vacías por defecto (para Debe y Haber)
    raw_id_fields = ('cuenta',)


@admin.register(Asiento)
class AsientoAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'descripcion_general', 'estado', 'creado_por')
    list_filter = ('estado', 'fecha')
    search_fields = ('id', 'descripcion_general')
    inlines = [TransaccionInline]  # ¡Aquí conectamos el detalle!
    raw_id_fields = ('creado_por',)
    date_hierarchy = 'fecha'


# --- Admin para PlanDeCuentas ---
# Lo registramos de forma estándar, pero con mejoras de UI.
@admin.register(PlanDeCuentas)
class PlanDeCuentasAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'tipo', 'naturaleza', 'es_auxiliar', 'padre')
    list_filter = ('tipo', 'naturaleza', 'es_auxiliar', 'estado_situacion')
    search_fields = ('codigo', 'descripcion')
    raw_id_fields = ('padre',)