from django.contrib import admin
from .models import PlanDeCuentas, Asiento, Transaccion

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