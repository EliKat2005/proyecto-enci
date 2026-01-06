# Validación de Jerarquía de Cuentas

## Descripción

Este documento describe la implementación de la validación de jerarquía en el Plan de Cuentas, que asegura que **las cuentas que tienen subcuentas (hijas) no pueden ser marcadas como auxiliares**.

## Motivación

En un plan de cuentas estructurado jerárquicamente:
- Las cuentas **auxiliares** son aquellas que reciben transacciones reales (detalles de diarios)
- Las cuentas **no-auxiliares** son estructurales y sirven solo para agrupar otras cuentas
- **Regla fundamental**: Solo las hojas del árbol (cuentas sin hijas) deben ser auxiliares

Si una cuenta con hijas fuera marcada como auxiliar, violaría esta regla, causando inconsistencia en los registros contables.

## Implementación

### 1. Validación en el Modelo (`EmpresaPlanCuenta.clean()`)

En `contabilidad/models.py`, línea 259-262:

```python
# Validar jerarquía: cuentas con hijas no pueden ser auxiliares
if self.es_auxiliar and self.tiene_hijas:
    raise ValidationError({
        'es_auxiliar': 'Las cuentas que tienen subcuentas no pueden ser marcadas como auxiliares.'
    })
```

### 2. Propiedades Relacionadas

#### `tiene_hijas` (línea 267-269)
```python
@property
def tiene_hijas(self):
    """Retorna True si esta cuenta tiene subcuentas."""
    return self.hijas.exists()
```

#### `puede_recibir_transacciones` (línea 271-273)
```python
@property
def puede_recibir_transacciones(self):
    """Solo las cuentas auxiliares (hojas del árbol) activas pueden recibir transacciones."""
    return self.es_auxiliar and not self.tiene_hijas and self.activa
```

## Casos de Uso

### ✓ Operaciones Permitidas

1. **Crear cuenta auxiliar sin hijas** (como hoja final)
```python
cuenta = EmpresaPlanCuenta.objects.create(
    empresa=empresa,
    codigo='1.1.01',
    descripcion='Caja',
    es_auxiliar=True,  # ✓ Permitido (no tiene hijas)
    padre=nivel_2,
    activa=True
)
```

2. **Crear estructura jerárquica**
```python
# Nivel 1: no-auxiliar (padre)
nivel_1 = EmpresaPlanCuenta.objects.create(..., es_auxiliar=False)

# Nivel 2: no-auxiliar (padre de nivel_1)
nivel_2 = EmpresaPlanCuenta.objects.create(..., es_auxiliar=False, padre=nivel_1)

# Nivel 3: auxiliar (hoja final)
nivel_3 = EmpresaPlanCuenta.objects.create(..., es_auxiliar=True, padre=nivel_2)
```

### ✗ Operaciones Bloqueadas

1. **Intentar marcar una cuenta con hijas como auxiliar**
```python
cuenta_con_hijas = EmpresaPlanCuenta.objects.get(id=123)
cuenta_con_hijas.es_auxiliar = True
cuenta_con_hijas.save()  # ✗ Lanza ValidationError
```

**Error**:
```
ValidationError: {'es_auxiliar': 'Las cuentas que tienen subcuentas no pueden ser marcadas como auxiliares.'}
```

2. **Intentar crear una subcuenta bajo una cuenta auxiliar**
```python
# Esta operación falla porque primero se intenta modificar el padre
cuenta_auxiliar = EmpresaPlanCuenta.objects.get(es_auxiliar=True)
subcuenta = EmpresaPlanCuenta(
    codigo='x.y',
    es_auxiliar=True,
    padre=cuenta_auxiliar  # ✗ Falla si se intenta guardar
)
subcuenta.save()
```

## Flujo de Validación

```
┌─────────────────────────┐
│ Intentar guardar cuenta │
└────────────┬────────────┘
             │
             ▼
┌──────────────────────────────┐
│ EmpresaPlanCuenta.save()     │
│ → Llama a full_clean()       │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│ clean()                      │
│ (Todas las validaciones)     │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│ ¿es_auxiliar=True AND        │
│ tiene_hijas=True?            │
└────────────┬─────────────────┘
             │
    ┌────────┴────────┐
    │                 │
   SÍ                NO
    │                 │
    ▼                 ▼
✗ ValidationError   ✓ Guardado
                    exitoso
```

## Pruebas Unitarias

Se incluyen 6 pruebas en `contabilidad/tests.py::PlanCuentasHierarchyValidationTests`:

1. **test_account_without_children_can_be_auxiliary**: ✓ Cuentas sin hijas pueden ser auxiliares
2. **test_account_with_children_cannot_be_auxiliary**: ✓ Cuentas con hijas no pueden ser auxiliares
3. **test_cannot_add_child_to_auxiliary_account**: ✓ No se pueden agregar hijas a auxiliares
4. **test_changing_parent_to_auxiliary_fails_if_parent_has_children**: ✓ No se puede cambiar a auxiliar si tiene hijas
5. **test_leaf_account_can_receive_transactions**: ✓ Las hojas pueden recibir transacciones
6. **test_non_leaf_account_cannot_receive_transactions**: ✓ Las no-hojas NO pueden recibir transacciones

### Ejecutar las Pruebas

```bash
uv run python manage.py test contabilidad.tests.PlanCuentasHierarchyValidationTests -v 2
```

## Impacto en la Funcionalidad

### 1. Creación de Asientos (`AsientoService.crear_asiento()`)

La validación asegura que:
- Solo se pueden crear líneas en cuentas donde `puede_recibir_transacciones = True`
- Esto previene transacciones en cuentas de agrupación

```python
# En services.py
def crear_asiento(...)
    for linea_data in lineas:
        cuenta = EmpresaPlanCuenta.objects.get(id=linea_data['cuenta_id'])
        assert cuenta.puede_recibir_transacciones  # Validación adicional
```

### 2. Auditoría de Estructura

La validación permite:
- Detectar configuraciones incorrectas del plan de cuentas
- Garantizar integridad referencial de la jerarquía
- Prevenir estados inconsistentes

## Rollback y Recuperación

Si se detecta que una cuenta con hijas fue marcada como auxiliar (antes de esta validación):

```python
from django.db.models import Q
from contabilidad.models import EmpresaPlanCuenta

# Encontrar cuentas en estado incorrecto
bad_accounts = EmpresaPlanCuenta.objects.filter(
    es_auxiliar=True,
    hijas__isnull=False
).distinct()

# Corregir
for account in bad_accounts:
    account.es_auxiliar = False
    account.save(update_fields=['es_auxiliar'])
```

Esta corrección está documentada en la migración 0018 (que se puede re-crear si es necesario).

## Referencias

- **Modelo**: [contabilidad/models.py#L180-L280](../contabilidad/models.py#L180-L280)
- **Servicios**: [contabilidad/services.py#L1-L150](../contabilidad/services.py#L1-L150)
- **Pruebas**: [contabilidad/tests.py#L132-L220](../contabilidad/tests.py#L132-L220)
- **Análisis Completo**: [docs/ANALISIS_COMPLETO.md#Validación-de-Jerarquía](./ANALISIS_COMPLETO.md)

## Estado de Implementación

✅ **Completado**:
- Validación en `EmpresaPlanCuenta.clean()`
- Propiedades `tiene_hijas` y `puede_recibir_transacciones`
- Suite de pruebas unitarias (6 tests)
- Documentación de casos de uso

⏳ **Próximos Pasos**:
- Ejecutar pruebas cuando MySQL esté disponible
- Documentar en manual de usuario
- Considerar agregar constraint a nivel de base de datos (opcional)
