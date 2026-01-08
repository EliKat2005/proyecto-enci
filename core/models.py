from django.conf import settings
from django.db import models

# NOTA: No necesitamos importar AuthUser directamente,
# usar settings.AUTH_USER_MODEL es la mejor práctica.


class UserProfile(models.Model):
    """
    Extiende el modelo User de Django para añadir campos
    específicos de nuestro negocio.
    """

    class Roles(models.TextChoices):
        ADMIN = "admin", "Administrador"
        DOCENTE = "docente", "Docente"
        ESTUDIANTE = "estudiante", "Estudiante"

    # Relación uno-a-uno con el modelo de Usuario de Django
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        # 'user_id' es el nombre de la columna en la BD, Django lo maneja.
    )

    # Campo de Rol basado en el ENUM de la BD
    rol = models.CharField(max_length=10, choices=Roles.choices, default=Roles.ESTUDIANTE)

    # Campo Booleano para el estado de activación
    esta_activo = models.BooleanField(default=False)

    class Meta:
        # Gestionado por Django; la tabla se crea vía migraciones
        managed = True
        db_table = "core_userprofile"
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        # Mostramos el username del usuario en el Admin de Django
        return self.user.username


class AuditLog(models.Model):
    """Registro simple de auditoría para acciones importantes del sistema.

    Guardamos el actor (quién hizo la acción), el usuario objetivo (si aplica),
    la acción y una descripción corta.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_targets",
    )
    action = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        who = self.actor.username if self.actor else "Sistema"
        target = self.target_user.username if self.target_user else "N/A"
        return f"[{self.created_at}] {who} -> {self.action} ({target})"


class Grupo(models.Model):
    """Grupo/Curso creado por un docente para organizar estudiantes.

    Cada grupo tiene su propio código de invitación y estudiantes asociados.
    """

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="grupos"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Grupo"
        verbose_name_plural = "Grupos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.nombre} ({self.docente.username})"

    def get_students_count(self):
        """Retorna el número de estudiantes en el grupo."""
        return self.referrals.count()

    def get_active_students_count(self):
        """Retorna el número de estudiantes activos en el grupo."""
        return self.referrals.filter(activated=True).count()


class Invitation(models.Model):
    """Código/invitación generado por un docente para que estudiantes se unan a un grupo.

    Cada invitación está vinculada a un grupo específico.
    """

    code = models.CharField(max_length=64, unique=True)
    grupo = models.ForeignKey(
        Grupo, on_delete=models.CASCADE, related_name="invitations", null=True, blank=True
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invitations"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    max_uses = models.IntegerField(default=1)
    uses_count = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Invitation"
        verbose_name_plural = "Invitations"

    def __str__(self):
        return f"{self.code} - {self.grupo.nombre} (by {self.creator.username})"

    def is_valid(self):
        from django.utils import timezone

        if not self.active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.max_uses is not None and self.uses_count >= self.max_uses:
            return False
        return True

    def delete(self, *args, **kwargs):
        """Sobrescribe delete para evitar eliminar invitaciones con estudiantes registrados."""
        from django.core.exceptions import ValidationError

        # Verificar si hay referrals usando esta invitación
        if self.referral_set.exists():
            raise ValidationError(
                f"No se puede eliminar la invitación {self.code} porque hay estudiantes registrados con ella. "
                f"Primero debe eliminar a los estudiantes del grupo."
            )
        super().delete(*args, **kwargs)


class Referral(models.Model):
    """Vincula a un estudiante con un grupo específico.

    Cada estudiante pertenece a un grupo y puede ser activado/desactivado por el docente.
    """

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referrals"
    )
    grupo = models.ForeignKey(
        Grupo, on_delete=models.CASCADE, related_name="referrals", null=True, blank=True
    )
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referred_students"
    )
    invitation = models.ForeignKey(Invitation, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    activated = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Referral"
        verbose_name_plural = "Referrals"
        unique_together = ("student", "grupo")  # Un estudiante solo puede estar una vez en un grupo

    def __str__(self):
        return f"{self.student.username} -> {self.grupo.nombre} ({self.docente.username})"


class Notification(models.Model):
    """Notificaciones internas del sistema.

    - `recipient`: usuario que recibe la notificación.
    - `actor`: quién causó el evento (opcional).
    - `verb`: acción corta (ej. 'registered', 'activated', 'commented').
    - `target_user`: usuario objetivo del evento, cuando aplique.
    - `empresa_id`: ID de la empresa relacionada (para comentarios).
    - `comment_section`: sección del comentario (PL, DI, RP).
    - `url`: URL directa a la acción/recurso.
    - `unread`: si la notificación aún no fue leída.
    - `created_at`: timestamp.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actor_notifications",
    )
    verb = models.CharField(max_length=100)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="target_notifications",
    )
    empresa_id = models.IntegerField(null=True, blank=True)
    comment_section = models.CharField(max_length=2, null=True, blank=True)
    url = models.CharField(max_length=500, null=True, blank=True)
    unread = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient.username}: {self.verb} ({'unread' if self.unread else 'read'})"
