from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.urls import reverse
from django.core.exceptions import ValidationError
from datetime import date
import json

from core.models import UserProfile, Notification
from .models import (
    Empresa, 
    EmpresaPlanCuenta, 
    EmpresaSupervisor, 
    EmpresaAsiento, 
    EmpresaTransaccion,
    EmpresaComment
)
from .services import AsientoService, LibroMayorService


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
def edit_company(request, empresa_id):
    """Permite al propietario editar el nombre y descripción de la empresa."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    # Solo el owner o superuser puede editar
    if not (request.user == empresa.owner or request.user.is_superuser):
        return HttpResponseForbidden('No autorizado para editar esta empresa')

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        
        if not nombre:
            messages.error(request, 'El nombre es obligatorio.')
            return redirect('contabilidad:edit_company', empresa_id=empresa.id)
        
        empresa.nombre = nombre
        empresa.descripcion = descripcion
        empresa.save(update_fields=['nombre', 'descripcion'])
        
        messages.success(request, f'Empresa "{empresa.nombre}" actualizada correctamente.')
        return redirect('contabilidad:company_detail', empresa_id=empresa.id)
    
    return render(request, 'contabilidad/edit_company.html', {'empresa': empresa})


@login_required
def delete_company(request, empresa_id):
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    # Solo el owner o superuser puede eliminar
    if not (request.user == empresa.owner or request.user.is_superuser):
        return HttpResponseForbidden('No autorizado para eliminar esta empresa')

    if request.method == 'POST':
        nombre = empresa.nombre
        try:
            with transaction.atomic():
                # 1) Borrar asientos y sus transacciones (CASCADE por FK "asiento")
                EmpresaAsiento.objects.filter(empresa=empresa).delete()

                # 2) Borrar cuentas del plan (asegurando borrar hojas primero para respetar FK padre PROTECT)
                cuentas = list(EmpresaPlanCuenta.objects.filter(empresa=empresa))
                # Ordenar por profundidad (más puntos primero) para eliminar de hojas -> raíz
                cuentas.sort(key=lambda c: (c.codigo or '').count('.'), reverse=True)
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
            return redirect('home')
        except ProtectedError as e:
            messages.error(
                request,
                'No se pudo eliminar la empresa porque existen registros relacionados protegidos '
                '(por ejemplo, cuentas con dependencias). Revise transacciones/cuentas e intente nuevamente.'
            )
            return redirect('contabilidad:company_detail', empresa_id=empresa.id)

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

    cuentas = EmpresaPlanCuenta.objects.filter(empresa=empresa).select_related('padre').order_by('codigo')
    comments = empresa.comments.filter(section='PL').select_related('author').order_by('-created_at')
    can_edit = (request.user == empresa.owner) or request.user.is_superuser
    
    # Determinar si el usuario es docente
    is_docente = False
    try:
        is_docente = (hasattr(request.user, 'userprofile') and request.user.userprofile.rol == UserProfile.Roles.DOCENTE)
    except:
        is_docente = False
    
    return render(request, 'contabilidad/company_plan.html', {'empresa': empresa, 'cuentas': cuentas, 'comments': comments, 'is_supervisor': is_supervisor, 'can_edit': can_edit, 'is_docente': is_docente})


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

    asientos = EmpresaAsiento.objects.filter(empresa=empresa).select_related('creado_por').prefetch_related('lineas__cuenta').order_by('-fecha')
    comments = empresa.comments.filter(section='DI').select_related('author').order_by('-created_at')
    can_edit = (request.user == empresa.owner) or request.user.is_superuser
    cuentas_aux = EmpresaPlanCuenta.objects.filter(empresa=empresa, es_auxiliar=True).order_by('codigo')
    
    # Determinar si el usuario es docente
    is_docente = False
    try:
        is_docente = (hasattr(request.user, 'userprofile') and request.user.userprofile.rol == UserProfile.Roles.DOCENTE)
    except:
        is_docente = False
    
    return render(request, 'contabilidad/company_diario.html', {
        'empresa': empresa,
        'asientos': asientos,
        'comments': comments,
        'is_supervisor': is_supervisor,
        'is_docente': is_docente,
        'can_edit': can_edit,
        'cuentas_aux': cuentas_aux,
    })


@login_required
def company_mayor(request, empresa_id):
    """Vista del Libro Mayor con filtros de cuenta y rango de fechas."""
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    is_supervisor = EmpresaSupervisor.objects.filter(empresa=empresa, docente=request.user).exists()
    if not (request.user == empresa.owner or request.user.is_superuser or (is_supervisor and empresa.visible_to_supervisor)):
        return HttpResponseForbidden('No autorizado')

    # Filtros de la solicitud
    cuenta_id = request.GET.get('cuenta_id')
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    
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
    cuentas_aux = EmpresaPlanCuenta.objects.filter(
        empresa=empresa, 
        es_auxiliar=True
    ).order_by('codigo')
    
    # Calcular saldos si hay cuenta seleccionada
    saldos_data = None
    cuenta_seleccionada = None
    if cuenta_id:
        try:
            cuenta_seleccionada = EmpresaPlanCuenta.objects.get(
                id=cuenta_id, 
                empresa=empresa
            )
            saldos_data = LibroMayorService.calcular_saldos_cuenta(
                cuenta=cuenta_seleccionada,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                incluir_borradores=False
            )
        except EmpresaPlanCuenta.DoesNotExist:
            messages.error(request, 'Cuenta no encontrada.')
    
    # Comentarios de la sección Mayor
    comments = empresa.comments.filter(section='MA').select_related('author').order_by('-created_at')
    can_edit = (request.user == empresa.owner) or request.user.is_superuser
    
    # Determinar si el usuario es docente
    is_docente = False
    try:
        is_docente = (hasattr(request.user, 'userprofile') and request.user.userprofile.rol == UserProfile.Roles.DOCENTE)
    except:
        is_docente = False
    
    return render(request, 'contabilidad/company_mayor.html', {
        'empresa': empresa,
        'cuentas_aux': cuentas_aux,
        'cuenta_seleccionada': cuenta_seleccionada,
        'saldos_data': saldos_data,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'comments': comments,
        'is_supervisor': is_supervisor,
        'is_docente': is_docente,
        'can_edit': can_edit,
    })


@login_required
@require_POST
def create_journal_entry(request, empresa_id):
    empresa = get_object_or_404(Empresa, pk=empresa_id)
    # Solo el owner o superuser puede crear asientos
    if not (request.user == empresa.owner or request.user.is_superuser):
        return HttpResponseForbidden('No autorizado')

    fecha_str = request.POST.get('fecha')
    descripcion = request.POST.get('descripcion', '').strip()
    lineas_json = request.POST.get('lineas_json', '[]')

    try:
        f = date.fromisoformat(fecha_str) if fecha_str else date.today()
    except Exception:
        messages.error(request, 'Fecha inválida.')
        return redirect('contabilidad:company_diario', empresa_id=empresa.id)

    try:
        raw = json.loads(lineas_json)
        lineas = []
        for idx, item in enumerate(raw):
            try:
                cuenta_id = int(item.get('cuenta_id'))
            except Exception:
                raise ValidationError(f'Línea {idx+1}: cuenta inválida')
            detalle = (item.get('detalle') or '').strip()
            debe = str(item.get('debe') or '0')
            haber = str(item.get('haber') or '0')
            lineas.append({
                'cuenta_id': cuenta_id,
                'detalle': detalle,
                'debe': debe,
                'haber': haber,
            })
    except ValidationError as ve:
        messages.error(request, str(ve))
        return redirect('contabilidad:company_diario', empresa_id=empresa.id)
    except Exception:
        messages.error(request, 'No se pudieron leer las líneas del asiento.')
        return redirect('contabilidad:company_diario', empresa_id=empresa.id)

    try:
        AsientoService.crear_asiento(
            empresa=empresa,
            fecha=f,
            descripcion=descripcion or 'Asiento contable',
            lineas=lineas,
            creado_por=request.user,
            auto_confirmar=True
        )
        messages.success(request, 'Asiento creado correctamente.')
    except ValidationError as e:
        # e.messages puede ser lista o string
        msg = '; '.join(e.messages) if hasattr(e, 'messages') else str(e)
        messages.error(request, msg)
    except Exception as e:
        messages.error(request, f'Error al crear el asiento: {e}')

    return redirect('contabilidad:company_diario', empresa_id=empresa.id)


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

    # Crear el comentario
    comment = EmpresaComment.objects.create(empresa=empresa, section=section, author=request.user, content=content)
    
    # Crear notificación para el dueño de la empresa (estudiante)
    section_names = {
        'PL': 'Plan de Cuentas',
        'DI': 'Libro Diario',
        'RP': 'Reportes'
    }
    
    # Solo notificar si el autor no es el dueño (evitar auto-notificaciones)
    if request.user != empresa.owner:
        # Determinar la URL según la sección
        if section == 'PL':
            url = reverse('contabilidad:company_plan', args=[empresa.id])
        elif section == 'DI':
            url = reverse('contabilidad:company_diario', args=[empresa.id])
        else:
            url = reverse('contabilidad:company_detail', args=[empresa.id])
        
        Notification.objects.create(
            recipient=empresa.owner,
            actor=request.user,
            verb='commented',
            empresa_id=empresa.id,
            comment_section=section,
            url=url,
            unread=True
        )
    
    messages.success(request, 'Comentario agregado.')
    # Redirect back to the referring page
    return redirect(request.META.get('HTTP_REFERER', 'contabilidad:company_detail'))

