from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from .models import UserProfile

class ActiveStudentBackend(ModelBackend):
    """
    Este es nuestro "guardia de seguridad" personalizado.
    Comprueba el login Y ADEMÁS comprueba si el perfil está activo.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # 1. Dejamos que el ModelBackend normal (el guardia de Django)
        #    verifique el usuario y la contraseña primero.
        user = super().authenticate(request, username=username, password=password, **kwargs)

        # Si el usuario/pass es incorrecto, user será None. No hacemos nada.
        if user is None:
            return None

        # 2. ¡NUESTRA LÓGICA PERSONALIZADA!
        # Si el usuario/pass FUE correcto, ahora aplicamos nuestras reglas.

        # Regla A: El Superusuario (admin) siempre puede entrar.
        if user.is_superuser:
            return user

        # Regla B: Si es un usuario normal, revisa su UserProfile.
        try:
            profile = user.userprofile # (user.userprofile viene del 'OneToOneField')
            
            if profile.esta_activo:
                # ¡Es un usuario (docente/estudiante) y ESTÁ ACTIVO!
                return user
            else:
                # Es un usuario (estudiante) pero NO ESTÁ ACTIVO.
                # Rechazamos el login.
                return None
        
        except UserProfile.DoesNotExist:
            # Caso raro: un usuario normal sin perfil. Lo rechazamos.
            return None

    def get_user(self, user_id):
        # Esta parte es necesaria para que Django pueda
        # obtener el objeto User durante la sesión.
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None