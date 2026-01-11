from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from contabilidad.models import Empresa

from .forms import RegistroForm
from .models import AuditLog, Invitation, Notification, Referral, UserProfile

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
        is_admin = request.user.is_superuser or (
            hasattr(request.user, "userprofile")
            and request.user.userprofile.rol == UserProfile.Roles.ADMIN
        )
        # docente: perfil rol=DOCENTE (no marcar superuser como docente)
        is_docente = (
            hasattr(request.user, "userprofile")
            and request.user.userprofile.rol == UserProfile.Roles.DOCENTE
        )
    except Exception:
        is_docente = False
        is_admin = False

    contexto = {
        "user": request.user,
        "is_docente": is_docente,
        "is_admin": is_admin,
        "empresas": Empresa.objects.filter(owner=request.user).select_related("original"),
    }
    return render(request, "core/home.html", contexto)


# --- ¡VISTA DE LOGIN PERSONALIZADA! ---
def login_view(request):
    """
    Maneja el inicio de sesión con comprobación de estado de activación.
    """
    # Si el usuario ya está autenticado, redirigir al home
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        # Obtenemos credenciales del POST
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        # Autenticar sin revelar si el usuario existe o no
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, "Credenciales inválidas.")
            empty_form = AuthenticationForm()
            return render(
                request, "core/login.html", {"form": empty_form, "username_value": username}
            )

        # La contraseña fue correcta: ahora verificamos estado del perfil.
        # NOTA: los superusuarios siempre pueden entrar (no requieren perfil activo).
        if not user.is_superuser:
            try:
                profile = user.userprofile
                if not profile.esta_activo:
                    messages.warning(
                        request,
                        "Tu cuenta está registrada, pero pendiente de activación por un administrador.",
                    )
                    empty_form = AuthenticationForm()
                    return render(
                        request, "core/login.html", {"form": empty_form, "username_value": username}
                    )
            except UserProfile.DoesNotExist:
                messages.error(
                    request, "Perfil de usuario no encontrado. Contacta al administrador."
                )
                empty_form = AuthenticationForm()
                return render(
                    request, "core/login.html", {"form": empty_form, "username_value": username}
                )

        login(request, user)
        logged_user = user

        # Respetar parámetro `next` si viene y es seguro
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}
        ):
            return redirect(next_url)

        return redirect("home")

    else:
        # Petición GET: solo muestra el formulario vacío
        form = AuthenticationForm()

    return render(request, "core/login.html", {"form": form})


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
    return render(request, "core/logout.html")


def registro_view(request):
    """
    Vista para el registro de nuevos usuarios.
    """
    # Determinar rol preseleccionado (viene como ?role=estudiante|docente desde login)
    role = request.GET.get("role", "estudiante")

    if request.method == "POST":
        # El template envía un campo oculto 'role' para que el form lo reciba
        form = RegistroForm(request.POST)
        if form.is_valid():
            form.save()  # Nuestro 'save' personalizado se encarga de todo
            # Informamos al usuario y redirigimos al login
            messages.success(
                request,
                "Registro completado. Tu cuenta está pendiente de activación.",
            )
            return redirect("login")
    else:
        # Preconfiguramos el formulario con el role seleccionado (no se muestra en UI)
        form = RegistroForm(initial={"role": role})

    contexto = {
        "form": form,
        "selected_role": role,
    }
    return render(request, "core/registro.html", contexto)


# --- Vista y decorador para docentes/admins ---
def is_docente_or_admin(user):
    try:
        return user.is_superuser or (
            hasattr(user, "userprofile") and user.userprofile.rol == UserProfile.Roles.DOCENTE
        )
    except Exception:
        return False


docente_required = user_passes_test(is_docente_or_admin, login_url="login")


