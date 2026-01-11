import csv
import io
import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.models import Notification, UserProfile

from .models import (
    Empresa,
    EmpresaAsiento,
    EmpresaComment,
    EmpresaPlanCuenta,
    EmpresaSupervisor,
    EmpresaTransaccion,
)
from .services import AsientoService, EstadosFinancierosService, LibroMayorService


@login_required
def my_companies(request):
    """Lista las empresas del usuario actual."""
    # Esta ruta ahora redirige al home centralizado donde se muestra la lista de empresas.
    return redirect("home")


@login_required
def create_company(request):
    # Determinar si el usuario es docente para mostrar la opción de plantilla
    is_docente = False
    try:
        is_docente = (
            hasattr(request.user, "userprofile")
            and request.user.userprofile.rol == UserProfile.Roles.DOCENTE
        )
    except Exception:
        is_docente = False

    if request.method == "POST":
        nombre = request.POST.get("nombre")
        descripcion = request.POST.get("descripcion", "")
        eslogan = request.POST.get("eslogan", "")
        logo = request.FILES.get("logo")
        # Solo permitir marcar como plantilla si es docente o superuser
        requested_template = request.POST.get("is_template") == "1"
        is_template = requested_template and (is_docente or request.user.is_superuser)
        if not nombre:
            messages.error(request, "El nombre es obligatorio.")
            return redirect("contabilidad:create_company")
        # Las empresas creadas por estudiantes no son visibles por defecto para sus docentes
        visible_default = True if (is_docente or request.user.is_superuser) else False
        emp = Empresa.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            eslogan=eslogan,
            logo=logo,
            owner=request.user,
            is_template=is_template,
            visible_to_supervisor=visible_default,
        )
        messages.success(request, f'Empresa "{emp.nombre}" creada.')
        return redirect("home")
    return render(request, "contabilidad/create_company.html", {"is_docente": is_docente})


@login_required
def generate_join_code(request, empresa_id):
    emp = get_object_or_404(Empresa, pk=empresa_id)
    # Solo docentes (propio docente) o superuser pueden generar join codes.
    is_docente = False
    try:
        is_docente = (
            hasattr(request.user, "userprofile")
            and request.user.userprofile.rol == UserProfile.Roles.DOCENTE
        )
    except Exception:
        is_docente = False

    if not (request.user.is_superuser or (is_docente and emp.owner == request.user)):
        return HttpResponseForbidden("No autorizado")
    code = emp.generate_join_code()
    messages.success(request, f"Join code generado: {code}")
    return redirect("home")


@login_required
def import_company(request):
    """Endpoint para que un estudiante importe una empresa por join_code (POST).

    Si la plantilla es encontrada, se crea una copia para el usuario y se registra
    una relación `EmpresaSupervisor` entre la nueva empresa y el docente propietario.
    """
    if request.method != "POST":
        return HttpResponseForbidden("Invalid")
    join_code = request.POST.get("join_code", "").strip()
    if not join_code:
        messages.error(request, "Código requerido.")
        return redirect("contabilidad:my_companies")
    try:
        new_emp = Empresa.import_from_template(join_code, request.user)
        # Registrar relación de supervisión con el docente original si existe
        if new_emp.original and new_emp.original.owner:
            try:
                EmpresaSupervisor.objects.get_or_create(
                    empresa=new_emp, docente=new_emp.original.owner
                )
            except Exception:
                pass

        messages.success(request, f"Empresa importada: {new_emp.nombre}")
        return redirect("home")
    except Empresa.DoesNotExist:
        messages.error(request, "Código inválido o plantilla no encontrada.")
        return redirect("contabilidad:my_companies")


@login_required
def company_detail(request, empresa_id):
    """Mostrar paneles de la empresa: Plan de cuentas, Libro Diario, Libro Mayor, etc.

    Permisos: propietario (owner), supervisores (docente) o superuser.
    """
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    # Check permission: owner, superuser, or supervisor
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    ):
        return HttpResponseForbidden("No autorizado para ver esta empresa")

    # Determinar si el usuario puede editar (solo owner)
    can_edit = (request.user == empresa.owner) or request.user.is_superuser

    # Determinar si el usuario es docente (para mostrar acciones específicas)
    is_docente = False
    try:
        is_docente = (
            hasattr(request.user, "userprofile")
            and request.user.userprofile.rol == UserProfile.Roles.DOCENTE
        )
    except Exception:
        is_docente = False

    return render(
        request,
        "contabilidad/company_detail.html",
        {"empresa": empresa, "can_edit": can_edit, "is_docente": is_docente},
    )


