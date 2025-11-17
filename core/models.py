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
        ADMIN = 'admin', 'Administrador'
        DOCENTE = 'docente', 'Docente'
        ESTUDIANTE = 'estudiante', 'Estudiante'

    # Relación uno-a-uno con el modelo de Usuario de Django
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        # 'user_id' es el nombre de la columna en la BD, Django lo maneja.
    )
    
    # Campo de Rol basado en el ENUM de la BD
    rol = models.CharField(
        max_length=10,
        choices=Roles.choices,
        default=Roles.ESTUDIANTE
    )
    
    # Campo Booleano para el estado de activación
    esta_activo = models.BooleanField(
        default=False
    )

    class Meta:
        managed = False # Django no gestionará esta tabla (ya existe)
        db_table = 'core_userprofile'
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'

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
        related_name='audit_actions'
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_targets'
    )
    action = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        who = self.actor.username if self.actor else 'Sistema'
        target = self.target_user.username if self.target_user else 'N/A'
        return f"[{self.created_at}] {who} -> {self.action} ({target})"


class Invitation(models.Model):
    """Código/invitación generado por un docente para que estudiantes se registren.

    No toca `UserProfile` directamente; sirve para vincular registros con el docente creador.
    """
    code = models.CharField(max_length=64, unique=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    max_uses = models.IntegerField(default=1)
    uses_count = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Invitation'
        verbose_name_plural = 'Invitations'

    def __str__(self):
        return f"{self.code} (by {self.creator.username})"

    def is_valid(self):
        from django.utils import timezone
        if not self.active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        if self.max_uses is not None and self.uses_count >= self.max_uses:
            return False
        return True


class Referral(models.Model):
    """Vincula a un estudiante con el docente que le proporcionó la invitación.

    Permite listar en el dashboard del docente los estudiantes referidos y su estado.
    """
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referrals'
    )
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referred_students'
    )
    invitation = models.ForeignKey(Invitation, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    activated = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Referral'
        verbose_name_plural = 'Referrals'

    def __str__(self):
        return f"{self.student.username} -> {self.docente.username}"