from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import UserProfile, Invitation, Referral
from core.models import AuditLog
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()

class RegistroForm(forms.ModelForm):
    """
    Formulario para el registro de nuevos usuarios (estudiantes).
    """
    # Campos adicionales del modelo User que queremos
    first_name = forms.CharField(label='Nombres', max_length=150, required=True)
    last_name = forms.CharField(label='Apellidos', max_length=150, required=True)
    email = forms.EmailField(label='Correo Electrónico', required=True)
    
    # Campos para la contraseña
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput, required=True)
    password_confirm = forms.CharField(label='Confirmar Contraseña', widget=forms.PasswordInput, required=True)
    # Indica si el registrante se identifica como estudiante y usará un código
    soy_estudiante = forms.BooleanField(label='Soy estudiante', required=False, initial=True)
    codigo_invite = forms.CharField(label='Código de invitación (si aplica)', required=False)

    class Meta:
        model = User # Basado en el modelo User de Django
        fields = ('username', 'first_name', 'last_name', 'email', 'password', 'soy_estudiante', 'codigo_invite')

    def clean_password_confirm(self):
        """
        Validación para asegurar que las dos contraseñas coincidan.
        """
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return password_confirm
    
    def clean_username(self):
        """
        Validación para asegurar que el nombre de usuario no exista ya.
        """
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username

    def clean_email(self):
        """
        Validación para asegurar que el correo electrónico no esté ya registrado.
        """
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este correo electrónico ya está registrado.")
        return email

    def clean(self):
        cleaned = super().clean()
        soy_estudiante = bool(cleaned.get('soy_estudiante'))
        codigo = (cleaned.get('codigo_invite') or '').strip()

        if soy_estudiante:
            # Si marca que es estudiante, el código es obligatorio
            if not codigo:
                raise forms.ValidationError('Si te registras como estudiante debes ingresar un código de invitación proporcionado por tu docente.')

            # Validar que la invitación exista y sea válida
            try:
                invitation = Invitation.objects.get(code=codigo)
            except Invitation.DoesNotExist:
                raise forms.ValidationError('Código de invitación inválido.')

            if not invitation.is_valid():
                raise forms.ValidationError('El código de invitación ha expirado o ha alcanzado su límite de uso.')

            # Validar que el creador de la invitación sea docente
            try:
                # Some installations use userprofile with managed=False; we check rol safely
                profile = invitation.creator.userprofile
                if profile.rol != UserProfile.Roles.DOCENTE:
                    raise forms.ValidationError('El código no pertenece a un docente válido.')
            except Exception:
                raise forms.ValidationError('El código no pertenece a un docente válido.')

        return cleaned

    def save(self, commit=True):
        """
        Sobrescribimos el método save para manejar la creación
        del User y del UserProfile en una sola transacción.
        """
        # 1. Crear el objeto User (pero no guardarlo aún)
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        
        if commit:
            # 2. Guardar el User
            user.save()
            
            # 3. Crear el UserProfile (¡Aquí está la lógica de negocio!)
            # Por defecto, creamos perfil como ESTUDIANTE y desactivado.
            UserProfile.objects.create(
                user=user,
                rol=UserProfile.Roles.ESTUDIANTE,
                esta_activo=False
            )

            # Si el usuario se registró como estudiante con un código, creamos Referral
            soy_estudiante = bool(self.cleaned_data.get('soy_estudiante'))
            codigo = (self.cleaned_data.get('codigo_invite') or '').strip()
            if soy_estudiante and codigo:
                try:
                    invitation = Invitation.objects.get(code=codigo)
                    if invitation.is_valid():
                        # Incrementar contador de usos
                        invitation.uses_count += 1
                        if invitation.max_uses is not None and invitation.uses_count >= invitation.max_uses:
                            invitation.active = False
                        invitation.save()

                        # Crear Referral (vincula estudiante con docente)
                        Referral.objects.create(
                            student=user,
                            docente=invitation.creator,
                            invitation=invitation,
                            activated=False
                        )

                        # Registrar en audit log
                        try:
                            AuditLog.objects.create(actor=invitation.creator, target_user=user, action='student_registered', description=f'Estudiante {user.username} registrado con código {invitation.code}')
                        except Exception:
                            pass
                        # Enviar notificación por email al docente (si tiene email)
                        try:
                            docente_email = invitation.creator.email
                            if docente_email:
                                subject = f"Nuevo estudiante registrado: {user.username}"
                                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', 'no-reply@example.com')
                                message = (
                                    f"Hola {invitation.creator.get_full_name() or invitation.creator.username},\n\n"
                                    f"El estudiante {user.get_full_name() or user.username} ({user.email}) se registró usando tu código {invitation.code} y está pendiente de activación.\n"
                                    f"Ingresa al dashboard para revisarlo: /docente/dashboard/\n\n"
                                    "Saludos."
                                )
                                try:
                                    send_mail(subject, message, from_email, [docente_email], fail_silently=False)
                                    try:
                                        AuditLog.objects.create(actor=None, target_user=invitation.creator, action='email_sent', description=f'Notificación enviada a {docente_email} sobre estudiante {user.username}')
                                    except Exception:
                                        pass
                                except Exception as e:
                                    try:
                                        AuditLog.objects.create(actor=None, target_user=invitation.creator, action='email_failed', description=f'Error enviando email a {docente_email}: {e}')
                                    except Exception:
                                        pass
                        except Exception:
                            # No fatal: si falla el envío, ya dejamos registro en AuditLog cuando se creó el referral
                            pass
                except Invitation.DoesNotExist:
                    # Si la invitación no existe, no hacemos referral (la validación debería prevenir esto)
                    pass
        return user


class InvitationForm(forms.ModelForm):
    """Formulario para que un docente genere un código/invitación."""
    # expires_at as optional date/time field (HTML5 datetime-local)
    expires_at = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))

    class Meta:
        model = Invitation
        fields = ('max_uses', 'expires_at')

    def save(self, creator=None, commit=True):
        import secrets
        # Generar un código seguro
        code = secrets.token_urlsafe(10)
        invitation = super().save(commit=False)
        invitation.code = code
        if creator is not None:
            invitation.creator = creator
        if commit:
            invitation.save()
        return invitation