@login_required
def edit_company(request, empresa_id):
    """Permite al propietario editar el nombre y descripción de la empresa."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    # Solo el owner o superuser puede editar
    if not (request.user == empresa.owner or request.user.is_superuser):
        return HttpResponseForbidden("No autorizado para editar esta empresa")

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        descripcion = request.POST.get("descripcion", "").strip()
        eslogan = request.POST.get("eslogan", "").strip()
        logo = request.FILES.get("logo")

        if not nombre:
            messages.error(request, "El nombre es obligatorio.")
            return redirect("contabilidad:edit_company", empresa_id=empresa.id)

        empresa.nombre = nombre
        empresa.descripcion = descripcion
        empresa.eslogan = eslogan
        if logo:
            empresa.logo = logo
        empresa.save(update_fields=["nombre", "descripcion", "eslogan", "logo"])

        messages.success(request, f'Empresa "{empresa.nombre}" actualizada correctamente.')
        return redirect("contabilidad:company_detail", empresa_id=empresa.id)

    return render(request, "contabilidad/edit_company.html", {"empresa": empresa})


@login_required
def delete_company(request, empresa_id):
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    # Solo el owner o superuser puede eliminar
    if not (request.user == empresa.owner or request.user.is_superuser):
        return HttpResponseForbidden("No autorizado para eliminar esta empresa")

    if request.method == "POST":
        nombre = empresa.nombre
        try:
            with transaction.atomic():
                # 1) Borrar asientos y sus transacciones (CASCADE por FK "asiento")
                EmpresaAsiento.objects.filter(empresa=empresa).delete()

                # 2) Borrar cuentas del plan (asegurando borrar hojas primero para respetar FK padre PROTECT)
                cuentas = list(EmpresaPlanCuenta.objects.filter(empresa=empresa))
                # Ordenar por profundidad (más puntos primero) para eliminar de hojas -> raíz
                cuentas.sort(key=lambda c: (c.codigo or "").count("."), reverse=True)
                for c in cuentas:
                    try:
                        c.delete()
                    except ProtectedError:
                        # Si por alguna razón quedan referencias, abortamos con mensaje claro
                        raise

                # 3) Eliminar relaciones adicionales
                EmpresaSupervisor.objects.filter(empresa=empresa).delete()
                EmpresaComment.objects.filter(empresa=empresa).delete()

                # 4) Finalmente eliminar la empresa
                empresa.delete()

            messages.success(request, f'Empresa "{nombre}" eliminada.')
            return redirect("home")
        except ProtectedError:
            messages.error(
                request,
                "No se pudo eliminar la empresa porque existen registros relacionados protegidos "
                "(por ejemplo, cuentas con dependencias). Revise transacciones/cuentas e intente nuevamente.",
            )
            return redirect("contabilidad:company_detail", empresa_id=empresa.id)

    return render(request, "contabilidad/delete_company_confirm.html", {"empresa": empresa})


@login_required
@require_POST
def toggle_visibility(request, empresa_id):
    """Permite al owner activar/desactivar la visibilidad de su empresa para el docente supervisor."""
    emp = get_object_or_404(Empresa, pk=empresa_id)
    if emp.owner != request.user:
        return HttpResponseForbidden("No autorizado")

    # toggle
    emp.visible_to_supervisor = not bool(emp.visible_to_supervisor)
    emp.save(update_fields=["visible_to_supervisor"])

    status = "habilitada" if emp.visible_to_supervisor else "deshabilitada"
    messages.success(request, f'Visibilidad para supervisores {status} para "{emp.nombre}".')
    return redirect("home")


@login_required
@require_POST
def toggle_visibility_api(request, empresa_id):
    """AJAX endpoint: toggle visibility and return JSON response.

    Permission checks mirror `toggle_visibility`. Returns 403 if not allowed,
    otherwise returns the new visibility state.
    """
    emp = get_object_or_404(Empresa, pk=empresa_id)
    if emp.owner != request.user:
        return JsonResponse({"error": "forbidden"}, status=403)

    emp.visible_to_supervisor = not bool(emp.visible_to_supervisor)
    emp.save(update_fields=["visible_to_supervisor"])

    return JsonResponse(
        {
            "empresa_id": emp.id,
            "visible": bool(emp.visible_to_supervisor),
            "message": "Visibilidad actualizada.",
        }
    )


@login_required
def company_plan(request, empresa_id):
    """Mostrar Plan de Cuentas de la empresa (lectura). Supervisores pueden ver si la empresa es visible."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    # Permisos: owner, superuser, or supervisor with visible flag
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
        return HttpResponseForbidden("No autorizado")

    cuentas = (
        EmpresaPlanCuenta.objects.filter(empresa=empresa).select_related("padre").order_by("codigo")
    )
    comments = (
        empresa.comments.filter(section="PL").select_related("author").order_by("-created_at")
    )
    can_edit = (request.user == empresa.owner) or request.user.is_superuser

    # Determinar si el usuario es docente
    is_docente = False
    try:
        is_docente = (
            hasattr(request.user, "userprofile")
            and request.user.userprofile.rol == UserProfile.Roles.DOCENTE
        )
    except:
        is_docente = False

    return render(
        request,
        "contabilidad/company_plan.html",
        {
            "empresa": empresa,
            "cuentas": cuentas,
            "comments": comments,
            "is_supervisor": is_supervisor,
            "can_edit": can_edit,
            "is_docente": is_docente,
        },
    )


@login_required
@require_POST
def add_account(request, empresa_id):
    """Crear una cuenta dentro del Plan de Cuentas de la empresa.

    Solo el owner de la empresa o superuser puede crear cuentas.
    Campos esperados: codigo, descripcion, tipo, naturaleza, es_auxiliar (on), padre_id (opcional).
    """
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    if not ((request.user == empresa.owner) or request.user.is_superuser):
        return HttpResponseForbidden("No autorizado")

    codigo = request.POST.get("codigo", "").strip()
    descripcion = request.POST.get("descripcion", "").strip()
    tipo = request.POST.get("tipo")
    naturaleza = request.POST.get("naturaleza")
    es_auxiliar = request.POST.get("es_auxiliar") == "1"
    padre_id = request.POST.get("padre") or None

    if not codigo or not descripcion:
        messages.error(request, "Código y descripción son obligatorios.")
        return redirect("contabilidad:company_plan", empresa_id=empresa.id)

    # Validar unicidad del código dentro de la empresa
    if EmpresaPlanCuenta.objects.filter(empresa=empresa, codigo=codigo).exists():
        messages.error(request, f"Ya existe una cuenta con el código {codigo} en esta empresa.")
        return redirect("contabilidad:company_plan", empresa_id=empresa.id)

    # Validar que 'tipo' y 'naturaleza' sean valores permitidos
    valid_tipos = [t[0] for t in EmpresaPlanCuenta._meta.get_field("tipo").choices]
    valid_naturalezas = [n[0] for n in EmpresaPlanCuenta._meta.get_field("naturaleza").choices]
    if tipo and tipo not in valid_tipos:
        messages.error(request, "Tipo de cuenta inválido.")
        return redirect("contabilidad:company_plan", empresa_id=empresa.id)
    if naturaleza and naturaleza not in valid_naturalezas:
        messages.error(request, "Naturaleza de cuenta inválida.")
        return redirect("contabilidad:company_plan", empresa_id=empresa.id)

    padre = None
    if padre_id:
        try:
            padre = EmpresaPlanCuenta.objects.get(pk=int(padre_id), empresa=empresa)
        except Exception:
            padre = None

    # Crear la cuenta
    try:
        EmpresaPlanCuenta.objects.create(
            empresa=empresa,
            codigo=codigo,
            descripcion=descripcion,
            tipo=tipo or EmpresaPlanCuenta._meta.get_field("tipo").choices[0][0],
            naturaleza=naturaleza or EmpresaPlanCuenta._meta.get_field("naturaleza").choices[0][0],
            es_auxiliar=bool(es_auxiliar),
            padre=padre,
        )
        messages.success(request, f"Cuenta {codigo} creada correctamente.")
    except Exception as e:
        messages.error(request, f"Error al crear la cuenta: {e}")

    return redirect("contabilidad:company_plan", empresa_id=empresa.id)


