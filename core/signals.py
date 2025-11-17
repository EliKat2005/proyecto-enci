from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import UserProfile


@receiver(post_save, sender=UserProfile)
def sync_group_on_profile_save(sender, instance, **kwargs):
    """Asegura que el usuario esté en el Group correspondiente a su `rol`.

    - Añade al usuario al grupo con el mismo nombre que `rol` (por ejemplo 'docente', 'estudiante').
    - Elimina al usuario de los grupos de rol opuesto si existen.

    Esto facilita permisos basados en grupos y mantiene la tabla `core_userprofile`
    como fuente de verdad para el rol del usuario.
    """
    try:
        user = instance.user
        role_name = instance.rol

        # Aseguramos que el grupo exista
        role_group, _ = Group.objects.get_or_create(name=role_name)
        # Añadimos el usuario al grupo del rol
        role_group.user_set.add(user)

        # Opcional: quitar de otros grupos de rol conocidos
        known_roles = ['docente', 'estudiante', 'admin']
        for other in known_roles:
            if other == role_name:
                continue
            g, _ = Group.objects.get_or_create(name=other)
            if user in g.user_set.all():
                g.user_set.remove(user)
    except Exception:
        # No fallamos la operación por errores en sincronización
        pass
