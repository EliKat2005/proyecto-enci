from django.contrib import admin
from .models import (
    PlanDeCuentas, Asiento, Transaccion,
    Empresa, EmpresaPlanCuenta, EmpresaAsiento, EmpresaTransaccion, EmpresaSupervisor
)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'owner', 'is_template', 'join_code', 'created_at')
    search_fields = ('nombre', 'owner__username', 'join_code')
    list_filter = ('is_template',)


@admin.register(EmpresaPlanCuenta)
class EmpresaPlanCuentaAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'codigo', 'descripcion', 'tipo', 'es_auxiliar')
    search_fields = ('codigo', 'descripcion')


@admin.register(EmpresaAsiento)
class EmpresaAsientoAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'fecha', 'creado_por', 'estado')
    search_fields = ('descripcion_general',)
    list_filter = ('estado',)


@admin.register(EmpresaTransaccion)
class EmpresaTransaccionAdmin(admin.ModelAdmin):
    list_display = ('asiento', 'cuenta', 'parcial', 'debe', 'haber')
    search_fields = ('detalle_linea',)


@admin.register(EmpresaSupervisor)
class EmpresaSupervisorAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'docente', 'created_at')
    search_fields = ('empresa__nombre', 'docente__username')

# Register legacy accounting models for convenience
# --- Admin para Asiento y Transaccion (Cabecera/Detalle) ---
# Usamos un TabularInline para ver y editar las transacciones
# directamente "dentro" del formulario del Asiento.

class TransaccionInline(admin.TabularInline):
    model = Transaccion
    extra = 2 # Muestra 2 líneas vacías por defecto (para Debe y Haber)


@admin.register(Asiento)
class AsientoAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'descripcion_general', 'estado', 'creado_por')
    list_filter = ('estado', 'fecha')
    search_fields = ('id', 'descripcion_general')
    inlines = [TransaccionInline] # ¡Aquí conectamos el detalle!


# --- Admin para PlanDeCuentas ---
# Lo registramos de forma estándar, pero con mejoras de UI.
@admin.register(PlanDeCuentas)
class PlanDeCuentasAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'tipo', 'naturaleza', 'es_auxiliar', 'padre')
    list_filter = ('tipo', 'naturaleza', 'es_auxiliar')
    search_fields = ('codigo', 'descripcion')