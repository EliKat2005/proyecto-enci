from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Empresa, EmpresaPlanCuenta, EmpresaSupervisor
from core.models import UserProfile
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods


@login_required
def my_companies(request):
    """Lista las empresas del usuario actual."""
    # Esta ruta ahora redirige al home centralizado donde se muestra la lista de empresas.
    return redirect('home')


@login_required
def create_company(request):
    # Determinar si el usuario es docente para mostrar la opción de plantilla
    is_docente = False
    try:
        is_docente = (hasattr(request.user, 'userprofile') and request.user.userprofile.rol == UserProfile.Roles.DOCENTE)
    except Exception:
        is_docente = False

    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        # Solo permitir marcar como plantilla si es docente o superuser
        requested_template = request.POST.get('is_template') == '1'
        is_template = requested_template and (is_docente or request.user.is_superuser)
        if not nombre:
            messages.error(request, 'El nombre es obligatorio.')
            return redirect('contabilidad:create_company')
        # Las empresas creadas por estudiantes no son visibles por defecto para sus docentes
        visible_default = True if (is_docente or request.user.is_superuser) else False
        emp = Empresa.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            owner=request.user,
            is_template=is_template,
            visible_to_supervisor=visible_default,
        )
        messages.success(request, f'Empresa "{emp.nombre}" creada.')
        return redirect('home')
    return render(request, 'contabilidad/create_company.html', {'is_docente': is_docente})


@login_required
def generate_join_code(request, empresa_id):
    emp = get_object_or_404(Empresa, pk=empresa_id)
    # Solo docentes (propio docente) o superuser pueden generar join codes.
    is_docente = False
    try:
        is_docente = (hasattr(request.user, 'userprofile') and request.user.userprofile.rol == UserProfile.Roles.DOCENTE)
    except Exception:
        is_docente = False

    if not (request.user.is_superuser or (is_docente and emp.owner == request.user)):
        return HttpResponseForbidden('No autorizado')
    code = emp.generate_join_code()
    messages.success(request, f'Join code generado: {code}')
    return redirect('home')


@login_required
def import_company(request):
    """Endpoint para que un estudiante importe una empresa por join_code (POST).

    Si la plantilla es encontrada, se crea una copia para el usuario y se registra
    una relación `EmpresaSupervisor` entre la nueva empresa y el docente propietario.
    """
    if request.method != 'POST':
        return HttpResponseForbidden('Invalid')
    join_code = request.POST.get('join_code', '').strip()
    if not join_code:
        messages.error(request, 'Código requerido.')
        return redirect('contabilidad:my_companies')
    try:
        new_emp = Empresa.import_from_template(join_code, request.user)
        # Registrar relación de supervisión con el docente original si existe
        if new_emp.original and new_emp.original.owner:
            try:
                EmpresaSupervisor.objects.get_or_create(empresa=new_emp, docente=new_emp.original.owner)
            except Exception:
                pass

        messages.success(request, f'Empresa importada: {new_emp.nombre}')
        return redirect('home')
    except Empresa.DoesNotExist:
        messages.error(request, 'Código inválido o plantilla no encontrada.')
        return redirect('contabilidad:my_companies')


@login_required
def supervised_companies(request):
    """Lista las empresas que el docente supervisa (o admin puede ver todas)."""
    # Permitir acceso sólo a docentes o superusers
    is_docente = False
    try:
        is_docente = (hasattr(request.user, 'userprofile') and request.user.userprofile.rol == UserProfile.Roles.DOCENTE)
    except Exception:
        is_docente = False

    if not (is_docente or request.user.is_superuser):
        return HttpResponseForbidden('No autorizado')

    if request.user.is_superuser:
        # Admin: ver todas las supervisiones agrupadas por docente (solo empresas visibles)
        supervisiones = EmpresaSupervisor.objects.select_related('empresa', 'docente').filter(empresa__visible_to_supervisor=True).order_by('-created_at')
    else:
        supervisiones = EmpresaSupervisor.objects.filter(docente=request.user, empresa__visible_to_supervisor=True).select_related('empresa').order_by('-created_at')

    contexto = {
        'supervisiones': supervisiones,
        'is_docente': is_docente,
        'is_admin': request.user.is_superuser,
    }

    return render(request, 'contabilidad/supervised_companies.html', contexto)