@login_required
@require_POST
def toggle_account_status(request, empresa_id, cuenta_id):
    """Activar/desactivar una cuenta del plan.

    Esto es más seguro que eliminar ya que preserva la integridad histórica.
    """
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    if not ((request.user == empresa.owner) or request.user.is_superuser):
        return HttpResponseForbidden("No autorizado")

    cuenta = get_object_or_404(EmpresaPlanCuenta, pk=cuenta_id, empresa=empresa)
    cuenta.activa = not cuenta.activa
    cuenta.save()

    estado = "activada" if cuenta.activa else "desactivada"
    messages.success(request, f"Cuenta {cuenta.codigo} {estado} correctamente.")
    return redirect("contabilidad:company_plan", empresa_id=empresa.id)


@login_required
@require_POST
def edit_account_description(request, empresa_id, cuenta_id):
    """Editar la descripción de una cuenta.

    Solo permite editar si la cuenta no tiene transacciones asociadas.
    """
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    if not ((request.user == empresa.owner) or request.user.is_superuser):
        return HttpResponseForbidden("No autorizado")

    cuenta = get_object_or_404(EmpresaPlanCuenta, pk=cuenta_id, empresa=empresa)

    # Verificar si tiene transacciones
    tiene_transacciones = EmpresaTransaccion.objects.filter(cuenta=cuenta).exists()
    if tiene_transacciones:
        messages.error(
            request,
            f"No se puede editar la cuenta {cuenta.codigo} porque tiene transacciones asociadas.",
        )
        return redirect("contabilidad:company_plan", empresa_id=empresa.id)

    nueva_descripcion = request.POST.get("descripcion", "").strip()
    if not nueva_descripcion:
        messages.error(request, "La descripción no puede estar vacía.")
        return redirect("contabilidad:company_plan", empresa_id=empresa.id)

    cuenta.descripcion = nueva_descripcion
    cuenta.save()

    messages.success(request, f"Descripción de cuenta {cuenta.codigo} actualizada correctamente.")
    return redirect("contabilidad:company_plan", empresa_id=empresa.id)


@login_required
@require_POST
def delete_account(request, empresa_id, cuenta_id):
    """Eliminar una cuenta del plan.

    Solo permite eliminar si:
    - No tiene transacciones asociadas
    - No tiene cuentas hijas
    """
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    if not ((request.user == empresa.owner) or request.user.is_superuser):
        return HttpResponseForbidden("No autorizado")

    cuenta = get_object_or_404(EmpresaPlanCuenta, pk=cuenta_id, empresa=empresa)

    # Verificar si tiene transacciones
    tiene_transacciones = EmpresaTransaccion.objects.filter(cuenta=cuenta).exists()
    if tiene_transacciones:
        messages.error(
            request,
            f"No se puede eliminar la cuenta {cuenta.codigo} porque tiene transacciones asociadas. Considera desactivarla en su lugar.",
        )
        return redirect("contabilidad:company_plan", empresa_id=empresa.id)

    # Verificar si tiene cuentas hijas
    tiene_hijas = EmpresaPlanCuenta.objects.filter(empresa=empresa, padre=cuenta).exists()
    if tiene_hijas:
        messages.error(
            request,
            f"No se puede eliminar la cuenta {cuenta.codigo} porque tiene subcuentas. Elimina primero las subcuentas.",
        )
        return redirect("contabilidad:company_plan", empresa_id=empresa.id)

    codigo_eliminado = cuenta.codigo
    cuenta.delete()

    messages.success(request, f"Cuenta {codigo_eliminado} eliminada correctamente.")
    return redirect("contabilidad:company_plan", empresa_id=empresa.id)


@login_required
def company_diario(request, empresa_id):
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
        return HttpResponseForbidden("No autorizado")

    asientos = (
        EmpresaAsiento.objects.filter(empresa=empresa)
        .select_related("creado_por")
        .prefetch_related("lineas__cuenta")
        .order_by("-fecha")
    )
    comments = (
        empresa.comments.filter(section="DI").select_related("author").order_by("-created_at")
    )
    can_edit = (request.user == empresa.owner) or request.user.is_superuser
    # Obtener cuentas hojas (sin hijos) y activas para usar en asientos
    from django.db.models import Exists, OuterRef

    cuentas_aux = (
        EmpresaPlanCuenta.objects.filter(empresa=empresa, activa=True)
        .annotate(_tiene_hijos=Exists(EmpresaPlanCuenta.objects.filter(padre=OuterRef("pk"))))
        .exclude(_tiene_hijos=True)
        .order_by("codigo")
    )

    # Determinar si el usuario es docente
    is_docente = False
    try:
        is_docente = (
            hasattr(request.user, "userprofile")
            and request.user.userprofile.rol == UserProfile.Roles.DOCENTE
        )
    except:
        is_docente = False

    return render(
        request,
        "contabilidad/company_diario.html",
        {
            "empresa": empresa,
            "asientos": asientos,
            "comments": comments,
            "is_supervisor": is_supervisor,
            "is_docente": is_docente,
            "can_edit": can_edit,
            "cuentas_aux": cuentas_aux,
        },
    )


