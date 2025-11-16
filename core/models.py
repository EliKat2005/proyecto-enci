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