@login_required
def company_detail(request, empresa_id):
    """Mostrar paneles de la empresa: Plan de cuentas, Libro Diario, Libro Mayor, etc.

    Permisos: propietario (owner), supervisores (docente) o superuser.
    """
    empresa = get_object_or_404(Empresa, pk=empresa_id)

    # Check permission: owner, superuser, or supervisor
    if not (request.user == empresa.owner or request.user.is_superuser or EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()):
        return HttpResponseForbidden('No autorizado para ver esta empresa')

    # Determinar si el usuario puede editar (solo owner)
    can_edit = (request.user == empresa.owner) or request.user.is_superuser

    # Determinar si el usuario es docente (para mostrar acciones específicas)
    is_docente = False
    try:
        is_docente = (hasattr(request.user, 'userprofile') and request.user.userprofile.rol == UserProfile.Roles.DOCENTE)
    except Exception:
        is_docente = False

    return render(request, 'contabilidad/company_detail.html', {'empresa': empresa, 'can_edit': can_edit, 'is_docente': is_docente})


@login_required
def delete_company(request, empresa_id):
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    # Solo el owner o superuser puede eliminar
    if not (request.user == empresa.owner or request.user.is_superuser):
        return HttpResponseForbidden('No autorizado para eliminar esta empresa')

    if request.method == 'POST':
        nombre = empresa.nombre
        empresa.delete()
        messages.success(request, f'Empresa "{nombre}" eliminada.')
        return redirect('home')

    return render(request, 'contabilidad/delete_company_confirm.html', {'empresa': empresa})


@login_required
@require_POST
def toggle_visibility(request, empresa_id):
    """Permite al owner activar/desactivar la visibilidad de su empresa para el docente supervisor."""
    emp = get_object_or_404(Empresa, pk=empresa_id)
    if emp.owner != request.user:
        return HttpResponseForbidden('No autorizado')

    # toggle
    emp.visible_to_supervisor = not bool(emp.visible_to_supervisor)
    emp.save(update_fields=['visible_to_supervisor'])

    status = 'habilitada' if emp.visible_to_supervisor else 'deshabilitada'
    messages.success(request, f'Visibilidad para supervisores {status} para "{emp.nombre}".')
    return redirect('home')


@login_required
@require_POST
def toggle_visibility_api(request, empresa_id):
    """AJAX endpoint: toggle visibility and return JSON response.

    Permission checks mirror `toggle_visibility`. Returns 403 if not allowed,
    otherwise returns the new visibility state.
    """
    emp = get_object_or_404(Empresa, pk=empresa_id)
    if emp.owner != request.user:
        return JsonResponse({'error': 'forbidden'}, status=403)

    emp.visible_to_supervisor = not bool(emp.visible_to_supervisor)
    emp.save(update_fields=['visible_to_supervisor'])

    return JsonResponse({
        'empresa_id': emp.id,
        'visible': bool(emp.visible_to_supervisor),
        'message': 'Visibilidad actualizada.'
    })


