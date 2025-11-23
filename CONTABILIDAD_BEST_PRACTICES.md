# Mejores Prácticas Contables Implementadas

## Resumen de Implementación

Este documento detalla las mejoras realizadas al sistema contable siguiendo las mejores prácticas internacionales y normativas tributarias.

---

## 1. Plan de Cuentas (Catálogo) ✅

### Estructura Jerárquica
- **Relación recursiva**: Campo `padre` permite crear estructura de árbol
- **Niveles**: Elemento → Grupo → Subgrupo → Cuenta → Subcuenta
- **Validación de jerarquía**: Los códigos de cuentas hijas deben comenzar con el código del padre

### Campos Clave
- `codigo`: Único por empresa, indexado
- `descripcion`: Nombre de la cuenta
- `tipo`: Activo, Pasivo, Patrimonio, Ingreso, Costo, Gasto
- `naturaleza`: Deudora o Acreedora
- `estado_situacion`: Balance (True) o Resultado (False)
- `es_auxiliar`: Indica si puede recibir transacciones

### Validaciones Implementadas
```python
# Solo cuentas auxiliares (hojas) pueden recibir transacciones
@property
def puede_recibir_transacciones(self):
    return self.es_auxiliar and not self.tiene_hijas
```

**Best Practice**: Previene errores comunes donde se registran movimientos en cuentas agrupadoras (ej: "1. ACTIVO").

---

## 2. Libro Diario ✅

### Modelo Asiento (Cabecera)
- **Numeración secuencial**: `numero_asiento` auto-incremental por empresa (auditoría)
- **Estados**: Borrador → Confirmado → Anulado
- **Soft Delete**: Los asientos NO se eliminan, se anulan con contra-asiento

### Campos de Auditoría
- `creado_por`: Usuario creador
- `fecha_creacion` / `fecha_modificacion`: Timestamps automáticos
- `anulado_por` / `fecha_anulacion` / `motivo_anulacion`: Trazabilidad de anulaciones
- `anulado_mediante`: Referencia al contra-asiento

### Validaciones de Integridad

#### Partida Doble (Debe = Haber)
```python
@property
def esta_balanceado(self):
    totales = self.lineas.aggregate(
        total_debe=Sum('debe'),
        total_haber=Sum('haber')
    )
    debe = totales['total_debe'] or Decimal('0.00')
    haber = totales['total_haber'] or Decimal('0.00')
    return debe == haber
```

**Implementación**: El servicio `AsientoService.crear_asiento()` valida que Debe = Haber antes de guardar.

#### Bancarización (Normativa Tributaria)
```python
LIMITE_BANCARIZACION = Decimal('1000.00')  # USD

# Si monto > $1,000 y se usa Caja → ERROR
# Debe usar cuenta Banco
```

**Best Practice**: Cumple con normativas tributarias que requieren bancarización de operaciones mayores.

---

## 3. Modelo de Transacciones (Líneas de Asiento)

### Validaciones por Línea
```python
def clean(self):
    # 1. Solo cuentas auxiliares
    if not self.cuenta.puede_recibir_transacciones:
        raise ValidationError('Solo cuentas de último nivel')
    
    # 2. No puede haber Debe Y Haber en la misma línea
    if self.debe > 0 and self.haber > 0:
        raise ValidationError('Use líneas separadas')
    
    # 3. Al menos uno debe ser > 0
    if self.debe == 0 and self.haber == 0:
        raise ValidationError('Monto requerido')
    
    # 4. No negativos
    if self.debe < 0 or self.haber < 0:
        raise ValidationError('No negativos')
```

---

## 4. Anulación de Asientos (No Hard Delete) ✅

