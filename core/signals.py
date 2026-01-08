from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string

from core.models import AuditLog

from .models import Notification, UserProfile

User = get_user_model()


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
        known_roles = ["docente", "estudiante", "admin"]
        for other in known_roles:
            if other == role_name:
                continue
            g, _ = Group.objects.get_or_create(name=other)
            if user in g.user_set.all():
                g.user_set.remove(user)
    except Exception:
        # No fallamos la operación por errores en sincronización
        pass


@receiver(post_save, sender=UserProfile)
def notify_admins_on_docente_create(sender, instance, created, **kwargs):
    """Cuando se crea un perfil nuevo con rol 'docente', notificar a administradores.

    Crea una `Notification` para cada admin (`is_staff=True`) y envía un email resumen.
    """
    try:
        if not created:
            return

        if instance.rol != UserProfile.Roles.DOCENTE:
            return

        # Crear notificaciones internas para admins
        admins = User.objects.filter(is_staff=True)
        admin_emails = []
        for admin in admins:
            try:
                Notification.objects.create(
                    recipient=admin,
                    actor=None,
                    verb="docente_registered",
                    target_user=instance.user,
                    unread=True,
                )
            except Exception:
                pass
            if admin.email:
                admin_emails.append(admin.email)

        # Enviar email a administradores
        if admin_emails:
            subject = f"Nuevo docente registrado: {instance.user.username}"
            try:
                text = render_to_string(
                    "emails/new_docente_admins.txt",
                    {"docente": instance.user, "dashboard_url": "/admin/"},
                )
            except Exception:
                text = f"Se ha registrado el docente {instance.user.get_full_name() or instance.user.username}."
            try:
                html = render_to_string(
                    "emails/new_docente_admins.html",
                    {"docente": instance.user, "dashboard_url": "/admin/"},
                )
            except Exception:
                html = None
            try:
                from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(
                    settings, "SERVER_EMAIL", "no-reply@example.com"
                )
                msg = EmailMultiAlternatives(subject, text, from_email, list(set(admin_emails)))
                if html:
                    msg.attach_alternative(html, "text/html")
                msg.send(fail_silently=False)
                try:
                    AuditLog.objects.create(
                        actor=None,
                        target_user=None,
                        action="email_sent_admins_docente",
                        description=f"Notificación enviada a admins sobre docente {instance.user.username}",
                    )
                except Exception:
                    pass
            except Exception as e:
                try:
                    AuditLog.objects.create(
                        actor=None,
                        target_user=None,
                        action="email_failed_admins_docente",
                        description=f"Error enviando email a admins: {e}",
                    )
                except Exception:
                    pass
    except Exception:
        pass