@login_required
def company_plan(request, empresa_id):
    """Mostrar Plan de Cuentas de la empresa (lectura). Supervisores pueden ver si la empresa es visible."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    # Permisos: owner, superuser, or supervisor with visible flag
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (request.user == empresa.owner or request.user.is_superuser or (is_supervisor and empresa.visible_to_supervisor)):
        return HttpResponseForbidden('No autorizado')

    cuentas = EmpresaPlanCuenta.objects.filter(empresa=empresa).order_by('codigo')
    comments = empresa.comments.filter(section='PL').order_by('-created_at')
    can_edit = (request.user == empresa.owner) or request.user.is_superuser
    return render(request, 'contabilidad/company_plan.html', {'empresa': empresa, 'cuentas': cuentas, 'comments': comments, 'is_supervisor': is_supervisor, 'can_edit': can_edit})


@login_required
@require_POST
def add_account(request, empresa_id):
    """Crear una cuenta dentro del Plan de Cuentas de la empresa.

    Solo el owner de la empresa o superuser puede crear cuentas.
    Campos esperados: codigo, descripcion, tipo, naturaleza, estado_situacion (on), es_auxiliar (on), padre_id (opcional).
    """
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    if not ((request.user == empresa.owner) or request.user.is_superuser):
        return HttpResponseForbidden('No autorizado')

    codigo = request.POST.get('codigo', '').strip()
    descripcion = request.POST.get('descripcion', '').strip()
    tipo = request.POST.get('tipo')
    naturaleza = request.POST.get('naturaleza')
    estado_situacion = request.POST.get('estado_situacion') == '1'
    es_auxiliar = request.POST.get('es_auxiliar') == '1'
    padre_id = request.POST.get('padre') or None

    if not codigo or not descripcion:
        messages.error(request, 'Código y descripción son obligatorios.')
        return redirect('contabilidad:company_plan', empresa_id=empresa.id)

    # Validar unicidad del código dentro de la empresa
    if EmpresaPlanCuenta.objects.filter(empresa=empresa, codigo=codigo).exists():
        messages.error(request, f'Ya existe una cuenta con el código {codigo} en esta empresa.')
        return redirect('contabilidad:company_plan', empresa_id=empresa.id)

    # Validar que 'tipo' y 'naturaleza' sean valores permitidos
    valid_tipos = [t[0] for t in EmpresaPlanCuenta._meta.get_field('tipo').choices]
    valid_naturalezas = [n[0] for n in EmpresaPlanCuenta._meta.get_field('naturaleza').choices]
    if tipo and tipo not in valid_tipos:
        messages.error(request, 'Tipo de cuenta inválido.')
        return redirect('contabilidad:company_plan', empresa_id=empresa.id)
    if naturaleza and naturaleza not in valid_naturalezas:
        messages.error(request, 'Naturaleza de cuenta inválida.')
        return redirect('contabilidad:company_plan', empresa_id=empresa.id)

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
            tipo=tipo or EmpresaPlanCuenta._meta.get_field('tipo').choices[0][0],
            naturaleza=naturaleza or EmpresaPlanCuenta._meta.get_field('naturaleza').choices[0][0],
            estado_situacion=bool(estado_situacion),
            es_auxiliar=bool(es_auxiliar),
            padre=padre
        )
        messages.success(request, f'Cuenta {codigo} creada correctamente.')
    except Exception as e:
        messages.error(request, f'Error al crear la cuenta: {e}')

    return redirect('contabilidad:company_plan', empresa_id=empresa.id)


@login_required
def company_diario(request, empresa_id):
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (request.user == empresa.owner or request.user.is_superuser or (is_supervisor and empresa.visible_to_supervisor)):
        return HttpResponseForbidden('No autorizado')

    asientos = EmpresaAsiento.objects.filter(empresa=empresa).order_by('-fecha')
    comments = empresa.comments.filter(section='DI').order_by('-created_at')
    return render(request, 'contabilidad/company_diario.html', {'empresa': empresa, 'asientos': asientos, 'comments': comments, 'is_supervisor': is_supervisor})


@login_required
@require_POST
def add_comment(request, empresa_id, section):
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    # Solo docentes supervisores o superuser pueden comentar
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (request.user.is_superuser or is_supervisor):
        return HttpResponseForbidden('No autorizado')

    content = request.POST.get('content', '').strip()
    if not content:
        messages.error(request, 'El comentario no puede estar vacío.')
        return redirect(request.META.get('HTTP_REFERER', 'contabilidad:company_detail'))

    if section not in dict((k, v) for k, v in EmpresaComment.SECTION_CHOICES):
        messages.error(request, 'Sección inválida.')
        return redirect(request.META.get('HTTP_REFERER', 'contabilidad:company_detail'))

    EmpresaComment.objects.create(empresa=empresa, section=section, author=request.user, content=content)
    messages.success(request, 'Comentario agregado.')
    # Redirect back to the referring page
    return redirect(request.META.get('HTTP_REFERER', 'contabilidad:company_detail'))
