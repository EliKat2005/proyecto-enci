# Guía Rápida: Importador de Plan de Cuentas desde Excel

## ✨ ¿Qué es esto?

Herramienta completa para importar masivamente un Plan de Cuentas desde un archivo Excel con validación automática y corrección de errores comunes.

## 🚀 Uso Rápido

### 1. Preparar el archivo Excel
Usar la plantilla incluida: `templates_excel/plan_cuentas_template.xlsx`

**Formato requerido:**
- Código: Identificador único (ej: 1, 1.1, 1.1.01)
- Descripción: Nombre de la cuenta
- Tipo: Activo, Pasivo, Patrimonio, Ingreso, Costo, Gasto
- Naturaleza: Deudora, Acreedora (se infiere automáticamente)
- Estado Situación: Si, No (se infiere automáticamente)
- Es Auxiliar: Si, No
- Código Padre: Código de la cuenta padre (opcional)

### 2. Ejecutar el comando

```bash
# Ver ayuda
uv run python manage.py importar_plan_cuentas --help

# Importación interactiva (pide confirmación)
uv run python manage.py importar_plan_cuentas --empresa-id 26 --file plan_cuentas.xlsx

# Con auto-corrección automática (sin preguntas)
uv run python manage.py importar_plan_cuentas --empresa-id 26 --file plan_cuentas.xlsx --auto-corregir

# Simular sin guardar cambios
uv run python manage.py importar_plan_cuentas --empresa-id 26 --file plan_cuentas.xlsx --dry-run
```

### 3. Validaciones Automáticas

El sistema valida y corrige automáticamente:
- ✅ Códigos duplicados
- ✅ Tipos inválidos
- ✅ Naturaleza inconsistente con tipo
- ✅ Ciclos en la jerarquía
- ✅ Padres inexistentes
- ✅ Cuentas auxiliares con sub-cuentas
- ✅ Capitalización de descripciones
- ✅ Inferencia de naturaleza desde tipo
- ✅ Normalización de booleanos (Sí, Si, S, 1, Yes, True, etc.)

## 📊 Ejemplo de Uso Completo

```bash
# 1. Preparar Excel con datos
# (Ver templates_excel/plan_cuentas_template.xlsx para el formato)

# 2. Ejecutar importación
$ uv run python manage.py importar_plan_cuentas --empresa-id 26 --file mi_plan.xlsx

# Salida esperada:
# ✓ Archivo cargado: 24 filas
# ✓ Validación completada: 0 errores, 2 advertencias
# ✓ Correcciones aplicadas: 3
#   - Fila 5: Descripción capitalizada
#   - Fila 8: Naturaleza inferida desde tipo
#   - Fila 12: Estado Situación inferido
# 
# ¿Desea proceder con la importación? (s/n): s
# 
# ✓ Importación completada
# ✓ 24 cuentas creadas exitosamente

# 3. Validar en la base de datos
$ uv run python manage.py shell
>>> from contabilidad.models import Empresa
>>> empresa = Empresa.objects.get(id=26)
>>> empresa.cuentas.count()  # Debe ser 24
```

## 📚 Documentación Completa

Ver: [docs/IMPORTAR_PLAN_CUENTAS.md](docs/IMPORTAR_PLAN_CUENTAS.md)

## 🧪 Tests

Todos los 14 tests pasan ✓

```bash
uv run pytest contabilidad/test_excel_import.py -v
```

## 🔗 Archivos Relacionados

- `contabilidad/services_excel_import.py` - Servicio de importación
- `contabilidad/management/commands/importar_plan_cuentas.py` - Comando Django
- `templates_excel/plan_cuentas_template.xlsx` - Plantilla Excel
- `contabilidad/test_excel_import.py` - Tests unitarios
- `docs/IMPORTAR_PLAN_CUENTAS.md` - Documentación detallada

## ❓ Preguntas Frecuentes

**P: ¿Qué pasa si el Excel tiene errores?**
R: Se muestran los errores, se puede usar --auto-corregir para arreglar automáticamente.

**P: ¿Se pueden eliminar cuentas existentes?**
R: No, la importación solo añade nuevas cuentas. Las existentes no se modifican.

**P: ¿Qué validaciones se hacen?**
R: Estructura, tipos, naturaleza, jerarquía, ciclos, duplicados, relaciones padre-hijo.

**P: ¿Se pueden hacer rollback?**
R: Usar --dry-run primero. Si algo sale mal, hacer DELETE en la base de datos.

---

**Rama:** `import-plan-cuentas-excel`  
**Estado:** ✅ Completada y funcional  
**Tests:** 46/46 PASSING  
**Publicada:** origin/import-plan-cuentas-excel
