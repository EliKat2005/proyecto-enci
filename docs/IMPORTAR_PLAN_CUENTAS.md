# Importador de Plan de Cuentas desde Excel

## Descripción

Este módulo permite importar un Plan de Cuentas completo desde un archivo Excel (.xlsx) con validación automática y corrección de errores comunes, asegurando que cumplan con las mejores prácticas contables.

## Características

### ✅ Validaciones Implementadas

1. **Validación Estructural**
   - Columnas requeridas presentes
   - Formatos de datos correctos
   - Detecta y rechaza valores vacíos en campos obligatorios

2. **Validación Contable**
   - Códigos únicos (sin duplicados)
   - Naturaleza consistente con tipo de cuenta
   - Jerarquía válida (sin ciclos, padres existentes)
   - Cuentas auxiliares no pueden tener hijas

3. **Auto-Correcciones Automáticas**
   - Capitalización de descripciones
   - Limpieza de espacios en blanco
   - Inferencia de naturaleza desde tipo
   - Inferencia de estado situación desde tipo
   - Normalización de valores booleanos

### 📊 Formato del Excel

El archivo debe contener las siguientes columnas (flexible, admite variaciones):

| Código | Descripción | Tipo | Naturaleza | Estado Situación | Es Auxiliar | Código Padre |
|--------|-------------|------|------------|------------------|------------|------------|
| 1 | Activos | Activo | Deudora | Si | No | |
| 1.1 | Activo Corriente | Activo | Deudora | Si | No | 1 |
| 1.1.01 | Caja | Activo | Deudora | Si | Si | 1.1 |

### 📝 Formatos Aceptados

**Tipos Válidos (case-insensitive):**
- Activo / Asset
- Pasivo / Liability
- Patrimonio / Equity
- Ingreso / Revenue
- Costo / Cost
- Gasto / Expense

**Naturaleza (case-insensitive):**
- Deudora / D / D.
- Acreedora / A / A.

**Valores Booleanos:**
- true / false
- si / no
- yes / no
- s / n
- 1 / 0
- verdadero / falso

## Uso

### Vía Management Command

```bash
# Importación básica
uv run python manage.py importar_plan_cuentas --empresa-id 26 --file plan.xlsx

# Simulación sin guardar cambios (dry-run)
uv run python manage.py importar_plan_cuentas --empresa-id 26 --file plan.xlsx --dry-run

# Auto-corrección sin confirmación
uv run python manage.py importar_plan_cuentas --empresa-id 26 --file plan.xlsx --auto-corregir
```

### Vía Código Python

```python
from contabilidad.models import Empresa
from contabilidad.services_excel_import import ExcelImportService

empresa = Empresa.objects.get(id=26)
servicio = ExcelImportService('ruta/al/plan.xlsx')

# 1. Cargar archivo
if not servicio.cargar_archivo():
    print("Errores:", servicio.errores)
    exit(1)

# 2. Validar y corregir
datos, errores, advertencias = servicio.validar_y_corregir()

if errores:
    print("Errores encontrados:", errores)
    exit(1)

# 3. Validar jerarquía
errores_jerarquia = servicio.validar_jerarquia(datos)

if errores_jerarquia:
    print("Errores de jerarquía:", errores_jerarquia)
    exit(1)

# 4. Importar
cantidad, errores_import = servicio.importar(empresa, datos)

print(f"Importadas {cantidad} cuentas")
```

## Reglas de Validación

### Códigos de Cuenta
- Deben ser únicos dentro de la empresa
- Pueden usar cualquier formato (ej: "1", "1.1", "1.1.01")

### Naturaleza vs. Tipo
La naturaleza debe ser coherente con el tipo:

| Tipo | Naturaleza Esperada |
|------|-------------------|
| Activo | Deudora |
| Pasivo | Acreedora |
| Patrimonio | Acreedora |
| Ingreso | Acreedora |
| Costo | Deudora |
| Gasto | Deudora |

### Estado Situación
Se asigna automáticamente según el tipo:

| Tipo | Estado Situación |
|------|-----------------|
| Activo/Pasivo/Patrimonio | True (Balance) |
| Ingreso/Costo/Gasto | False (Resultado) |

### Jerarquía
- Si una cuenta tiene `codigo_padre`, ese padre debe existir en los datos
- No se permiten ciclos (A → B → A)
- Una cuenta auxiliar no puede tener cuentas hijas

## Flujo de Importación

1. **Carga**: Lee el archivo Excel y extrae headers y datos
2. **Validación**: Verifica estructura y contenido
3. **Corrección**: Aplica auto-correcciones a errores comunes
4. **Jerarquía**: Valida relaciones padre-hijo
5. **Confirmación**: Muestra resumen y pide confirmación
6. **Importación**: Crea cuentas en la base de datos (en 2 pasadas: sin padre, con padre)
7. **Reporte**: Muestra resultados y errores ocurridos

## Manejo de Errores

### Errores Bloqueantes (detienen importación)
- Código duplicado
- Tipo inválido
- Naturaleza inválida e imposible de inferir
- Padre inexistente
- Ciclos en jerarquía
- Cuenta auxiliar con hijas

### Advertencias (solo notificación)
- Inconsistencia tipo-naturaleza (se corrige automáticamente)
- Cuenta con saldo negativo contra su naturaleza

## Ejemplo de Uso Completo

```bash
# 1. Preparar Excel con plan de cuentas
# (crear archivo: plan_2026.xlsx con estructura indicada)

# 2. Simular importación (sin guardar)
uv run python manage.py importar_plan_cuentas \
  --empresa-id 26 \
  --file plan_2026.xlsx \
  --dry-run

# 3. Si todo está bien, importar con auto-corrección
uv run python manage.py importar_plan_cuentas \
  --empresa-id 26 \
  --file plan_2026.xlsx \
  --auto-corregir
```

## Testing

```bash
# Ejecutar tests del servicio de importación
uv run python -m pytest contabilidad/test_excel_import.py -v

# Tests específicos
uv run python -m pytest contabilidad/test_excel_import.py::ExcelImportServiceTestCase::test_importar_cuentas_simple -v
```

## Mejoras Futuras

- [ ] API REST para upload de archivos
- [ ] Vista web para importación
- [ ] Validaciones personalizadas por empresa
- [ ] Historial de importaciones
- [ ] Rollback de importaciones fallidas
- [ ] Exportación de plan de cuentas a Excel
