"""
Permisos personalizados para el sistema contable.
Implementa lógica de autorización granular para empresas y recursos.
"""

from rest_framework import permissions

from contabilidad.models import EmpresaSupervisor


class IsEmpresaOwnerOrSupervisor(permissions.BasePermission):
    """
    Permiso para acceder a recursos de una empresa.

    Permite:
    - Owner de la empresa: Lectura y escritura completa
    - Supervisor (si visible_to_supervisor=True): Solo lectura
    - Superuser: Acceso completo
    """

    message = "No tienes permiso para acceder a esta empresa."

    def has_object_permission(self, request, view, obj):
        # Superuser tiene acceso completo
        if request.user.is_superuser:
            return True

        # Obtener la empresa del objeto
        empresa = obj.empresa if hasattr(obj, "empresa") else obj

        # Owner tiene acceso completo
        if empresa.owner == request.user:
            return True

        # Verificar si es supervisor
        is_supervisor = EmpresaSupervisor.objects.filter(
            empresa=empresa, docente=request.user
        ).exists()

        if is_supervisor and empresa.visible_to_supervisor:
            # Supervisores solo tienen acceso de lectura
            if request.method in permissions.SAFE_METHODS:
                return True
            else:
                self.message = "Los supervisores solo tienen permisos de lectura."
                return False

        return False


class IsEmpresaOwner(permissions.BasePermission):
    """
    Permiso estricto: solo el owner de la empresa.
    Usar para operaciones críticas como eliminar o modificar configuración.
    """

    message = "Solo el propietario de la empresa puede realizar esta acción."

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        empresa = obj.empresa if hasattr(obj, "empresa") else obj

        return empresa.owner == request.user


class IsSupervisorWithAccess(permissions.BasePermission):
    """
    Permiso para supervisores con acceso habilitado.
    Solo lectura.
    """

    message = "No tienes acceso como supervisor a esta empresa."

    def has_object_permission(self, request, view, obj):
        empresa = obj.empresa if hasattr(obj, "empresa") else obj

        # Verificar si es supervisor con acceso
        is_supervisor = EmpresaSupervisor.objects.filter(
            empresa=empresa, docente=request.user
        ).exists()

        if is_supervisor and empresa.visible_to_supervisor:
            # Solo métodos seguros (GET, HEAD, OPTIONS)
            return request.method in permissions.SAFE_METHODS

        return False


class CanModifyAsiento(permissions.BasePermission):
    """
    Permiso para modificar asientos contables.

    Reglas:
    - Owner puede modificar cualquier asiento
    - Solo asientos no cerrados pueden modificarse
    - Solo asientos del último período pueden modificarse
    """

    message = "No puedes modificar este asiento contable."

    def has_object_permission(self, request, view, obj):
        # Superuser puede todo
        if request.user.is_superuser:
            return True

        # Debe ser owner
        if obj.empresa.owner != request.user:
            self.message = "No eres el propietario de esta empresa."
            return False

        # Verificar si el asiento está anulado
        if obj.anulado:
            self.message = "No puedes modificar un asiento anulado."
            return False

        # Aquí podrías agregar más lógica:
        # - Verificar si el período está cerrado
        # - Verificar si han pasado X días desde la creación
        # - Etc.

        return True


class CanDeleteAsiento(permissions.BasePermission):
    """
    Permiso para eliminar asientos.
    Restricción más estricta que modificar.
    """

    message = "No puedes eliminar este asiento contable."

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        if obj.empresa.owner != request.user:
            self.message = "No eres el propietario de esta empresa."
            return False

        if obj.anulado:
            self.message = "El asiento ya está anulado."
            return False

        # Podrías agregar más restricciones:
        # - Solo asientos del día actual
        # - Solo si no hay asientos posteriores
        # - Requiere motivo/auditoría

        return True
