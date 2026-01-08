from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import AuditLog, Invitation, Notification, Referral, UserProfile

# --- Admin para UserProfile ---
# Queremos que el UserProfile se edite "dentro" del modelo User.
# Para esto, usamos un Inline.


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Perfiles"


# --- Admin de User (Personalizado) ---
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")


# Re-registramos el modelo User con nuestro UserAdmin personalizado
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# --- Admin para UserProfile (acciones para activar/desactivar) ---
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "rol", "esta_activo")
    list_filter = ("rol", "esta_activo")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    raw_id_fields = ("user",)
    actions = ["activar_perfiles", "desactivar_perfiles"]

    def activar_perfiles(self, request, queryset):
        updated = queryset.update(esta_activo=True)
        # Registrar en audit log por cada perfil
        for perfil in queryset:
            AuditLog.objects.create(
                actor=request.user,
                target_user=perfil.user,
                action="activar_perfil",
                description="Perfil activado por admin desde admin.",
            )
        self.message_user(request, f"{updated} perfil(es) activados.")

    activar_perfiles.short_description = "Activar perfiles seleccionados"

    def desactivar_perfiles(self, request, queryset):
        updated = queryset.update(esta_activo=False)
        for perfil in queryset:
            AuditLog.objects.create(
                actor=request.user,
                target_user=perfil.user,
                action="desactivar_perfil",
                description="Perfil desactivado por admin desde admin.",
            )
        self.message_user(request, f"{updated} perfil(es) desactivados.")

    desactivar_perfiles.short_description = "Desactivar perfiles seleccionados"


# --- Admin para AuditLog ---
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target_user", "description")
    list_filter = ("action", "created_at")
    search_fields = ("actor__username", "target_user__username", "description")
    date_hierarchy = "created_at"
    readonly_fields = ("actor", "target_user", "action", "description", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# --- Admin para Invitation ---
@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "creator",
        "active",
        "uses_count",
        "max_uses",
        "created_at",
        "expires_at",
    )
    list_filter = ("active", "created_at")
    search_fields = ("code", "creator__username")
    readonly_fields = ("uses_count",)
    raw_id_fields = ("creator",)


# --- Admin para Referral ---
@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("student", "docente", "activated", "created_at")
    list_filter = ("activated", "created_at")
    search_fields = ("student__username", "docente__username")
    raw_id_fields = ("student", "docente", "invitation")


# --- Admin para Notification ---
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "verb", "actor", "unread", "created_at")
    list_filter = ("unread", "verb", "created_at")
    search_fields = ("recipient__username", "actor__username", "verb")
    raw_id_fields = ("recipient", "actor", "target_user")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