@login_required
def company_mayor(request, empresa_id):
    """Vista del Libro Mayor con filtros de cuenta y rango de fechas."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
        return HttpResponseForbidden("No autorizado")

    # Filtros de la solicitud
    cuenta_id = request.GET.get("cuenta_id")
    fecha_inicio_str = request.GET.get("fecha_inicio")
    fecha_fin_str = request.GET.get("fecha_fin")

    # Parsear fechas
    fecha_inicio = None
    fecha_fin = None
    if fecha_inicio_str:
        try:
            fecha_inicio = date.fromisoformat(fecha_inicio_str)
        except:
            pass
    if fecha_fin_str:
        try:
            fecha_fin = date.fromisoformat(fecha_fin_str)
        except:
            pass

    # Obtener todas las cuentas auxiliares para el selector
    cuentas_aux = EmpresaPlanCuenta.objects.filter(empresa=empresa, es_auxiliar=True).order_by(
        "codigo"
    )

    # Calcular saldos si hay cuenta seleccionada
    saldos_data = None
    cuenta_seleccionada = None
    if cuenta_id:
        try:
            cuenta_seleccionada = EmpresaPlanCuenta.objects.get(id=cuenta_id, empresa=empresa)
            saldos_data = LibroMayorService.calcular_saldos_cuenta(
                cuenta=cuenta_seleccionada,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                incluir_borradores=False,
            )
        except EmpresaPlanCuenta.DoesNotExist:
            messages.error(request, "Cuenta no encontrada.")

    # Comentarios de la sección Mayor
    comments = (
        empresa.comments.filter(section="MA").select_related("author").order_by("-created_at")
    )
    can_edit = (request.user == empresa.owner) or request.user.is_superuser

    # Determinar si el usuario es docente
    is_docente = False
    try:
        is_docente = (
            hasattr(request.user, "userprofile")
            and request.user.userprofile.rol == UserProfile.Roles.DOCENTE
        )
    except:
        is_docente = False

    return render(
        request,
        "contabilidad/company_mayor.html",
        {
            "empresa": empresa,
            "cuentas_aux": cuentas_aux,
            "cuenta_seleccionada": cuenta_seleccionada,
            "saldos_data": saldos_data,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "comments": comments,
            "is_supervisor": is_supervisor,
            "is_docente": is_docente,
            "can_edit": can_edit,
        },
    )


@login_required
@require_POST
def create_journal_entry(request, empresa_id):
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    # Solo el owner o superuser puede crear asientos
    if not (request.user == empresa.owner or request.user.is_superuser):
        return HttpResponseForbidden("No autorizado")

    fecha_str = request.POST.get("fecha")
    descripcion = request.POST.get("descripcion", "").strip()
    lineas_json = request.POST.get("lineas_json", "[]")

    try:
        f = date.fromisoformat(fecha_str) if fecha_str else date.today()
    except Exception:
        messages.error(request, "Fecha inválida.")
        return redirect("contabilidad:company_diario", empresa_id=empresa.id)

    try:
        raw = json.loads(lineas_json)
        lineas = []
        for idx, item in enumerate(raw):
            try:
                cuenta_id = int(item.get("cuenta_id"))
            except Exception:
                raise ValidationError(f"Línea {idx + 1}: cuenta inválida")
            detalle = (item.get("detalle") or "").strip()
            debe = str(item.get("debe") or "0")
            haber = str(item.get("haber") or "0")
            lineas.append(
                {
                    "cuenta_id": cuenta_id,
                    "detalle": detalle,
                    "debe": debe,
                    "haber": haber,
                }
            )
    except ValidationError as ve:
        messages.error(request, str(ve))
        return redirect("contabilidad:company_diario", empresa_id=empresa.id)
    except Exception:
        messages.error(request, "No se pudieron leer las líneas del asiento.")
        return redirect("contabilidad:company_diario", empresa_id=empresa.id)

    try:
        AsientoService.crear_asiento(
            empresa=empresa,
            fecha=f,
            descripcion=descripcion or "Asiento contable",
            lineas=lineas,
            creado_por=request.user,
            auto_confirmar=True,
        )
        messages.success(request, "Asiento creado correctamente.")
    except ValidationError as e:
        # e.messages puede ser lista o string
        msg = "; ".join(e.messages) if hasattr(e, "messages") else str(e)
        messages.error(request, msg)
    except Exception as e:
        messages.error(request, f"Error al crear el asiento: {e}")

    return redirect("contabilidad:company_diario", empresa_id=empresa.id)


@login_required
@require_POST
def add_comment(request, empresa_id, section):
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    # Solo docentes supervisores o superuser pueden comentar
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (request.user.is_superuser or is_supervisor):
        return HttpResponseForbidden("No autorizado")

    content = request.POST.get("content", "").strip()
    if not content:
        messages.error(request, "El comentario no puede estar vacío.")
        return redirect(request.META.get("HTTP_REFERER", "contabilidad:company_detail"))

    if section not in dict((k, v) for k, v in EmpresaComment.SECTION_CHOICES):
        messages.error(request, "Sección inválida.")
        return redirect(request.META.get("HTTP_REFERER", "contabilidad:company_detail"))

    # Crear el comentario
    comment = EmpresaComment.objects.create(
        empresa=empresa, section=section, author=request.user, content=content
    )

    # Crear notificación para el dueño de la empresa (estudiante)
    section_names = {
        "PL": "Plan de Cuentas",
        "DI": "Libro Diario",
        "MA": "Libro Mayor",
        "BC": "Balance de Comprobación",
        "EF": "Estados Financieros",
    }

    # Solo notificar si el autor no es el dueño (evitar auto-notificaciones)
    if request.user != empresa.owner:
        # Determinar la URL según la sección
        section_urls = {
            "PL": reverse("contabilidad:company_plan", args=[empresa.id]) + "#comments-section",
            "DI": reverse("contabilidad:company_diario", args=[empresa.id]) + "#comments-section",
            "MA": reverse("contabilidad:company_mayor", args=[empresa.id]) + "#comments-section",
            "BC": reverse("contabilidad:company_balance_comprobacion", args=[empresa.id])
            + "#comments-section",
            "EF": reverse("contabilidad:company_estados_financieros", args=[empresa.id])
            + "#comments-section",
        }
        url = section_urls.get(section, reverse("contabilidad:company_detail", args=[empresa.id]))

        Notification.objects.create(
            recipient=empresa.owner,
            actor=request.user,
            verb="commented",
            empresa=empresa,
            comment_section=section,
            url=url,
            unread=True,
        )

    messages.success(request, "Comentario agregado.")
    # Redirect back to the referring page
    return redirect(request.META.get("HTTP_REFERER", "contabilidad:company_detail"))


@login_required
def company_balance_comprobacion(request, empresa_id):
    """Vista del Balance de Comprobación."""
    empresa = get_object_or_404(Empresa, id=empresa_id)

    # Verificar permisos
    if empresa.owner != request.user:
        supervisor_access = EmpresaSupervisor.objects.filter(
            empresa=empresa, docente=request.user
        ).exists()
        if not (supervisor_access and empresa.visible_to_supervisor):
            return HttpResponseForbidden("No tienes permisos para ver esta empresa.")

    # Obtener parámetros de fecha
    fecha_inicio_str = request.GET.get("fecha_inicio")
    fecha_fin_str = request.GET.get("fecha_fin")

    # Valores por defecto: primer y último día del año actual
    from datetime import datetime

    hoy = date.today()
    fecha_inicio = date(hoy.year, 1, 1)
    fecha_fin = hoy

    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        except ValueError:
            messages.warning(request, "Fecha de inicio inválida, usando valor por defecto.")

    if fecha_fin_str:
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except ValueError:
            messages.warning(request, "Fecha de fin inválida, usando valor por defecto.")

    # Obtener todas las cuentas auxiliares con movimientos
    cuentas_con_movimientos = []
    cuentas = empresa.cuentas.filter(es_auxiliar=True).order_by("codigo")

    total_saldo_inicial = {"deudor": 0, "acreedor": 0}
    total_movimientos = {"debe": 0, "haber": 0}
    total_saldo_final = {"deudor": 0, "acreedor": 0}

    for cuenta in cuentas:
        saldos = LibroMayorService.calcular_saldos_cuenta(
            cuenta=cuenta, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin
        )

        # Solo incluir cuentas con algún movimiento o saldo
        if (
            saldos["saldo_inicial"] != 0
            or saldos["debe"] != 0
            or saldos["haber"] != 0
            or saldos["saldo_final"] != 0
        ):
            # Determinar columna de saldo inicial (deudor/acreedor)
            saldo_inicial_deudor = saldos["saldo_inicial"] if saldos["saldo_inicial"] > 0 else 0
            saldo_inicial_acreedor = (
                abs(saldos["saldo_inicial"]) if saldos["saldo_inicial"] < 0 else 0
            )

            # Determinar columna de saldo final (deudor/acreedor)
            saldo_final_deudor = saldos["saldo_final"] if saldos["saldo_final"] > 0 else 0
            saldo_final_acreedor = abs(saldos["saldo_final"]) if saldos["saldo_final"] < 0 else 0

            cuentas_con_movimientos.append(
                {
                    "cuenta": cuenta,
                    "saldo_inicial_deudor": saldo_inicial_deudor,
                    "saldo_inicial_acreedor": saldo_inicial_acreedor,
                    "debe": saldos["debe"],
                    "haber": saldos["haber"],
                    "saldo_final_deudor": saldo_final_deudor,
                    "saldo_final_acreedor": saldo_final_acreedor,
                }
            )

            # Acumular totales
            total_saldo_inicial["deudor"] += saldo_inicial_deudor
            total_saldo_inicial["acreedor"] += saldo_inicial_acreedor
            total_movimientos["debe"] += saldos["debe"]
            total_movimientos["haber"] += saldos["haber"]
            total_saldo_final["deudor"] += saldo_final_deudor
            total_saldo_final["acreedor"] += saldo_final_acreedor

    # Verificar cuadratura
    cuadra_inicial = abs(total_saldo_inicial["deudor"] - total_saldo_inicial["acreedor"]) < 0.01
    cuadra_movimientos = abs(total_movimientos["debe"] - total_movimientos["haber"]) < 0.01
    cuadra_final = abs(total_saldo_final["deudor"] - total_saldo_final["acreedor"]) < 0.01
    cuadra_todo = cuadra_inicial and cuadra_movimientos and cuadra_final

    # Obtener comentarios para esta sección
    comments = (
        empresa.comments.filter(section="BC").select_related("author").order_by("-created_at")
    )

    # Verificar si es docente y supervisor
    is_docente = request.user.userprofile.rol == UserProfile.Roles.DOCENTE
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()

    context = {
        "empresa": empresa,
        "cuentas": cuentas_con_movimientos,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "total_saldo_inicial": total_saldo_inicial,
        "total_movimientos": total_movimientos,
        "total_saldo_final": total_saldo_final,
        "cuadra_inicial": cuadra_inicial,
        "cuadra_movimientos": cuadra_movimientos,
        "cuadra_final": cuadra_final,
        "cuadra_todo": cuadra_todo,
        "active_section": "balance",
        "comments": comments,
        "is_supervisor": is_supervisor,
        "is_docente": is_docente,
    }

    return render(request, "contabilidad/company_balance_comprobacion.html", context)


@login_required
def company_estados_financieros(request, empresa_id):
    """Vista de Estados Financieros (Balance General y Estado de Resultados)."""
    empresa = get_object_or_404(Empresa, id=empresa_id)

    # Verificar permisos
    if empresa.owner != request.user:
        supervisor_access = EmpresaSupervisor.objects.filter(
            empresa=empresa, docente=request.user
        ).exists()
        if not (supervisor_access and empresa.visible_to_supervisor):
            return HttpResponseForbidden("No tienes permisos para ver esta empresa.")

    # Obtener parámetros
    from datetime import datetime

    reporte = request.GET.get("reporte", "balance")  # 'balance' o 'resultados'
    fecha_str = request.GET.get("fecha")
    fecha_inicio_str = request.GET.get("fecha_inicio")
    fecha_fin_str = request.GET.get("fecha_fin")

    # Valores por defecto
    hoy = date.today()
    fecha_corte = hoy
    fecha_inicio = date(hoy.year, 1, 1)
    fecha_fin = hoy

    if fecha_str:
        try:
            fecha_corte = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            messages.warning(request, "Fecha inválida, usando hoy.")

    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    if fecha_fin_str:
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Generar reportes
    balance_general = None
    estado_resultados = None

    if reporte == "balance":
        balance_general = EstadosFinancierosService.balance_general(empresa, fecha_corte)
    else:  # resultados
        estado_resultados = EstadosFinancierosService.estado_de_resultados(
            empresa, fecha_inicio, fecha_fin
        )

    # Obtener comentarios para esta sección
    comments = (
        empresa.comments.filter(section="EF").select_related("author").order_by("-created_at")
    )

    # Verificar si es docente y supervisor
    is_docente = request.user.userprofile.rol == UserProfile.Roles.DOCENTE
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()

    context = {
        "empresa": empresa,
        "reporte": reporte,
        "balance_general": balance_general,
        "estado_resultados": estado_resultados,
        "fecha_corte": fecha_corte,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "active_section": "estados",
        "comments": comments,
        "is_supervisor": is_supervisor,
        "is_docente": is_docente,
    }

    return render(request, "contabilidad/company_estados_financieros.html", context)


@login_required
def export_balance_csv(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    if empresa.owner != request.user and not (
        EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
        and empresa.visible_to_supervisor
    ):
        return HttpResponseForbidden("No tienes permisos")
    from datetime import datetime

    fecha_inicio_str = request.GET.get("fecha_inicio")
    fecha_fin_str = request.GET.get("fecha_fin")
    hoy = date.today()
    fecha_inicio = date(hoy.year, 1, 1)
    fecha_fin = hoy
    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if fecha_fin_str:
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    cuentas = empresa.cuentas.filter(es_auxiliar=True).order_by("codigo")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Codigo",
            "Cuenta",
            "Saldo Inicial Deudor",
            "Saldo Inicial Acreedor",
            "Debe",
            "Haber",
            "Saldo Final Deudor",
            "Saldo Final Acreedor",
        ]
    )
    for cuenta in cuentas:
        s = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_inicio, fecha_fin)
        si_d = s["saldo_inicial"] if s["saldo_inicial"] > 0 else 0
        si_a = abs(s["saldo_inicial"]) if s["saldo_inicial"] < 0 else 0
        sf_d = s["saldo_final"] if s["saldo_final"] > 0 else 0
        sf_a = abs(s["saldo_final"]) if s["saldo_final"] < 0 else 0
        if si_d or si_a or s["debe"] or s["haber"] or sf_d or sf_a:
            writer.writerow(
                [
                    cuenta.codigo,
                    cuenta.descripcion,
                    f"{si_d:.2f}",
                    f"{si_a:.2f}",
                    f"{s['debe']:.2f}",
                    f"{s['haber']:.2f}",
                    f"{sf_d:.2f}",
                    f"{sf_a:.2f}",
                ]
            )
    resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="balance_{empresa.id}.csv"'
    return resp


@login_required
def export_estados_csv(request, empresa_id):
    empresa = get_object_or_404(Empresa, id=empresa_id)
    if empresa.owner != request.user and not (
        EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
        and empresa.visible_to_supervisor
    ):
        return HttpResponseForbidden("No tienes permisos")
    from datetime import datetime

    reporte = request.GET.get("reporte", "balance")
    fecha_str = request.GET.get("fecha")
    fecha_inicio_str = request.GET.get("fecha_inicio")
    fecha_fin_str = request.GET.get("fecha_fin")
    hoy = date.today()
    fecha_corte = hoy
    fecha_inicio = date(hoy.year, 1, 1)
    fecha_fin = hoy
    if fecha_str:
        try:
            fecha_corte = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if fecha_fin_str:
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if reporte == "balance":
        bg = EstadosFinancierosService.balance_general(empresa, fecha_corte)
        writer.writerow(["SECCION", "CODIGO", "CUENTA", "SALDO"])
        for det in bg["detalle_activos"]:
            writer.writerow(
                ["ACTIVO", det["cuenta"].codigo, det["cuenta"].descripcion, f"{det['saldo']:.2f}"]
            )
        for det in bg["detalle_pasivos"]:
            writer.writerow(
                ["PASIVO", det["cuenta"].codigo, det["cuenta"].descripcion, f"{det['saldo']:.2f}"]
            )
        for det in bg["detalle_patrimonio"]:
            writer.writerow(
                [
                    "PATRIMONIO",
                    det["cuenta"].codigo,
                    det["cuenta"].descripcion,
                    f"{det['saldo']:.2f}",
                ]
            )
        writer.writerow([])
        writer.writerow(["TOTALES", "", "", ""])
        writer.writerow(["ACTIVO", "", "", f"{bg['activos']:.2f}"])
        writer.writerow(["PASIVO", "", "", f"{bg['pasivos']:.2f}"])
        writer.writerow(["PATRIMONIO", "", "", f"{bg['patrimonio']:.2f}"])
        writer.writerow(["BALANCEADO", "", "", "SI" if bg["balanceado"] else "NO"])
    else:
        er = EstadosFinancierosService.estado_de_resultados(empresa, fecha_inicio, fecha_fin)
        writer.writerow(["SECCION", "CODIGO", "CUENTA", "MONTO"])
        for det in er["detalle_ingresos"]:
            writer.writerow(
                ["INGRESOS", det["cuenta"].codigo, det["cuenta"].descripcion, f"{det['monto']:.2f}"]
            )
        for det in er["detalle_costos"]:
            writer.writerow(
                ["COSTOS", det["cuenta"].codigo, det["cuenta"].descripcion, f"{det['monto']:.2f}"]
            )
        for det in er["detalle_gastos"]:
            writer.writerow(
                ["GASTOS", det["cuenta"].codigo, det["cuenta"].descripcion, f"{det['monto']:.2f}"]
            )
        writer.writerow([])
        writer.writerow(["TOTALES", "", "", ""])
        writer.writerow(["INGRESOS", "", "", f"{er['ingresos']:.2f}"])
        writer.writerow(["COSTOS", "", "", f"{er['costos']:.2f}"])
        writer.writerow(["GASTOS", "", "", f"{er['gastos']:.2f}"])
        writer.writerow(["UTILIDAD BRUTA", "", "", f"{er['utilidad_bruta']:.2f}"])
        writer.writerow(["UTILIDAD NETA", "", "", f"{er['utilidad_neta']:.2f}"])
    resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
    fname = "estados_balance" if reporte == "balance" else "estados_resultados"
    resp["Content-Disposition"] = f'attachment; filename="{fname}_{empresa.id}.csv"'
    return resp


@login_required
def export_balance_xlsx(request, empresa_id):
    try:
        import openpyxl
    except Exception:
        return export_balance_csv(request, empresa_id)
    empresa = get_object_or_404(Empresa, id=empresa_id)
    if empresa.owner != request.user and not (
        EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
        and empresa.visible_to_supervisor
    ):
        return HttpResponseForbidden("No tienes permisos")
    from datetime import datetime

    fecha_inicio_str = request.GET.get("fecha_inicio")
    fecha_fin_str = request.GET.get("fecha_fin")
    hoy = date.today()
    fecha_inicio = date(hoy.year, 1, 1)
    fecha_fin = hoy
    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if fecha_fin_str:
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Balance"
    ws.append(
        [
            "Balance de Comprobación",
            f"Empresa: {empresa.nombre}",
            f"Periodo: {fecha_inicio} a {fecha_fin}",
        ]
    )
    ws.append([])
    ws.append(
        [
            "Codigo",
            "Cuenta",
            "Saldo Inicial Deudor",
            "Saldo Inicial Acreedor",
            "Debe",
            "Haber",
            "Saldo Final Deudor",
            "Saldo Final Acreedor",
        ]
    )
    cuentas = empresa.cuentas.filter(es_auxiliar=True).order_by("codigo")
    for cuenta in cuentas:
        s = LibroMayorService.calcular_saldos_cuenta(cuenta, fecha_inicio, fecha_fin)
        si_d = s["saldo_inicial"] if s["saldo_inicial"] > 0 else 0
        si_a = abs(s["saldo_inicial"]) if s["saldo_inicial"] < 0 else 0
        sf_d = s["saldo_final"] if s["saldo_final"] > 0 else 0
        sf_a = abs(s["saldo_final"]) if s["saldo_final"] < 0 else 0
        if si_d or si_a or s["debe"] or s["haber"] or sf_d or sf_a:
            ws.append(
                [
                    cuenta.codigo,
                    cuenta.descripcion,
                    float(si_d),
                    float(si_a),
                    float(s["debe"]),
                    float(s["haber"]),
                    float(sf_d),
                    float(sf_a),
                ]
            )
    output = io.BytesIO()
    wb.save(output)
    resp = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="balance_{empresa.id}.xlsx"'
    return resp


@login_required
def export_estados_xlsx(request, empresa_id):
    try:
        import openpyxl
    except Exception:
        return export_estados_csv(request, empresa_id)
    empresa = get_object_or_404(Empresa, id=empresa_id)
    if empresa.owner != request.user and not (
        EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
        and empresa.visible_to_supervisor
    ):
        return HttpResponseForbidden("No tienes permisos")
    from datetime import datetime

    reporte = request.GET.get("reporte", "balance")
    fecha_str = request.GET.get("fecha")
    fecha_inicio_str = request.GET.get("fecha_inicio")
    fecha_fin_str = request.GET.get("fecha_fin")
    hoy = date.today()
    fecha_corte = hoy
    fecha_inicio = date(hoy.year, 1, 1)
    fecha_fin = hoy
    if fecha_str:
        try:
            fecha_corte = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    if fecha_fin_str:
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except ValueError:
            pass
    wb = openpyxl.Workbook()
    ws = wb.active
    if reporte == "balance":
        ws.title = "Balance General"
        bg = EstadosFinancierosService.balance_general(empresa, fecha_corte)
        ws.append(["Balance General", f"Empresa: {empresa.nombre}", f"Corte: {fecha_corte}"])
        ws.append([])
        ws.append(["SECCION", "CODIGO", "CUENTA", "SALDO"])
        for det in bg["detalle_activos"]:
            ws.append(
                ["ACTIVO", det["cuenta"].codigo, det["cuenta"].descripcion, float(det["saldo"])]
            )
        for det in bg["detalle_pasivos"]:
            ws.append(
                ["PASIVO", det["cuenta"].codigo, det["cuenta"].descripcion, float(det["saldo"])]
            )
        for det in bg["detalle_patrimonio"]:
            ws.append(
                ["PATRIMONIO", det["cuenta"].codigo, det["cuenta"].descripcion, float(det["saldo"])]
            )
        ws.append([])
        ws.append(["TOTALES", "", "", ""])
        ws.append(["ACTIVO", "", "", float(bg["activos"])])
        ws.append(["PASIVO", "", "", float(bg["pasivos"])])
        ws.append(["PATRIMONIO", "", "", float(bg["patrimonio"])])
        ws.append(["BALANCEADO", "", "", "SI" if bg["balanceado"] else "NO"])
    else:
        ws.title = "Estado Resultados"
        er = EstadosFinancierosService.estado_de_resultados(empresa, fecha_inicio, fecha_fin)
        ws.append(
            [
                "Estado de Resultados",
                f"Empresa: {empresa.nombre}",
                f"Periodo: {fecha_inicio} a {fecha_fin}",
            ]
        )
        ws.append([])
        ws.append(["SECCION", "CODIGO", "CUENTA", "MONTO"])
        for det in er["detalle_ingresos"]:
            ws.append(
                ["INGRESOS", det["cuenta"].codigo, det["cuenta"].descripcion, float(det["monto"])]
            )
        for det in er["detalle_costos"]:
            ws.append(
                ["COSTOS", det["cuenta"].codigo, det["cuenta"].descripcion, float(det["monto"])]
            )
        for det in er["detalle_gastos"]:
            ws.append(
                ["GASTOS", det["cuenta"].codigo, det["cuenta"].descripcion, float(det["monto"])]
            )
        ws.append([])
        ws.append(["TOTALES", "", "", ""])
        ws.append(["INGRESOS", "", "", float(er["ingresos"])])
        ws.append(["COSTOS", "", "", float(er["costos"])])
        ws.append(["GASTOS", "", "", float(er["gastos"])])
        ws.append(["UTILIDAD BRUTA", "", "", float(er["utilidad_bruta"])])
        ws.append(["UTILIDAD NETA", "", "", float(er["utilidad_neta"])])
    output = io.BytesIO()
    wb.save(output)
    fname = "estados_balance" if reporte == "balance" else "estados_resultados"
    resp = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{fname}_{empresa.id}.xlsx"'
    return resp


@login_required
def company_libro_mayor(request, empresa_id):
    """Vista del Libro Mayor por Cuenta"""
    empresa = get_object_or_404(Empresa, id=empresa_id)
    if empresa.owner != request.user and not (
        EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
        and empresa.visible_to_supervisor
    ):
        return HttpResponseForbidden("No tienes permisos")

    from datetime import datetime

    # Obtener cuentas auxiliares
    cuentas_auxiliares = empresa.cuentas.filter(es_auxiliar=True).order_by("codigo")

    # Parámetros
    cuenta_id = request.GET.get("cuenta_id")
    fecha_inicio_str = request.GET.get("fecha_inicio")
    fecha_fin_str = request.GET.get("fecha_fin")

    hoy = date.today()
    fecha_inicio = date(hoy.year, 1, 1)
    fecha_fin = hoy

    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    if fecha_fin_str:
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    context = {
        "empresa": empresa,
        "cuentas_auxiliares": cuentas_auxiliares,
        "cuenta_id": int(cuenta_id) if cuenta_id else None,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "movimientos": [],
        "totales": {"debe": 0, "haber": 0},
        "saldo_final": 0,
        "cuenta_actual": None,
    }

    if cuenta_id:
        try:
            cuenta_actual = EmpresaPlanCuenta.objects.get(id=cuenta_id, empresa=empresa)
            context["cuenta_actual"] = cuenta_actual

            # Obtener transacciones
            transacciones = (
                EmpresaTransaccion.objects.filter(
                    cuenta=cuenta_actual,
                    asiento__fecha__gte=fecha_inicio,
                    asiento__fecha__lte=fecha_fin,
                    asiento__anulado=False,
                )
                .select_related("asiento", "cuenta")
                .order_by("asiento__fecha", "asiento__id")
            )

            # Calcular saldo inicial
            saldos = LibroMayorService.calcular_saldos_cuenta(
                cuenta_actual, fecha_inicio, fecha_fin
            )
            saldo_acum = saldos["saldo_inicial"]

            movimientos = []
            total_debe = 0
            total_haber = 0

            for transaccion in transacciones:
                if transaccion.debe > 0:
                    saldo_acum += transaccion.debe
                else:
                    saldo_acum -= transaccion.haber

                movimientos.append(
                    {
                        "fecha": transaccion.asiento.fecha,
                        "numero_asiento": transaccion.asiento.numero,
                        "descripcion": transaccion.asiento.descripcion,
                        "debe": transaccion.debe,
                        "haber": transaccion.haber,
                        "saldo": saldo_acum,
                    }
                )

                total_debe += transaccion.debe
                total_haber += transaccion.haber

            context["movimientos"] = movimientos
            context["totales"] = {"debe": total_debe, "haber": total_haber}
            context["saldo_final"] = saldo_acum

        except EmpresaPlanCuenta.DoesNotExist:
            pass

    return render(request, "contabilidad/company_libro_mayor.html", context)


# ============================================================================
# VISTAS DE MACHINE LEARNING / INTELIGENCIA ARTIFICIAL
# ============================================================================


@login_required
def ml_dashboard(request, empresa_id):
    """Dashboard principal de ML/AI con métricas y visualizaciones."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    # Verificar permisos
    if not empresa.user_can_view(request.user):
        return HttpResponseForbidden("No tienes permiso para ver esta empresa.")

    context = {
        "empresa": empresa,
        "seccion_activa": "ml_dashboard",
        "titulo_pagina": "Dashboard ML/AI",
    }
    return render(request, "contabilidad/ml_dashboard.html", context)


