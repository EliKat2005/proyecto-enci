from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile
from .models import AuditLog

# --- Admin para UserProfile ---
# Queremos que el UserProfile se edite "dentro" del modelo User.
# Para esto, usamos un Inline.

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfiles'

# --- Admin de User (Personalizado) ---
# Definimos un nuevo User admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

# Re-registramos el modelo User con nuestro UserAdmin personalizado
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# --- Admin para UserProfile (acciones para activar/desactivar) ---
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rol', 'esta_activo')
    list_filter = ('rol', 'esta_activo')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name')
    actions = ['activar_perfiles', 'desactivar_perfiles']

    def activar_perfiles(self, request, queryset):
        updated = queryset.update(esta_activo=True)
        # Registrar en audit log por cada perfil
        for perfil in queryset:
            AuditLog.objects.create(
                actor=request.user,
                target_user=perfil.user,
                action='activar_perfil',
                description=f'Perfil activado por admin desde admin.'
            )
        self.message_user(request, f"{updated} perfil(es) activados.")
    activar_perfiles.short_description = 'Activar perfiles seleccionados'

    def desactivar_perfiles(self, request, queryset):
        updated = queryset.update(esta_activo=False)
        for perfil in queryset:
            AuditLog.objects.create(
                actor=request.user,
                target_user=perfil.user,
                action='desactivar_perfil',
                description=f'Perfil desactivado por admin desde admin.'
            )
        self.message_user(request, f"{updated} perfil(es) desactivados.")
    desactivar_perfiles.short_description = 'Desactivar perfiles seleccionados'