### Método de Anulación
```python
def anular(self, usuario, motivo):
    # 1. Crear contra-asiento con líneas invertidas
    contra_asiento = EmpresaAsiento.objects.create(
        descripcion_general=f'ANULACIÓN: {self.descripcion_general}',
        estado=EstadoAsiento.CONFIRMADO
    )
    
    # 2. Invertir Debe ↔ Haber
    for linea in self.lineas.all():
        EmpresaTransaccion.objects.create(
            asiento=contra_asiento,
            cuenta=linea.cuenta,
            debe=linea.haber,  # Invertir
            haber=linea.debe   # Invertir
        )
    
    # 3. Marcar original como anulado
    self.estado = EstadoAsiento.ANULADO
    self.anulado_por = usuario
    self.save()
```

**Best Practice**: Mantiene la integridad de auditoría. Los asientos anulados permanecen en la base de datos con trazabilidad completa.

---

## 5. Libro Mayor (Cálculo Dinámico - No Persiste) ✅

### Servicio LibroMayorService
No crea tablas, calcula al vuelo.

```python
def calcular_saldos_cuenta(cuenta, fecha_inicio, fecha_fin):
    # 1. Saldo inicial (antes de fecha_inicio)
    # 2. Movimientos del período
    # 3. Saldo final
    
    # Fórmula según naturaleza:
    if cuenta.naturaleza == DEUDORA:
        saldo = saldo_inicial + debe - haber
    else:  # ACREEDORA
        saldo = saldo_inicial + haber - debe
```

**Best Practice**: Evita redundancia de datos. El Libro Mayor se genera a demanda.

### Balance de Comprobación
```python
balance_de_comprobacion(empresa, fecha)
# Retorna todas las cuentas con:
# - Debe del período
# - Haber del período
# - Saldo Deudor
# - Saldo Acreedor
```

---

## 6. Estados Financieros ✅

### Estado de Resultados
```python
def estado_de_resultados(empresa, fecha_inicio, fecha_fin):
    # Ingresos (naturaleza acreedora)
    # - Costos (naturaleza deudora)
    # = Utilidad Bruta
    # - Gastos (naturaleza deudora)
    # = Utilidad Neta
```

### Balance General
```python
def balance_general(empresa, fecha_corte):
    # Activos (naturaleza deudora)
    # = Pasivos + Patrimonio (naturaleza acreedora)
    
    # Valida: Activo = Pasivo + Patrimonio
```

### Asiento de Cierre del Ejercicio
```python
def asiento_de_cierre(empresa, fecha_cierre, usuario):
    # 1. Cierra Ingresos → Debe (cancela saldo acreedor)
    # 2. Cierra Costos/Gastos → Haber (cancela saldo deudor)
    # 3. Diferencia → Cuenta "Resultados del Ejercicio" (Patrimonio)
    
    # Resultado: Todas las cuentas de resultado quedan en 0
```

**Best Practice**: Automatiza el proceso de cierre anual contable.

---

## 7. Índices de Base de Datos ✅

### Campos Indexados
```python
# EmpresaPlanCuenta
indexes = [
    ('empresa', 'codigo'),
    ('empresa', 'tipo'),
    ('empresa', 'es_auxiliar'),
]

# EmpresaAsiento
indexes = [
    ('empresa', 'fecha'),
    ('empresa', 'estado'),
    ('empresa', 'numero_asiento'),
]

# EmpresaTransaccion
indexes = [
    ('asiento', 'cuenta'),
    ('cuenta',),
]
```

**Best Practice**: Optimiza consultas frecuentes (búsquedas por fecha, empresa, cuenta).

---

## 8. Seguridad y Atomicidad ✅

### Uso de Transacciones
```python
@transaction.atomic
def crear_asiento(...):
    # Si falla cualquier línea → Rollback completo
    asiento.save()
    for linea in lineas:
        linea.save()
```

**Best Practice**: Garantiza que un asiento nunca quede parcialmente guardado.

---

## 9. Validaciones Tributarias Específicas

### Bancarización
- **Norma**: Transacciones > $1,000 USD deben ser bancarizadas
- **Implementación**: `AsientoService._validar_bancarizacion()`
- **Acción**: Bloquea el asiento si usa Caja en lugar de Banco

