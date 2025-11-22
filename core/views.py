from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import RegistroForm
# --- ¡Nuevas importaciones! ---
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .models import UserProfile, Referral, AuditLog, Invitation
from contabilidad.models import Empresa
# -----------------------------
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Notification
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.contrib.messages import get_messages

# Obtenemos el modelo User
User = get_user_model()


@login_required 
def home_view(request):
    """
    Vista para la página de inicio.
    """
    # Pasamos información del usuario a la plantilla
    # Determinar si el usuario es docente y/o admin (para mostrar enlaces en la UI)
    is_docente = False
    is_admin = False
    try:
        # admin: superuser OR perfil rol=ADMIN
        is_admin = request.user.is_superuser or (hasattr(request.user, 'userprofile') and request.user.userprofile.rol == UserProfile.Roles.ADMIN)
        # docente: perfil rol=DOCENTE (no marcar superuser como docente)
        is_docente = (hasattr(request.user, 'userprofile') and request.user.userprofile.rol == UserProfile.Roles.DOCENTE)
    except Exception:
        is_docente = False
        is_admin = False

    contexto = {
        'user': request.user,
        'is_docente': is_docente,
        'is_admin': is_admin,
        'empresas': Empresa.objects.filter(owner=request.user)
    }
    return render(request, 'core/home.html', contexto)