@login_required
def ml_analytics(request, empresa_id):
    """Vista de analytics y métricas financieras."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    if not empresa.user_can_view(request.user):
        return HttpResponseForbidden("No tienes permiso para ver esta empresa.")

    context = {
        "empresa": empresa,
        "seccion_activa": "ml_analytics",
        "titulo_pagina": "Analytics Financiero",
    }
    return render(request, "contabilidad/ml_analytics.html", context)


@login_required
def ml_predictions(request, empresa_id):
    """Vista de predicciones financieras con Prophet."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    if not empresa.user_can_view(request.user):
        return HttpResponseForbidden("No tienes permiso para ver esta empresa.")

    context = {
        "empresa": empresa,
        "seccion_activa": "ml_predictions",
        "titulo_pagina": "Predicciones Financieras",
    }
    return render(request, "contabilidad/ml_predictions.html", context)


@login_required
def ml_anomalies(request, empresa_id):
    """Vista de detección y gestión de anomalías."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    if not empresa.user_can_view(request.user):
        return HttpResponseForbidden("No tienes permiso para ver esta empresa.")

    context = {
        "empresa": empresa,
        "seccion_activa": "ml_anomalies",
        "titulo_pagina": "Detección de Anomalías",
    }
    return render(request, "contabilidad/ml_anomalies.html", context)


@login_required
def ml_embeddings(request, empresa_id):
    """Vista de búsqueda semántica con embeddings."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    if not empresa.user_can_view(request.user):
        return HttpResponseForbidden("No tienes permiso para ver esta empresa.")

    context = {
        "empresa": empresa,
        "seccion_activa": "ml_embeddings",
        "titulo_pagina": "Búsqueda Semántica",
    }
    return render(request, "contabilidad/ml_embeddings.html", context)