### Retenciones (Preparado para extensión)
El servicio está preparado para agregar:
- Detección de compras (cuentas de proveedores)
- Cálculo automático de retenciones de IVA
- Cuentas de retención en el plan de cuentas

---

## 10. Arquitectura de Servicios

### Separación de Responsabilidades
```
models.py       → Estructura de datos + validaciones de modelo
services.py     → Lógica de negocio compleja
views.py        → Orquestación + presentación
```

**Best Practice**: Lógica contable centralizada en servicios reutilizables.

---

## Uso de los Servicios

### Ejemplo: Crear Asiento con Validaciones
```python
from contabilidad.services import AsientoService

asiento = AsientoService.crear_asiento(
    empresa=mi_empresa,
    fecha=date.today(),
    descripcion='Compra de mercadería',
    lineas=[
        {
            'cuenta_id': cuenta_inventario.id,
            'detalle': 'Mercadería',
            'debe': Decimal('1500.00'),
            'haber': Decimal('0.00')
        },
        {
            'cuenta_id': cuenta_banco.id,
            'detalle': 'Pago con transferencia',
            'debe': Decimal('0.00'),
            'haber': Decimal('1500.00')
        }
    ],
    creado_por=request.user,
    auto_confirmar=True
)
# Validaciones automáticas:
# ✓ Partida doble (1500 = 1500)
# ✓ Solo cuentas auxiliares
# ✓ Bancarización (monto > $1000, usa Banco ✓)
# ✓ Numeración secuencial
```

### Ejemplo: Generar Estado de Resultados
```python
from contabilidad.services import EstadosFinancierosService

resultado = EstadosFinancierosService.estado_de_resultados(
    empresa=mi_empresa,
    fecha_inicio=date(2025, 1, 1),
    fecha_fin=date(2025, 12, 31)
)

print(f"Ingresos: ${resultado['ingresos']}")
print(f"Costos: ${resultado['costos']}")
print(f"Gastos: ${resultado['gastos']}")
print(f"Utilidad Neta: ${resultado['utilidad_neta']}")
```

### Ejemplo: Anular Asiento
```python
# NO hacer: asiento.delete()  ❌

# CORRECTO:
asiento.anular(
    usuario=request.user,
    motivo='Error en el monto registrado'
)
# Resultado:
# - Asiento original → estado=ANULADO
# - Nuevo contra-asiento creado automáticamente
# - Trazabilidad completa
```

---

## Próximos Pasos Sugeridos

1. **Interfaz de Usuario**:
   - Formulario dinámico para crear asientos (múltiples líneas)
   - Vista del Libro Mayor con drill-down
   - Reportes PDF de estados financieros

2. **Validaciones Adicionales**:
   - Detección automática de cuentas duplicadas
   - Sugerencias de cuentas basadas en descripciones (IA)
   - Validación de montos máximos por tipo de operación

3. **Automatizaciones**:
   - Plantillas de asientos recurrentes (nómina, servicios)
   - Asientos predefinidos (compra, venta, pago)
   - Integración con facturación electrónica

4. **Reportes Avanzados**:
   - Flujo de efectivo
   - Razones financieras
   - Gráficos de tendencias

---

## Cumplimiento de Normativas

✅ **Partida Doble**: Implementada y validada  
✅ **Auditoría**: Numeración secuencial sin huecos  
✅ **No eliminación**: Soft-delete con contra-asientos  
✅ **Bancarización**: Validación automática  
✅ **Trazabilidad**: Quién, cuándo, qué modificó  
✅ **Integridad**: Transacciones atómicas  
✅ **Performance**: Índices en campos clave  

---

**Fecha de Implementación**: 22 de noviembre de 2025  
**Versión del Sistema**: 1.0  
**Framework**: Django 5.2.8  
**Base de Datos**: PostgreSQL (recomendado) / SQLite (desarrollo)