# --- ¡VISTA DE LOGIN PERSONALIZADA! ---
def login_view(request):
    """
    Maneja el inicio de sesión con comprobación de estado de activación.
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)

        # Obtenemos credenciales del POST
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        # Caso A: usuario no existe
        try:
            user_check = User.objects.get(username=username)
        except User.DoesNotExist:
            # Usuario no existe
            messages.error(request, 'El usuario no existe.')
            # Devolver formulario vacío pero conservar el username en el campo
            empty_form = AuthenticationForm()
            return render(request, 'core/login.html', {'form': empty_form, 'username_value': username})

        # A estas alturas el usuario existe. Comprobamos la contraseña.
        if not user_check.check_password(password):
            # Contraseña incorrecta
            messages.error(request, 'Contraseña incorrecta. Por favor verifica tus credenciales.')
            empty_form = AuthenticationForm()
            return render(request, 'core/login.html', {'form': empty_form, 'username_value': username})

        # La contraseña es correcta. Ahora verificamos el estado del perfil.
        # NOTA: los superusuarios siempre pueden entrar (no requieren perfil activo).
        if not user_check.is_superuser:
            try:
                profile = user_check.userprofile
                if not profile.esta_activo:
                    # Cuenta existente, contraseña correcta, pero perfil no activo
                    messages.warning(request, 'Tu cuenta está registrada, pero pendiente de activación por un administrador.')
                    empty_form = AuthenticationForm()
                    return render(request, 'core/login.html', {'form': empty_form, 'username_value': username})
            except UserProfile.DoesNotExist:
                # Si no tiene perfil definido, no permitimos el login por seguridad
                messages.error(request, 'Perfil de usuario no encontrado. Contacta al administrador.')
                empty_form = AuthenticationForm()
                return render(request, 'core/login.html', {'form': empty_form, 'username_value': username})

        # Si llegamos aquí, el usuario existe, contraseña correcta y perfil activo (o es superuser)
        # Autenticamos vía backend para mantener compatibilidad
        user = authenticate(request, username=username, password=password)
        if user is None:
            # Raro: no autenticó a través de los backends (causa externa). Hacemos login manual como fallback.
            user_check.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user_check)
            logged_user = user_check
        else:
            login(request, user)
            logged_user = user

        # Respetar parámetro `next` si viene y es seguro
        from django.utils.http import url_has_allowed_host_and_scheme
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)

        return redirect('home')

    else:
        # Petición GET: solo muestra el formulario vacío
        form = AuthenticationForm()

    return render(request, 'core/login.html', {'form': form})


def logout_view(request):
    """
    Vista personalizada de logout que limpia los mensajes antes de cerrar sesión.
    """
    # Limpiar todos los mensajes de la sesión
    storage = get_messages(request)
    for _ in storage:
        pass  # Iterar para consumir todos los mensajes
    
    # Cerrar sesión
    logout(request)
    
    # Renderizar la página de logout sin mensajes
    return render(request, 'core/logout.html')


def registro_view(request):
    """
    Vista para el registro de nuevos usuarios.
    """
    # Determinar rol preseleccionado (viene como ?role=estudiante|docente desde login)
    role = request.GET.get('role', 'estudiante')

    if request.method == 'POST':
        # El template envía un campo oculto 'role' para que el form lo reciba
        form = RegistroForm(request.POST)
        if form.is_valid():
            form.save() # Nuestro 'save' personalizado se encarga de todo
            # Informamos al usuario y redirigimos al login
            messages.success(request, 'Registro completado. Tu cuenta está pendiente de activación por un docente o administrador.')
            return redirect('login')
    else:
        # Preconfiguramos el formulario con el role seleccionado (no se muestra en UI)
        form = RegistroForm(initial={'role': role})

    contexto = {
        'form': form,
        'selected_role': role,
    }
    return render(request, 'core/registro.html', contexto)


# --- Vista y decorador para docentes/admins ---
def is_docente_or_admin(user):
    try:
        return user.is_superuser or (hasattr(user, 'userprofile') and user.userprofile.rol == UserProfile.Roles.DOCENTE)
    except Exception:
        return False


docente_required = user_passes_test(is_docente_or_admin, login_url='login')


@docente_required
def docente_alumnos_view(request):
    """Lista y gestiona estudiantes (activar/desactivar).

    GET: muestra lista paginada, filtrable por `q`.
    POST: procesa `profile_id` y `action` ('activar'|'desactivar').
    """
    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        action = request.POST.get('action')
        if not profile_id or action not in ('activar', 'desactivar'):
            messages.error(request, 'Solicitud inválida.')
            return redirect('docente_alumnos')

        profile = get_object_or_404(UserProfile, pk=profile_id)
        if profile.rol != UserProfile.Roles.ESTUDIANTE:
            messages.error(request, 'Solo se pueden gestionar perfiles de estudiantes.')
            return redirect('docente_alumnos')

        profile.esta_activo = True if action == 'activar' else False
        profile.save()
        # Registrar en audit log
        try:
            from .models import AuditLog
            AuditLog.objects.create(
                actor=request.user,
                target_user=profile.user,
                action='activar_perfil' if profile.esta_activo else 'desactivar_perfil',
                description=f"Perfil {'activado' if profile.esta_activo else 'desactivado'} por {request.user.username} desde UI docente."
            )
        except Exception:
            # No fatal: si falla el logging no impedimos la operación
            pass

        messages.success(request, f"Perfil de {profile.user.username} {'activado' if profile.esta_activo else 'desactivado'}.")
        return redirect('docente_alumnos')

    # GET: lista
    q = request.GET.get('q', '').strip()
    estudiantes = UserProfile.objects.filter(rol=UserProfile.Roles.ESTUDIANTE).select_related('user').order_by('user__username')
    if q:
        estudiantes = estudiantes.filter(
            Q(user__username__icontains=q) | Q(user__email__icontains=q) | Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q)
        )

    paginator = Paginator(estudiantes, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/docente_alumnos.html', {'page_obj': page_obj, 'q': q})


@docente_required
def docente_dashboard_view(request):
    """Dashboard para que el docente vea sus estudiantes referidos y gestione códigos/invitaciones."""
    # POST: puede contener varias operaciones diferenciadas por 'operation'
    if request.method == 'POST':
        operation = request.POST.get('operation')

        # Referral activation/deactivation
        if operation == 'referral_action':
            referral_id = request.POST.get('referral_id')
            action = request.POST.get('action')
            if not referral_id or action not in ('activar', 'desactivar'):
                messages.error(request, 'Solicitud inválida.')
                return redirect('docente_dashboard')

            referral = get_object_or_404(Referral, pk=referral_id, docente=request.user)
            referral.activated = True if action == 'activar' else False
            referral.save()
            try:
                profile = referral.student.userprofile
                profile.esta_activo = referral.activated
                profile.save()
            except Exception:
                pass
            try:
                AuditLog.objects.create(
                    actor=request.user,
                    target_user=referral.student,
                    action='activar_referral' if referral.activated else 'desactivar_referral',
                    description=f"Referral {'activado' if referral.activated else 'desactivado'} por {request.user.username} en dashboard."
                )
            except Exception:
                pass
            messages.success(request, f"Perfil de {referral.student.username} {'activado' if referral.activated else 'desactivado'}.")
            return redirect('docente_dashboard')

        # Create Invitation
        if operation == 'create_invitation':
            from .forms import InvitationForm
            form = InvitationForm(request.POST)
            if form.is_valid():
                inv = form.save(creator=request.user)
                try:
                    AuditLog.objects.create(actor=request.user, action='create_invitation', description=f'Invitation {inv.code} creada por {request.user.username}')
                except Exception:
                    pass
                messages.success(request, f'Código creado: {inv.code} (usos: {inv.max_uses})')
            else:
                messages.error(request, f'Error al crear el código: {form.errors.as_json()}')
            return redirect('docente_dashboard')

        # Invitation actions: activar/desactivar/eliminar
        if operation == 'invitation_action':
            inv_id = request.POST.get('invitation_id')
            inv_action = request.POST.get('inv_action')
            if not inv_id or inv_action not in ('activar', 'desactivar', 'eliminar'):
                messages.error(request, 'Solicitud inválida.')
                return redirect('docente_dashboard')
            inv = get_object_or_404(Invitation, pk=inv_id, creator=request.user)
            if inv_action == 'eliminar':
                inv_code = inv.code
                inv.delete()
                try:
                    AuditLog.objects.create(actor=request.user, action='delete_invitation', description=f'Invitation {inv_code} eliminada por {request.user.username}')
                except Exception:
                    pass
                messages.success(request, f'Código {inv_code} eliminado.')
            else:
                inv.active = True if inv_action == 'activar' else False
                inv.save()
                try:
                    AuditLog.objects.create(actor=request.user, action='toggle_invitation', description=f'Invitation {inv.code} set active={inv.active} by {request.user.username}')
                except Exception:
                    pass
                messages.success(request, f'Código {inv.code} actualizado.')
            return redirect('docente_dashboard')

    # GET: lista de referrals e invitaciones del docente
    q = request.GET.get('q', '').strip()
    referrals = Referral.objects.filter(docente=request.user).select_related('student', 'invitation').order_by('-created_at')
    invitations = Invitation.objects.filter(creator=request.user).order_by('-created_at')
    if q:
        referrals = referrals.filter(
            Q(student__username__icontains=q) | Q(student__email__icontains=q) | Q(student__first_name__icontains=q) | Q(student__last_name__icontains=q)
        )

    # Paginación ligera para referrals
    paginator = Paginator(referrals, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'core/docente_dashboard.html', {'referrals': page_obj, 'invitations': invitations})


@login_required
def notifications_view(request):
    """Lista de notificaciones del usuario."""
    notes = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:100]
    return render(request, 'core/notifications.html', {'notifications': notes})


@login_required
def mark_notification_read(request):
    if request.method != 'POST':
        return HttpResponseForbidden('Invalid')
    nid = request.POST.get('notification_id')
    if not nid:
        messages.error(request, 'Notificación no especificada.')
        return redirect('notifications')
    try:
        n = Notification.objects.get(pk=nid, recipient=request.user)
        n.unread = False
        n.save()
        messages.success(request, 'Notificación marcada como leída.')
    except Notification.DoesNotExist:
        messages.error(request, 'Notificación no encontrada.')
    return redirect('notifications')


@login_required
def mark_all_notifications_read(request):
    if request.method != 'POST':
        return HttpResponseForbidden('Invalid')
    Notification.objects.filter(recipient=request.user, unread=True).update(unread=False)
    messages.success(request, 'Todas las notificaciones han sido marcadas como leídas.')
    return redirect('notifications')


@login_required
def delete_notification(request):
    """Elimina una notificación específica del usuario."""
    if request.method != 'POST':
        return HttpResponseForbidden('Invalid')
    nid = request.POST.get('notification_id')
    if not nid:
        messages.error(request, 'Notificación no especificada.')
        return redirect('notifications')
    try:
        n = Notification.objects.get(pk=nid, recipient=request.user)
        n.delete()
        messages.success(request, 'Notificación eliminada.')
    except Notification.DoesNotExist:
        messages.error(request, 'Notificación no encontrada.')
    return redirect('notifications')


@login_required
def delete_all_notifications(request):
    """Elimina todas las notificaciones del usuario."""
    if request.method != 'POST':
        return HttpResponseForbidden('Invalid')
    count = Notification.objects.filter(recipient=request.user).count()
    Notification.objects.filter(recipient=request.user).delete()
    messages.success(request, f'{count} notificación{"es" if count != 1 else ""} eliminada{"s" if count != 1 else ""}.')
    return redirect('notifications')


