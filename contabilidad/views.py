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
from django.views.decorators.http import require_http_methods, require_POST

from core.models import Notification, UserProfile

from .forms import MovimientoKardexForm, ProductoInventarioForm
from .kardex_service import KardexService
from .ml_services import MLAnalyticsService
from .models import (
    Empresa,
    EmpresaAsiento,
    EmpresaComment,
    EmpresaPlanCuenta,
    EmpresaSupervisor,
    EmpresaTransaccion,
    ProductoInventario,
    TipoMovimientoKardex,
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

    VALIDACIÓN: El estudiante solo puede importar plantillas de docentes a los que
    pertenece (verificado mediante Referral/Grupo).
    """
    if request.method != "POST":
        return HttpResponseForbidden("Invalid")
    join_code = request.POST.get("join_code", "").strip()
    if not join_code:
        messages.error(request, "Código requerido.")
        return redirect("contabilidad:my_companies")

    try:
        # Buscar la plantilla
        template = Empresa.objects.get(join_code=join_code, is_template=True)
        docente_owner = template.owner

        # VALIDACIÓN: Verificar que el estudiante pertenece a un grupo del docente
        from core.models import Referral

        es_estudiante_del_docente = Referral.objects.filter(
            student=request.user,
            docente=docente_owner,
            activated=True,  # Solo estudiantes activados por el docente
        ).exists()

        if not es_estudiante_del_docente:
            messages.error(
                request,
                "No puedes importar esta plantilla. Solo puedes importar plantillas de "
                "docentes a cuyos grupos perteneces. Asegúrate de haberte unido mediante "
                "el código de invitación de tu docente.",
            )
            return redirect("contabilidad:my_companies")

        # Si pasa la validación, importar la empresa
        new_emp = template.copy_for_owner(request.user)

        # Registrar relación de supervisión con el docente original
        try:
            EmpresaSupervisor.objects.get_or_create(empresa=new_emp, docente=docente_owner)
        except Exception:
            pass

        messages.success(request, f"Empresa importada exitosamente: {new_emp.nombre}")
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
            auto_confirmar=False,  # Crear como BORRADOR por defecto
        )
        messages.success(
            request, "Asiento creado como borrador. Confírmalo para incluirlo en reportes."
        )
    except ValidationError as e:
        # e.messages puede ser lista o string
        msg = "; ".join(e.messages) if hasattr(e, "messages") else str(e)
        messages.error(request, msg)
    except Exception as e:
        messages.error(request, f"Error al crear el asiento: {e}")

    return redirect("contabilidad:company_diario", empresa_id=empresa.id)


@login_required
@require_POST
def confirmar_asiento(request, empresa_id, asiento_id):
    """Confirmar un asiento en estado BORRADOR."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    if not (request.user == empresa.owner or request.user.is_superuser):
        return HttpResponseForbidden("No autorizado")

    asiento = get_object_or_404(EmpresaAsiento, pk=asiento_id, empresa=empresa)

    try:
        AsientoService.confirmar_asiento(asiento)
        messages.success(
            request, f"Asiento #{asiento.numero_asiento} confirmado. Ahora se incluye en reportes."
        )
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Error al confirmar el asiento: {e}")

    return redirect("contabilidad:company_diario", empresa_id=empresa.id)


@login_required
@require_POST
def anular_asiento(request, empresa_id, asiento_id):
    """Anular un asiento confirmado (crea contra-asiento)."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    if not (request.user == empresa.owner or request.user.is_superuser):
        return HttpResponseForbidden("No autorizado")

    asiento = get_object_or_404(EmpresaAsiento, pk=asiento_id, empresa=empresa)
    motivo = request.POST.get("motivo", "Anulación por corrección").strip()

    try:
        contra_asiento = AsientoService.anular_asiento(asiento, request.user, motivo)
        messages.success(
            request,
            f"Asiento #{asiento.numero_asiento} anulado. Contra-asiento #{contra_asiento.numero_asiento} creado.",
        )
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Error al anular el asiento: {e}")

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
        "KD": "Kardex de Inventario",
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
            "KD": reverse("contabilidad:kardex_lista_productos", args=[empresa.id])
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
    is_docente = False
    try:
        is_docente = (
            hasattr(request.user, "userprofile")
            and request.user.userprofile.rol == UserProfile.Roles.DOCENTE
        )
    except Exception:
        is_docente = False
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
    is_docente = False
    try:
        is_docente = (
            hasattr(request.user, "userprofile")
            and request.user.userprofile.rol == UserProfile.Roles.DOCENTE
        )
    except Exception:
        is_docente = False
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


# DEPRECATED: export_balance_csv, export_balance_xlsx, export_estados_csv y export_estados_xlsx eliminadas.
# Usar export_empresa_completo_xlsx() para exportación consolidada con 8 hojas profesionales.


@login_required
def export_empresa_completo_xlsx(request, empresa_id):
    """
    Exporta un archivo Excel completo con toda la información de la empresa.
    Incluye: Plan de Cuentas, Balance de Comprobación, Estados Financieros,
    Métricas ML, Tendencias, Top Cuentas, etc.
    """
    empresa = get_object_or_404(Empresa, id=empresa_id)

    # Verificar permisos
    if empresa.owner != request.user and not (
        EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
        and empresa.visible_to_supervisor
    ):
        return HttpResponseForbidden("No tienes permisos para acceder a esta empresa")

    from datetime import datetime

    from .excel_export import ExcelExportService

    # Obtener parámetros de fecha
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

    # Generar Excel completo
    try:
        service = ExcelExportService(empresa, fecha_inicio, fecha_fin)
        excel_content = service.generar_excel_completo()

        # Crear respuesta
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Reporte_Completo_{empresa.nombre.replace(' ', '_')}_{timestamp}.xlsx"

        response = HttpResponse(
            excel_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        messages.error(
            request, f"Error al generar el reporte Excel: {str(e)}. Por favor, intente nuevamente."
        )
        return redirect("contabilidad:company_detail", empresa_id=empresa.id)


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

    # Verificar permisos: owner, superuser, or supervisor with visible flag
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
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

    # Verificar permisos
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
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

    # Verificar permisos
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
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

    # Verificar permisos
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
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

    # Verificar permisos
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
        return HttpResponseForbidden("No tienes permiso para ver esta empresa.")

    # Generar sugerencias inteligentes basadas en las cuentas más utilizadas

    from django.db.models import Count

    sugerencias = []

    # Obtener cuentas más utilizadas por tipo (para tener variedad)
    tipo_emoji_map = {
        "ACTIVO": "💰",
        "PASIVO": "🏦",
        "PATRIMONIO": "📊",
        "INGRESO": "📈",
        "GASTO": "📉",
    }

    # Palabras a eliminar (stop words contables comunes)
    stop_words = {"de", "del", "la", "el", "los", "las", "por", "para", "en", "y", "a"}

    def limpiar_descripcion(desc: str) -> str:
        """Extrae palabras clave significativas de la descripción."""
        palabras = desc.lower().split()
        # Filtrar stop words y mantener solo palabras significativas
        palabras_clave = [
            p.capitalize() for p in palabras if p.lower() not in stop_words and len(p) > 2
        ]
        # Limitar a 3 palabras y máximo 30 caracteres
        texto = " ".join(palabras_clave[:3])
        if len(texto) > 30:
            texto = texto[:27] + "..."
        return texto

    # Obtener 2 cuentas más usadas de cada tipo
    for tipo, emoji in tipo_emoji_map.items():
        cuentas = (
            EmpresaPlanCuenta.objects.filter(empresa=empresa, activa=True, tipo=tipo)
            .annotate(num_transacciones=Count("empresatransaccion"))
            .filter(num_transacciones__gt=0)
            .order_by("-num_transacciones")[:2]
        )

        for cuenta in cuentas:
            texto_sugerencia = limpiar_descripcion(cuenta.descripcion)
            if texto_sugerencia:  # Solo agregar si hay texto válido
                sugerencias.append(
                    {
                        "texto": texto_sugerencia,
                        "texto_completo": cuenta.descripcion,
                        "emoji": emoji,
                        "tipo": tipo.lower(),
                        "codigo": cuenta.codigo,
                    }
                )

    # Si no hay suficientes sugerencias (menos de 4), agregar cuentas auxiliares populares
    if len(sugerencias) < 4:
        codigos_usados = [s["codigo"] for s in sugerencias]
        cuentas_adicionales = (
            EmpresaPlanCuenta.objects.filter(empresa=empresa, activa=True, es_auxiliar=True)
            .exclude(codigo__in=codigos_usados)
            .order_by("codigo")[:6]
        )

        for cuenta in cuentas_adicionales:
            if len(sugerencias) >= 10:
                break
            emoji = tipo_emoji_map.get(cuenta.tipo, "📋")
            texto_sugerencia = limpiar_descripcion(cuenta.descripcion)
            if texto_sugerencia:
                sugerencias.append(
                    {
                        "texto": texto_sugerencia,
                        "texto_completo": cuenta.descripcion,
                        "emoji": emoji,
                        "tipo": cuenta.tipo.lower(),
                        "codigo": cuenta.codigo,
                    }
                )

    # Limitar a 8 sugerencias máximo
    sugerencias = sugerencias[:8]

    context = {
        "empresa": empresa,
        "seccion_activa": "ml_embeddings",
        "titulo_pagina": "Búsqueda Semántica",
        "sugerencias": sugerencias,
    }
    return render(request, "contabilidad/ml_embeddings.html", context)


@login_required
def ml_health_score(request, empresa_id):
    """Vista de health score financiero avanzado (FASE 4)."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    # Verificar permisos
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
        return HttpResponseForbidden("No tienes permiso para ver esta empresa.")

    context = {
        "empresa": empresa,
        "seccion_activa": "ml_health_score",
        "titulo_pagina": "Salud Financiera",
    }
    return render(request, "contabilidad/ml_health_score.html", context)


# ==================== ML/AI API ENDPOINTS ====================


@login_required
@require_http_methods(["GET"])
def ml_api_dashboard_metrics(request, empresa_id):
    """API: Obtener métricas del dashboard ML."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    # Verificar permisos
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
        return JsonResponse({"error": "No tienes permiso"}, status=403)

    try:
        ml_service = MLAnalyticsService(empresa)
        metrics = ml_service.get_dashboard_metrics()
        return JsonResponse(metrics)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def ml_api_analytics(request, empresa_id):
    """API: Obtener datos de analytics con series de tiempo."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    # Verificar permisos
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
        return JsonResponse({"error": "No tienes permiso"}, status=403)

    try:
        meses = int(request.GET.get("meses", 12))
        ml_service = MLAnalyticsService(empresa)
        data = ml_service.get_analytics_time_series(meses)
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def ml_api_predictions(request, empresa_id):
    """API: Generar predicciones financieras."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    # Verificar permisos
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
        return JsonResponse({"error": "No tienes permiso"}, status=403)

    try:
        body = json.loads(request.body)
        tipo = body.get("tipo", "ingresos")
        periodos = int(body.get("periodos", 6))

        # Mapear valores del frontend a tipos de cuenta
        tipo_map = {
            "ingresos": "INGRESO",
            "gastos": "GASTO",
            "flujo": "FLUJO",  # Para flujo, combinaremos ingresos - gastos
        }

        tipo_cuenta = tipo_map.get(tipo, "INGRESO")

        ml_service = MLAnalyticsService(empresa)
        predictions = ml_service.generate_predictions(tipo_cuenta, periodos)
        return JsonResponse(predictions)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def ml_api_anomalies(request, empresa_id):
    """API: Detectar anomalías en transacciones."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    # Verificar permisos
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
        return JsonResponse({"error": "No tienes permiso"}, status=403)

    try:
        meses = int(request.GET.get("meses", 12))
        umbral = float(request.GET.get("umbral", 2.0))

        ml_service = MLAnalyticsService(empresa)
        anomalies = ml_service.detect_anomalies(meses, umbral)

        return JsonResponse(
            {
                "anomalies": anomalies,
                "total": len(anomalies),
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def ml_api_embeddings(request, empresa_id):
    """API: Búsqueda semántica de cuentas."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    # Verificar permisos
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (
        request.user == empresa.owner
        or request.user.is_superuser
        or (is_supervisor and empresa.visible_to_supervisor)
    ):
        return JsonResponse({"error": "No tienes permiso"}, status=403)

    try:
        body = json.loads(request.body)
        query = body.get("query", "")
        limit = int(body.get("limit", 10))

        if not query:
            return JsonResponse({"error": "Query es requerido"}, status=400)

        ml_service = MLAnalyticsService(empresa)
        results = ml_service.semantic_search(query, limit)

        return JsonResponse(
            {
                "results": results,
                "total": len(results),
                "query": query,
            }
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# -------------------------
# Vistas de Control de Inventarios (Kardex)
# -------------------------


@login_required
def kardex_lista_productos(request, empresa_id):
    """Lista de productos con control de inventario (Kardex) y análisis inteligente."""
    from datetime import datetime, timedelta

    from django.db.models import Sum

    empresa = get_object_or_404(Empresa, id=empresa_id)

    # Verificar permisos
    if empresa.owner != request.user:
        supervisor_access = EmpresaSupervisor.objects.filter(
            empresa=empresa, docente=request.user
        ).exists()
        if not (supervisor_access and empresa.visible_to_supervisor):
            return HttpResponseForbidden("No tienes permisos para ver esta empresa.")

    from .models import ProductoInventario

    # Obtener todos los productos de la empresa
    productos = (
        ProductoInventario.objects.filter(empresa=empresa)
        .select_related("cuenta_inventario", "cuenta_costo_venta")
        .prefetch_related("movimientos")
        .order_by("sku")
    )

    # Fecha de hace 30 días para análisis de rotación
    hace_30_dias = datetime.now().date() - timedelta(days=30)

    # Enriquecer con datos calculados y análisis
    productos_data = []
    total_productos_activos = 0
    total_con_stock_bajo = 0
    valor_total_inventario = 0
    productos_criticos = []
    productos_sin_movimiento = []
    productos_alta_rotacion = []

    for producto in productos:
        stock_actual = producto.stock_actual
        costo_promedio = producto.costo_promedio_actual
        valor_total = producto.valor_inventario_actual
        requiere_reabastecimiento = producto.requiere_reabastecimiento

        # Analizar movimientos recientes (últimos 30 días)
        movimientos_recientes = producto.movimientos.filter(fecha__gte=hace_30_dias)
        num_movimientos = movimientos_recientes.count()

        # Calcular salidas (ventas) en los últimos 30 días
        salidas_recientes = (
            movimientos_recientes.filter(
                tipo_movimiento__in=[
                    TipoMovimientoKardex.SALIDA,
                    TipoMovimientoKardex.DEVOLUCION_COMPRA,
                    TipoMovimientoKardex.AJUSTE_SALIDA,
                ]
            ).aggregate(total=Sum("cantidad"))["total"]
            or 0
        )

        # Clasificar productos
        if requiere_reabastecimiento and producto.activo:
            productos_criticos.append(
                {
                    "producto": producto,
                    "stock": stock_actual,
                    "minimo": producto.stock_minimo,
                    "deficit": producto.stock_minimo - stock_actual,
                }
            )

        # Productos sin movimiento en 30 días
        if num_movimientos == 0 and producto.activo and stock_actual > 0:
            productos_sin_movimiento.append(
                {"producto": producto, "dias_inactivo": 30, "valor_inmovilizado": valor_total}
            )

        # Productos de alta rotación (más del 50% del stock vendido en 30 días)
        if salidas_recientes > 0 and stock_actual > 0:
            ratio_rotacion = float(salidas_recientes / stock_actual) if stock_actual > 0 else 0
            if ratio_rotacion > 0.5:
                productos_alta_rotacion.append(
                    {
                        "producto": producto,
                        "rotacion": ratio_rotacion * 100,
                        "salidas": salidas_recientes,
                    }
                )

        item = {
            "producto": producto,
            "stock_actual": stock_actual,
            "costo_promedio": costo_promedio,
            "valor_total": valor_total,
            "requiere_reabastecimiento": requiere_reabastecimiento,
            "num_movimientos_30d": num_movimientos,
            "salidas_30dias": salidas_recientes,
        }
        productos_data.append(item)

        # Calcular estadísticas
        if producto.activo:
            total_productos_activos += 1
        if requiere_reabastecimiento:
            total_con_stock_bajo += 1
        valor_total_inventario += valor_total

    can_edit = (request.user == empresa.owner) or request.user.is_superuser

    # Categorías más valiosas
    from collections import defaultdict

    categorias_stats = defaultdict(lambda: {"cantidad": 0, "valor": 0})
    for item in productos_data:
        cat = item["producto"].categoria or "Sin categoría"
        categorias_stats[cat]["cantidad"] += 1
        categorias_stats[cat]["valor"] += float(item["valor_total"])

    categorias_top = sorted(categorias_stats.items(), key=lambda x: x[1]["valor"], reverse=True)[:5]

    # Recomendaciones inteligentes
    recomendaciones = []

    if productos_criticos:
        recomendaciones.append(
            {
                "tipo": "urgente",
                "icono": "🚨",
                "titulo": f"{len(productos_criticos)} producto(s) crítico(s)",
                "mensaje": "Requieren reabastecimiento inmediato",
                "detalle": ", ".join([p["producto"].sku for p in productos_criticos[:3]]),
                "color": "red",
            }
        )

    if productos_sin_movimiento:
        valor_inmovilizado = sum(p["valor_inmovilizado"] for p in productos_sin_movimiento)
        recomendaciones.append(
            {
                "tipo": "advertencia",
                "icono": "⚠️",
                "titulo": f"{len(productos_sin_movimiento)} producto(s) sin movimiento",
                "mensaje": f"${valor_inmovilizado:,.2f} en inventario inmovilizado (30 días)",
                "detalle": "Considerar liquidación o promoción",
                "color": "yellow",
            }
        )

    if productos_alta_rotacion:
        recomendaciones.append(
            {
                "tipo": "exito",
                "icono": "📈",
                "titulo": f"{len(productos_alta_rotacion)} producto(s) de alta rotación",
                "mensaje": "Productos estrella con alta demanda",
                "detalle": "Considerar aumentar stock de seguridad",
                "color": "green",
            }
        )

    # Detectar tipo de empresa por descripción/nombre para sugerencias
    nombre_lower = empresa.nombre.lower() + " " + (empresa.descripcion or "").lower()
    tipo_empresa_detectado = None
    sugerencias_productos = []

    if any(
        word in nombre_lower
        for word in ["restaurant", "comida", "cafetería", "bar", "cocina", "gastro"]
    ):
        tipo_empresa_detectado = "Restaurante/Gastronomía"
        sugerencias_productos = ["Ingredientes perecederos", "Bebidas", "Utensilios", "Suministros"]
    elif any(
        word in nombre_lower
        for word in ["retail", "tienda", "comercio", "venta", "boutique", "almacén"]
    ):
        tipo_empresa_detectado = "Retail/Comercio"
        sugerencias_productos = [
            "Productos de temporada",
            "Artículos promocionales",
            "Merchandising",
        ]
    elif any(
        word in nombre_lower for word in ["manufactur", "fabric", "producc", "industrial", "planta"]
    ):
        tipo_empresa_detectado = "Manufactura/Industrial"
        sugerencias_productos = [
            "Materias primas",
            "Producto en proceso",
            "Producto terminado",
            "Insumos",
        ]
    elif any(
        word in nombre_lower for word in ["farmacia", "droguería", "salud", "medical", "clínica"]
    ):
        tipo_empresa_detectado = "Farmacia/Salud"
        sugerencias_productos = [
            "Medicamentos",
            "Productos de cuidado",
            "Equipos médicos",
            "Suplementos",
        ]
    elif any(
        word in nombre_lower
        for word in ["tecnología", "software", "electrónica", "informática", "tech"]
    ):
        tipo_empresa_detectado = "Tecnología/Electrónica"
        sugerencias_productos = ["Hardware", "Software", "Accesorios", "Componentes"]

    # Determinar si es docente y supervisor
    try:
        is_docente = (
            hasattr(request.user, "userprofile") and request.user.userprofile.rol == "DOCENTE"
        )
    except:
        is_docente = False

    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()

    # Comentarios de Kardex (solo si la empresa es visible)
    comments_kardex = []
    if empresa.visible_to_supervisor:
        comments_kardex = empresa.comments.filter(section="KD")

    context = {
        "empresa": empresa,
        "productos_data": productos_data,
        "total_productos_activos": total_productos_activos,
        "total_con_stock_bajo": total_con_stock_bajo,
        "valor_total_inventario": valor_total_inventario,
        "can_edit": can_edit,
        "is_supervisor": is_supervisor,
        "is_docente": is_docente,
        "active_section": "kardex",
        # Análisis inteligente
        "productos_criticos": productos_criticos,
        "productos_sin_movimiento": productos_sin_movimiento,
        "productos_alta_rotacion": productos_alta_rotacion,
        "recomendaciones": recomendaciones,
        "categorias_top": categorias_top,
        "tipo_empresa_detectado": tipo_empresa_detectado,
        "sugerencias_productos": sugerencias_productos,
        # Sistema de comentarios
        "comments_kardex": comments_kardex,
        "section_code": "KD",
    }

    return render(request, "contabilidad/kardex_lista_productos.html", context)


@login_required
def kardex_producto_detalle(request, empresa_id, producto_id):
    """Vista del Kardex (tarjeta de movimientos) de un producto específico."""
    empresa = get_object_or_404(Empresa, id=empresa_id)

    # Verificar permisos
    if empresa.owner != request.user:
        supervisor_access = EmpresaSupervisor.objects.filter(
            empresa=empresa, docente=request.user
        ).exists()
        if not (supervisor_access and empresa.visible_to_supervisor):
            return HttpResponseForbidden("No tienes permisos para ver esta empresa.")

    from .kardex_service import KardexService
    from .models import ProductoInventario

    producto = get_object_or_404(ProductoInventario, id=producto_id, empresa=empresa)

    # Filtros de fecha
    from datetime import datetime

    fecha_inicio_str = request.GET.get("fecha_inicio")
    fecha_fin_str = request.GET.get("fecha_fin")

    fecha_inicio = None
    fecha_fin = None

    if fecha_inicio_str:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        except ValueError:
            messages.warning(request, "Fecha de inicio inválida.")

    if fecha_fin_str:
        try:
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except ValueError:
            messages.warning(request, "Fecha de fin inválida.")

    # Obtener reporte Kardex
    kardex_raw = KardexService.obtener_kardex_producto(producto, fecha_inicio, fecha_fin)

    # Formatear datos para template
    kardex_data = {
        "movimientos": kardex_raw["movimientos"],
        "saldo_inicial": {
            "cantidad": kardex_raw["saldo_inicial"],
            "costo_promedio": kardex_raw["valor_inicial"] / kardex_raw["saldo_inicial"]
            if kardex_raw["saldo_inicial"] > 0
            else 0,
            "valor_total": kardex_raw["valor_inicial"],
        },
        "saldo_final": {
            "cantidad": kardex_raw["saldo_final"],
            "costo_promedio": kardex_raw["valor_final"] / kardex_raw["saldo_final"]
            if kardex_raw["saldo_final"] > 0
            else 0,
            "valor_total": kardex_raw["valor_final"],
        },
        "total_entradas": kardex_raw["total_entradas"],
        "total_salidas": kardex_raw["total_salidas"],
    }

    can_edit = (request.user == empresa.owner) or request.user.is_superuser

    try:
        is_docente = (
            hasattr(request.user, "userprofile") and request.user.userprofile.rol == "DOCENTE"
        )
    except:
        is_docente = False

    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()

    context = {
        "empresa": empresa,
        "producto": producto,
        "kardex_data": kardex_data,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "can_edit": can_edit,
        "is_supervisor": is_supervisor,
        "is_docente": is_docente,
        "active_section": "kardex",
    }

    return render(request, "contabilidad/kardex_producto_detalle.html", context)


@login_required
def kardex_crear_producto(request, empresa_id):
    """Vista para crear un nuevo producto de inventario."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    # Verificar permisos
    can_edit = (
        request.user == empresa.owner
        or EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    )

    if not can_edit:
        messages.error(request, "No tienes permisos para crear productos en esta empresa.")
        return redirect("contabilidad:kardex_lista_productos", empresa_id=empresa_id)

    if request.method == "POST":
        form = ProductoInventarioForm(request.POST, empresa=empresa)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.empresa = empresa
            producto.save()
            messages.success(
                request, f"✅ Producto '{producto.sku} - {producto.nombre}' creado exitosamente."
            )
            return redirect("contabilidad:kardex_lista_productos", empresa_id=empresa_id)
    else:
        form = ProductoInventarioForm(empresa=empresa)

    try:
        is_docente = (
            hasattr(request.user, "userprofile") and request.user.userprofile.rol == "DOCENTE"
        )
    except:
        is_docente = False

    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()

    context = {
        "empresa": empresa,
        "form": form,
        "can_edit": can_edit,
        "is_supervisor": is_supervisor,
        "is_docente": is_docente,
        "active_section": "kardex",
    }

    return render(request, "contabilidad/kardex_producto_form.html", context)


@login_required
def kardex_registrar_movimiento(request, empresa_id, producto_id):
    """Vista para registrar un movimiento de inventario (entrada/salida)."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    producto = get_object_or_404(ProductoInventario, pk=producto_id, empresa=empresa)

    # Verificar permisos
    can_edit = (
        request.user == empresa.owner
        or EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    )

    if not can_edit:
        messages.error(request, "No tienes permisos para registrar movimientos en esta empresa.")
        return redirect(
            "contabilidad:kardex_producto_detalle", empresa_id=empresa_id, producto_id=producto_id
        )

    if request.method == "POST":
        form = MovimientoKardexForm(request.POST, producto=producto)
        if form.is_valid():
            try:
                # Extraer datos del formulario
                tipo_movimiento = form.cleaned_data["tipo_movimiento"]
                fecha = form.cleaned_data["fecha"]
                cantidad = form.cleaned_data["cantidad"]
                costo_unitario = form.cleaned_data.get("costo_unitario")
                documento_referencia = form.cleaned_data.get("documento_referencia", "")
                tercero = form.cleaned_data.get("tercero")
                observaciones = form.cleaned_data.get("observaciones", "")

                # Determinar si es entrada o salida
                entradas = [
                    TipoMovimientoKardex.COMPRA,
                    TipoMovimientoKardex.DEVOLUCION_VENTA,
                    TipoMovimientoKardex.AJUSTE_ENTRADA,
                ]
                salidas = [
                    TipoMovimientoKardex.VENTA,
                    TipoMovimientoKardex.DEVOLUCION_COMPRA,
                    TipoMovimientoKardex.AJUSTE_SALIDA,
                ]

                # Usar KardexService para registrar el movimiento
                if tipo_movimiento in entradas:
                    movimiento = KardexService.registrar_entrada(
                        producto=producto,
                        tipo_movimiento=tipo_movimiento,
                        cantidad=cantidad,
                        costo_unitario=costo_unitario,
                        fecha=fecha,
                        documento_referencia=documento_referencia,
                        tercero=tercero,
                        observaciones=observaciones,
                        usuario=request.user,
                    )
                    messages.success(
                        request,
                        f"✅ Entrada registrada: {cantidad} {producto.unidad_medida} "
                        f"@ ${costo_unitario:,.2f}. Nuevo stock: {producto.stock_actual}",
                    )
                elif tipo_movimiento in salidas:
                    movimiento = KardexService.registrar_salida(
                        producto=producto,
                        tipo_movimiento=tipo_movimiento,
                        cantidad=cantidad,
                        fecha=fecha,
                        documento_referencia=documento_referencia,
                        tercero=tercero,
                        observaciones=observaciones,
                        usuario=request.user,
                    )
                    messages.success(
                        request,
                        f"✅ Salida registrada: {cantidad} {producto.unidad_medida}. "
                        f"Nuevo stock: {producto.stock_actual}",
                    )
                else:
                    raise ValueError(f"Tipo de movimiento no reconocido: {tipo_movimiento}")

                # Redirigir al detalle del producto (Kardex)
                return redirect(
                    "contabilidad:kardex_producto_detalle",
                    empresa_id=empresa_id,
                    producto_id=producto_id,
                )

            except ValueError as e:
                messages.error(request, f"❌ Error al registrar el movimiento: {str(e)}")
            except Exception as e:
                messages.error(request, f"❌ Error inesperado: {str(e)}")
    else:
        # Prellenar la fecha con hoy
        from datetime import date

        form = MovimientoKardexForm(initial={"fecha": date.today()}, producto=producto)

    try:
        is_docente = (
            hasattr(request.user, "userprofile") and request.user.userprofile.rol == "DOCENTE"
        )
    except:
        is_docente = False

    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()

    context = {
        "empresa": empresa,
        "producto": producto,
        "form": form,
        "can_edit": can_edit,
        "is_supervisor": is_supervisor,
        "is_docente": is_docente,
        "active_section": "kardex",
    }

    return render(request, "contabilidad/kardex_movimiento_form.html", context)