@docente_required
def docente_alumnos_view(request):
    """Lista y gestiona estudiantes (activar/desactivar).

    GET: muestra lista paginada, filtrable por `q`.
    POST: procesa `profile_id` y `action` ('activar'|'desactivar').
    """
    if request.method == "POST":
        profile_id = request.POST.get("profile_id")
        action = request.POST.get("action")
        if not profile_id or action not in ("activar", "desactivar"):
            messages.error(request, "Solicitud inválida.")
            return redirect("docente_alumnos")

        profile = get_object_or_404(UserProfile, pk=profile_id)
        if profile.rol != UserProfile.Roles.ESTUDIANTE:
            messages.error(request, "Solo se pueden gestionar perfiles de estudiantes.")
            return redirect("docente_alumnos")

        profile.esta_activo = True if action == "activar" else False
        profile.save()
        # Registrar en audit log
        try:
            AuditLog.objects.create(
                actor=request.user,
                target_user=profile.user,
                action="activar_perfil" if profile.esta_activo else "desactivar_perfil",
                description=f"Perfil {'activado' if profile.esta_activo else 'desactivado'} por {request.user.username} desde UI docente.",
            )
        except Exception:
            # No fatal: si falla el logging no impedimos la operación
            pass

        messages.success(
            request,
            f"Perfil de {profile.user.username} {'activado' if profile.esta_activo else 'desactivado'}.",
        )
        return redirect("docente_alumnos")

    # GET: lista
    q = request.GET.get("q", "").strip()
    estudiantes = (
        UserProfile.objects.filter(rol=UserProfile.Roles.ESTUDIANTE)
        .select_related("user")
        .order_by("user__username")
    )
    if q:
        estudiantes = estudiantes.filter(
            Q(user__username__icontains=q)
            | Q(user__email__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
        )

    paginator = Paginator(estudiantes, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "core/docente_alumnos.html", {"page_obj": page_obj, "q": q})


@docente_required
def docente_dashboard_view(request):
    """Dashboard para que el docente vea sus grupos, estudiantes referidos y gestione códigos/invitaciones."""
    # POST: puede contener varias operaciones diferenciadas por 'operation'
    if request.method == "POST":
        operation = request.POST.get("operation")

        # Crear Grupo
        if operation == "create_grupo":
            from .forms import GrupoForm

            form = GrupoForm(request.POST)
            if form.is_valid():
                grupo = form.save(docente=request.user)
                try:
                    AuditLog.objects.create(
                        actor=request.user,
                        action="create_grupo",
                        description=f'Grupo "{grupo.nombre}" creado por {request.user.username}',
                    )
                except Exception:
                    pass
                messages.success(request, f'✅ Grupo "{grupo.nombre}" creado exitosamente.')
            else:
                messages.error(request, f"Error al crear el grupo: {form.errors}")
            return redirect("docente_dashboard")

        # Editar Grupo
        if operation == "edit_grupo":
            grupo_id = request.POST.get("grupo_id")
            if not grupo_id:
                messages.error(request, "Solicitud inválida.")
                return redirect("docente_dashboard")
            from .forms import GrupoForm
            from .models import Grupo

            grupo = get_object_or_404(Grupo, pk=grupo_id, docente=request.user)
            form = GrupoForm(request.POST, instance=grupo)
            if form.is_valid():
                form.save()
                try:
                    AuditLog.objects.create(
                        actor=request.user,
                        action="edit_grupo",
                        description=f'Grupo "{grupo.nombre}" editado por {request.user.username}',
                    )
                except Exception:
                    pass
                messages.success(request, f'✅ Grupo "{grupo.nombre}" actualizado exitosamente.')
            else:
                messages.error(request, f"Error al editar el grupo: {form.errors}")
            return redirect("docente_dashboard")

        # Eliminar/Desactivar Grupo
        if operation == "delete_grupo":
            grupo_id = request.POST.get("grupo_id")
            if not grupo_id:
                messages.error(request, "Solicitud inválida.")
                return redirect("docente_dashboard")
            from .models import Grupo

            grupo = get_object_or_404(Grupo, pk=grupo_id, docente=request.user)
            grupo_nombre = grupo.nombre
            # Desactivar en lugar de eliminar para mantener historial
            grupo.active = False
            grupo.save()
            try:
                AuditLog.objects.create(
                    actor=request.user,
                    action="delete_grupo",
                    description=f'Grupo "{grupo_nombre}" desactivado por {request.user.username}',
                )
            except Exception:
                pass
            # Respuesta AJAX
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": True, "grupo_id": grupo.id, "active": False})
            messages.success(request, f'✓ Grupo "{grupo_nombre}" desactivado exitosamente.')
            return redirect("docente_dashboard")

        # Activar Grupo
        if operation == "activate_grupo":
            grupo_id = request.POST.get("grupo_id")
            if not grupo_id:
                messages.error(request, "Solicitud inválida.")
                return redirect("docente_dashboard")
            from .models import Grupo

            grupo = get_object_or_404(Grupo, pk=grupo_id, docente=request.user)
            grupo_nombre = grupo.nombre
            grupo.active = True
            grupo.save()
            try:
                AuditLog.objects.create(
                    actor=request.user,
                    action="activate_grupo",
                    description=f'Grupo "{grupo_nombre}" activado por {request.user.username}',
                )
            except Exception:
                pass
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": True, "grupo_id": grupo.id, "active": True})
            messages.success(request, f'✓ Grupo "{grupo_nombre}" activado exitosamente.')
            return redirect("docente_dashboard")

        # Eliminar Grupo Permanentemente
        if operation == "permanent_delete_grupo":
            grupo_id = request.POST.get("grupo_id")
            if not grupo_id:
                messages.error(request, "Solicitud inválida.")
                return redirect("docente_dashboard")
            from .models import Grupo

            grupo = get_object_or_404(Grupo, pk=grupo_id, docente=request.user)
            grupo_nombre = grupo.nombre
            try:
                AuditLog.objects.create(
                    actor=request.user,
                    action="permanent_delete_grupo",
                    description=f'Grupo "{grupo_nombre}" eliminado permanentemente por {request.user.username}',
                )
            except Exception:
                pass
            # Eliminar el grupo (esto también eliminará invitaciones por CASCADE)
            grupo.delete()
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": True, "grupo_id": int(grupo_id), "removed": True})
            messages.success(request, f'✓ Grupo "{grupo_nombre}" eliminado permanentemente.')
            return redirect("docente_dashboard")

        # Referral activation/deactivation/delete
        if operation == "referral_action":
            referral_id = request.POST.get("referral_id")
            action = request.POST.get("action")
            if not referral_id or action not in ("activar", "desactivar", "eliminar"):
                messages.error(request, "Solicitud inválida.")
                return redirect("docente_dashboard")

            referral = get_object_or_404(Referral, pk=referral_id, docente=request.user)

            # Eliminar del grupo
            if action == "eliminar":
                student_username = referral.student.username
                grupo_nombre = referral.grupo.nombre if referral.grupo else "N/A"
                grupo_id = referral.grupo.id if referral.grupo else None
                try:
                    AuditLog.objects.create(
                        actor=request.user,
                        target_user=referral.student,
                        action="eliminar_referral",
                        description=f"Estudiante {student_username} eliminado del grupo '{grupo_nombre}' por {request.user.username} desde el dashboard.",
                    )
                except Exception:
                    pass
                referral.delete()
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    # Recalcular contadores del grupo
                    from .models import Grupo

                    students_count = 0
                    active_count = 0
                    if grupo_id:
                        g = Grupo.objects.filter(id=grupo_id, docente=request.user).first()
                        if g:
                            students_count = g.get_students_count()
                            active_count = g.get_active_students_count()
                    return JsonResponse(
                        {
                            "ok": True,
                            "referral_id": int(referral_id),
                            "removed": True,
                            "grupo_id": grupo_id,
                            "students_count": students_count,
                            "active_count": active_count,
                        }
                    )
                messages.success(
                    request,
                    f"❌ Estudiante {student_username} eliminado del grupo '{grupo_nombre}'.",
                )
                return redirect("docente_dashboard")

            # Activar / Desactivar dentro del grupo
            referral.activated = True if action == "activar" else False
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
                    action="activar_referral" if referral.activated else "desactivar_referral",
                    description=f"Referral {'activado' if referral.activated else 'desactivado'} por {request.user.username} en dashboard.",
                )
            except Exception:
                pass
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                # Recalcular contadores del grupo
                grupo_id = referral.grupo.id if referral.grupo else None
                students_count = referral.grupo.get_students_count() if referral.grupo else 0
                active_count = referral.grupo.get_active_students_count() if referral.grupo else 0
                return JsonResponse(
                    {
                        "ok": True,
                        "referral_id": referral.id,
                        "activated": referral.activated,
                        "grupo_id": grupo_id,
                        "students_count": students_count,
                        "active_count": active_count,
                    }
                )
            messages.success(
                request,
                f"{'✅' if referral.activated else '⚠️'} Estudiante {referral.student.username} {'activado' if referral.activated else 'desactivado'} exitosamente.",
            )
            return redirect("docente_dashboard")

        # Create Invitation
        if operation == "create_invitation":
            from .forms import InvitationForm  # Import local para evitar circular dependency

            form = InvitationForm(request.POST, docente=request.user)
            if form.is_valid():
                inv = form.save(creator=request.user)
                try:
                    AuditLog.objects.create(
                        actor=request.user,
                        action="create_invitation",
                        description=f"Invitation {inv.code} creada para grupo {inv.grupo.nombre}",
                    )
                except Exception:
                    pass
                messages.success(
                    request,
                    f'✅ Código de invitación creado: {inv.code} para el grupo "{inv.grupo.nombre}" (máx. {inv.max_uses} usos)',
                )
            else:
                messages.error(request, f"Error al crear el código: {form.errors}")
            return redirect("docente_dashboard")

        # Invitation actions: activar/desactivar/eliminar
        if operation == "invitation_action":
            inv_id = request.POST.get("invitation_id")
            inv_action = request.POST.get("inv_action")
            if not inv_id or inv_action not in ("activar", "desactivar", "eliminar"):
                messages.error(request, "Solicitud inválida.")
                return redirect("docente_dashboard")
            inv = get_object_or_404(Invitation, pk=inv_id, creator=request.user)
            if inv_action == "eliminar":
                # Verificar si hay estudiantes registrados con este código
                students_count = Referral.objects.filter(invitation=inv).count()
                if students_count > 0:
                    messages.error(
                        request,
                        f"⚠️ No se puede eliminar el código {inv.code} porque hay {students_count} estudiante(s) registrado(s) con él. Primero debe eliminar a los estudiantes del grupo.",
                    )
                    return redirect("docente_dashboard")

                try:
                    inv_code = inv.code
                    inv.delete()
                    try:
                        AuditLog.objects.create(
                            actor=request.user,
                            action="delete_invitation",
                            description=f"Invitation {inv_code} eliminada por {request.user.username}",
                        )
                    except Exception:
                        pass
                    messages.success(request, f"❌ Código {inv_code} eliminado permanentemente.")
                except ValidationError as e:
                    messages.error(request, str(e))
                    return redirect("docente_dashboard")
            else:
                inv.active = True if inv_action == "activar" else False
                inv.save()
                try:
                    AuditLog.objects.create(
                        actor=request.user,
                        action="toggle_invitation",
                        description=f"Invitation {inv.code} set active={inv.active} by {request.user.username}",
                    )
                except Exception:
                    pass
                messages.success(
                    request,
                    f"{'✅' if inv.active else '⚠️'} Código {inv.code} {'activado' if inv.active else 'desactivado'} exitosamente.",
                )
            return redirect("docente_dashboard")

    # GET: lista de grupos, referrals e invitaciones del docente
    from .forms import GrupoForm, InvitationForm
    from .models import Grupo

    # Mostrar todos los grupos (activos e inactivos) ordenados: activos primero
    grupos = (
        Grupo.objects.filter(docente=request.user)
        .prefetch_related("referrals__student")
        .order_by("-active", "-created_at")
    )

    q = request.GET.get("q", "").strip()
    referrals = (
        Referral.objects.filter(docente=request.user)
        .select_related("student", "invitation", "grupo")
        .order_by("-created_at")
    )
    invitations = (
        Invitation.objects.filter(creator=request.user)
        .select_related("grupo")
        .order_by("-created_at")
    )
    if q:
        referrals = referrals.filter(
            Q(student__username__icontains=q)
            | Q(student__email__icontains=q)
            | Q(student__first_name__icontains=q)
            | Q(student__last_name__icontains=q)
        )

    # Paginación ligera para referrals
    paginator = Paginator(referrals, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Obtener empresas supervisadas (compartidas por estudiantes)
    estudiantes_ids = referrals.values_list("student_id", flat=True).distinct()
    empresas_supervisadas = (
        Empresa.objects.filter(owner_id__in=estudiantes_ids, visible_to_supervisor=True)
        .select_related("owner")
        .order_by("-updated_at")[:50]
    )

    # Formularios para el template
    grupo_form = GrupoForm()
    invitation_form = InvitationForm(docente=request.user)

    return render(
        request,
        "core/docente_dashboard.html",
        {
            "grupos": grupos,
            "referrals": page_obj,
            "invitations": invitations,
            "empresas_supervisadas": empresas_supervisadas,
            "grupo_form": grupo_form,
            "invitation_form": invitation_form,
        },
    )


@login_required
def notifications_view(request):
    """Lista de notificaciones del usuario."""
    notes = Notification.objects.filter(recipient=request.user).order_by("-created_at")[:100]
    return render(request, "core/notifications.html", {"notifications": notes})


@login_required
def mark_notification_read(request):
    if request.method != "POST":
        return HttpResponseForbidden("Invalid")
    nid = request.POST.get("notification_id")
    if not nid:
        messages.error(request, "Notificación no especificada.")
        return redirect("notifications")
    try:
        n = Notification.objects.get(pk=nid, recipient=request.user)
        n.unread = False
        n.save()
        messages.success(request, "Notificación marcada como leída.")
    except Notification.DoesNotExist:
        messages.error(request, "Notificación no encontrada.")
    return redirect("notifications")


@login_required
def mark_all_notifications_read(request):
    if request.method != "POST":
        return HttpResponseForbidden("Invalid")
    Notification.objects.filter(recipient=request.user, unread=True).update(unread=False)
    messages.success(request, "Todas las notificaciones han sido marcadas como leídas.")
    return redirect("notifications")


@login_required
def delete_notification(request):
    """Elimina una notificación específica del usuario."""
    if request.method != "POST":
        return HttpResponseForbidden("Invalid")
    nid = request.POST.get("notification_id")
    if not nid:
        messages.error(request, "Notificación no especificada.")
        return redirect("notifications")
    try:
        n = Notification.objects.get(pk=nid, recipient=request.user)
        n.delete()
        messages.success(request, "Notificación eliminada.")
    except Notification.DoesNotExist:
        messages.error(request, "Notificación no encontrada.")
    return redirect("notifications")


@login_required
def delete_all_notifications(request):
    """Elimina todas las notificaciones del usuario."""
    if request.method != "POST":
        return HttpResponseForbidden("Invalid")
    count = Notification.objects.filter(recipient=request.user).count()
    Notification.objects.filter(recipient=request.user).delete()
    messages.success(
        request,
        f"{count} notificación{'es' if count != 1 else ''} eliminada{'s' if count != 1 else ''}.",
    )
    return redirect("notifications")


@login_required
@user_passes_test(
    lambda u: hasattr(u, "userprofile") and u.userprofile.rol == "docente", login_url="/"
)
def student_profile_view(request, student_id, grupo_id):
    """Vista para que el docente vea el perfil de un estudiante y sus empresas compartidas.

    Args:
        student_id: ID del estudiante
        grupo_id: ID del grupo al que pertenece el estudiante
    """
    from .models import Grupo

    # Verificar que el grupo pertenece al docente
    grupo = get_object_or_404(Grupo, pk=grupo_id, docente=request.user)

    # Verificar que el estudiante pertenece a ese grupo
    referral = get_object_or_404(Referral, grupo=grupo, student_id=student_id, docente=request.user)
    student = referral.student

    # Obtener las empresas del estudiante que están visibles para supervisores
    empresas_compartidas = Empresa.objects.filter(
        owner=student, visible_to_supervisor=True
    ).order_by("-updated_at")

    # Obtener todas las empresas del estudiante (para mostrar estadísticas)
    total_empresas = Empresa.objects.filter(owner=student).count()
    empresas_compartidas_count = empresas_compartidas.count()
    empresas_privadas = total_empresas - empresas_compartidas_count

    context = {
        "student": student,
        "grupo": grupo,
        "referral": referral,
        "empresas_compartidas": empresas_compartidas,
        "total_empresas": total_empresas,
        "empresas_compartidas_count": empresas_compartidas_count,
        "empresas_privadas": empresas_privadas,
    }

    return render(request, "core/student_profile.html", context)
