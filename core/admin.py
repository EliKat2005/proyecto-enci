from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

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