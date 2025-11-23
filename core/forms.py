from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import UserProfile, Invitation, Referral, Notification, Grupo
from core.models import AuditLog
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
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
    # Rol del usuario que se registra: estudiante o docente
    role = forms.ChoiceField(
        label='¿Eres estudiante o docente?',
        choices=(('estudiante', 'Soy estudiante'), ('docente', 'Soy docente')),
        widget=forms.RadioSelect,
        initial='estudiante'
    )
    codigo_invite = forms.CharField(label='Código de invitación (si aplica)', required=False)

    class Meta:
        model = User # Basado en el modelo User de Django
        fields = ('username', 'first_name', 'last_name', 'email', 'password', 'role', 'codigo_invite')

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
        role = (cleaned.get('role') or 'estudiante')
        codigo = (cleaned.get('codigo_invite') or '').strip()

        if role == 'estudiante':
            # Si selecciona estudiante, el código es obligatorio
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

            # 3. Crear el UserProfile según el rol elegido
            role = (self.cleaned_data.get('role') or 'estudiante')
            if role == 'estudiante':
                UserProfile.objects.create(
                    user=user,
                    rol=UserProfile.Roles.ESTUDIANTE,
                    esta_activo=False
                )

                # Si el usuario se registró como estudiante con un código, creamos Referral
                codigo = (self.cleaned_data.get('codigo_invite') or '').strip()
                if codigo:
                    try:
                        invitation = Invitation.objects.get(code=codigo)
                        if invitation.is_valid():
                            # Incrementar contador de usos
                            invitation.uses_count += 1
                            if invitation.max_uses is not None and invitation.uses_count >= invitation.max_uses:
                                invitation.active = False
                            invitation.save()

                            # Crear Referral (vincula estudiante con docente y grupo)
                            Referral.objects.create(
                                student=user,
                                docente=invitation.creator,
                                invitation=invitation,
                                grupo=invitation.grupo,
                                activated=False
                            )

                            # Registrar en audit log
                            try:
                                AuditLog.objects.create(actor=invitation.creator, target_user=user, action='student_registered', description=f'Estudiante {user.username} registrado con código {invitation.code}')
                            except Exception:
                                pass

                            # Crear notificación en la app para el docente
                            try:
                                Notification.objects.create(
                                    recipient=invitation.creator,
                                    actor=None,
                                    verb='student_registered',
                                    target_user=user,
                                    unread=True
                                )
                            except Exception:
                                pass

                            # Notificar a administradores (is_staff=True) dentro de la app y por email
                            try:
                                admins = User.objects.filter(is_staff=True)
                                admin_emails = []
                                for admin in admins:
                                    try:
                                        Notification.objects.create(
                                            recipient=admin,
                                            actor=None,
                                            verb='student_registered',
                                            target_user=user,
                                            unread=True
                                        )
                                    except Exception:
                                        pass
                                    if admin.email:
                                        admin_emails.append(admin.email)

                                # Enviar email a admins (si hay alguno)
                                if admin_emails:
                                    admin_subject = f"Nuevo estudiante registrado: {user.username}"
                                    try:
                                        admin_text = render_to_string('emails/new_student_admins.txt', {'student': user, 'invitation': invitation, 'dashboard_url': '/admin/'})
                                    except Exception:
                                        admin_text = f"El estudiante {user.get_full_name() or user.username} ({user.email}) se registró usando el código {invitation.code}."
                                    try:
                                        admin_html = render_to_string('emails/new_student_admins.html', {'student': user, 'invitation': invitation, 'dashboard_url': '/admin/'})
                                    except Exception:
                                        admin_html = None
                                    try:
                                        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', 'no-reply@example.com')
                                        admin_msg = EmailMultiAlternatives(admin_subject, admin_text, from_email, list(set(admin_emails)))
                                        if admin_html:
                                            admin_msg.attach_alternative(admin_html, 'text/html')
                                        admin_msg.send(fail_silently=False)
                                        try:
                                            AuditLog.objects.create(actor=None, target_user=None, action='email_sent_admins', description=f'Notificación enviada a admins sobre estudiante {user.username}')
                                        except Exception:
                                            pass
                                    except Exception as e:
                                        try:
                                            AuditLog.objects.create(actor=None, target_user=None, action='email_failed_admins', description=f'Error enviando email a admins: {e}')
                                        except Exception:
                                            pass
                            except Exception:
                                pass

                            # Enviar notificación por email al docente (si tiene email)
                            try:
                                docente_email = invitation.creator.email
                                if docente_email:
                                    subject = f"Nuevo estudiante registrado: {user.username}"
                                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'SERVER_EMAIL', 'no-reply@example.com')
                                    # Contexto para las plantillas de email
                                    ctx = {
                                        'docente': invitation.creator,
                                        'student': user,
                                        'invitation': invitation,
                                        'dashboard_url': '/docente/dashboard/'
                                    }
                                    # Renderizar plantillas: texto y HTML
                                    try:
                                        text_body = render_to_string('emails/new_student.txt', ctx)
                                    except Exception:
                                        # Fallback simple en caso de error renderizando
                                        text_body = (
                                            f"Hola {invitation.creator.get_full_name() or invitation.creator.username},\n\n"
                                            f"El estudiante {user.get_full_name() or user.username} ({user.email}) se registró usando tu código {invitation.code} y está pendiente de activación.\n"
                                            f"Ingresa al dashboard para revisarlo: {ctx['dashboard_url']}\n\n"
                                            "Saludos."
                                        )
                                    try:
                                        html_body = render_to_string('emails/new_student.html', ctx)
                                    except Exception:
                                        html_body = None

                                    try:
                                        msg = EmailMultiAlternatives(subject, text_body, from_email, [docente_email])
                                        if html_body:
                                            msg.attach_alternative(html_body, 'text/html')
                                        msg.send(fail_silently=False)
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
            else:
                # Registro como docente: crear perfil docente (desactivado hasta que admin lo active)
                try:
                    UserProfile.objects.create(
                        user=user,
                        rol=UserProfile.Roles.DOCENTE,
                        esta_activo=False
                    )
                except Exception:
                    # Si falla la creación del perfil, no bloquear el registro
                    pass
                # El signal `notify_admins_on_docente_create` en `core.signals` se encargará de notificar a admins

        return user


class InvitationForm(forms.ModelForm):
    """Formulario para que un docente genere un código/invitación para un grupo específico."""
    # expires_at as optional date/time field (HTML5 datetime-local)
    expires_at = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))

    class Meta:
        model = Invitation
        fields = ('grupo', 'max_uses', 'expires_at')

    def __init__(self, *args, **kwargs):
        docente = kwargs.pop('docente', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar los grupos para mostrar solo los del docente actual
        if docente:
            self.fields['grupo'].queryset = Grupo.objects.filter(docente=docente, active=True)
            self.fields['grupo'].required = True

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


class GrupoForm(forms.ModelForm):
    """Formulario para crear/editar grupos."""
    
    class Meta:
        model = Grupo
        fields = ('nombre', 'descripcion', 'active')
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Matemáticas 2025-1'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción del grupo (opcional)'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nombre': 'Nombre del Grupo',
            'descripcion': 'Descripción',
            'active': 'Grupo Activo',
        }
    
    def save(self, docente=None, commit=True):
        """Guarda el grupo asignándole el docente."""
        grupo = super().save(commit=False)
        if docente is not None:
            grupo.docente = docente
        if commit:
            grupo.save()
        return grupo