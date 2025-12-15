# Estándar de Ingeniería de Software Contable (Best Practices)

**Versión del Documento:** 2.1.0 (Edición MariaDB/Debian)  
**Estado:** Release Candidate  
**Última actualización:** 14 de diciembre de 2025

---

## 📋 Target Stack

| Componente | Tecnología |
|------------|------------|
| **Lenguaje** | Python 3.13 |
| **Gestor de Paquetes** | uv (Astral) |
| **Base de Datos** | MariaDB 10.11+ (InnoDB Engine) |
| **Sistema Operativo** | Debian 13 "Trixie" GNU/Linux |
| **Framework** | Django 5.x |

---

## 🎯 Objetivo

Definir la arquitectura, reglas de negocio y patrones de diseño para el desarrollo de un **Sistema de Contabilidad Core**, asegurando:
- ✅ Integridad financiera
- ✅ Escalabilidad
- ✅ Cumplimiento normativo (NIIF/GAAP)

---

---

## 1. Arquitectura de Datos: El Plan de Cuentas (Core)

**El corazón del sistema.** Se abandona la estructura plana y visual del Excel (`Plan de cuentas.csv`) en favor de un modelo de **Árbol de Adyacencia** optimizado para consultas recursivas (CTE) en MariaDB.

### 1.1 Modelo: `PlanCuenta`

**Motor de Almacenamiento:** Estrictamente **InnoDB** para garantizar integridad referencial.

#### Jerarquía Recursiva (Adjacency List Pattern)

- **Campo `parent_id`:** Apunta a la cuenta padre
- **Integridad Estructural:** Validación en Python para evitar ciclos (una cuenta no puede ser ancestro de sí misma)

#### Segregación de Roles (Tipos de Nodo)

| Tipo | Descripción | ¿Recibe Transacciones? |
|------|-------------|------------------------|
| **Nodos Acumuladores (View)** | Elementos, Grupos y Subgrupos. Solo sirven para agrupar en reportes | ❌ PROHIBIDO |
| **Nodos Transaccionales (Hojas)** | Cuentas y Subcuentas. Son las únicas que reciben asientos | ✅ PERMITIDO |

#### Normalización de Naturaleza

| Naturaleza | Tipos de Cuenta | Comportamiento |
|------------|-----------------|----------------|
| **DEUDORA** | Activos (1), Costos (5), Gastos (6) | Aumentan al **Debe** |
| **ACREEDORA** | Pasivos (2), Patrimonio (3), Ingresos (4) | Aumentan al **Haber** |

### 1.2 Validaciones de Integridad (Business Logic)

```python
# Validación de Estructura de Código (Naming Convention)
def clean(self):
    if self.parent:
        if not self.codigo.startswith(self.parent.codigo):
            raise ValidationError(
                f"El código {self.codigo} debe comenzar con el prefijo "
                f"del padre {self.parent.codigo}"
            )
            
# Propiedad de Bloqueo
@property
def puede_recibir_transacciones(self):
    # Solo si es hoja (auxiliar) y está activa
    return self.es_auxiliar and not self.tiene_hijas and self.activa
```

---
---

## 2. Gestión de Entidades (Normalización de Terceros)

**Mejora crítica sobre el Excel:** En el archivo `Libro Diario.csv`, los beneficiarios están mezclados en texto libre. En un sistema profesional, esto debe normalizarse para reportes fiscales.

### 2.1 Modelo: `EmpresaTercero` (Auxiliares)

**Características principales:**
- **Identificador Fiscal:** RUC/Cédula/DNI (Validado con algoritmo módulo 11/10 según país)
- **Taxonomía:** Cliente, Proveedor, Empleado, Accionista, Gobierno

**Implementación:**
- Cada línea del asiento contable (`EmpresaTransaccion`) tendrá una `ForeignKey` nullable a `EmpresaTercero`
- **Beneficio:** Permite reportes de "Libro Auxiliar por Tercero" (Sub-ledger), vital para declaraciones como el DIOT o Anexos Transaccionales

---

---

## 3. Libro Diario y Transaccionalidad (ACID)

Implementación estricta de principios contables sobre MariaDB.

### 3.1 Eliminación del concepto "Parcial" (Excel Legacy)

❌ **En el Excel** `Libro Diario.csv`, la columna "Parcial" se usa para sub-detalles visuales.  
✅ **Arquitectura Web:** La columna "Parcial" **SE ELIMINA** del modelo de datos.

**Solución:** Todos los montos se guardan en las columnas `Debe` o `Haber` asociadas directamente a la cuenta de último nivel.

### 3.2 Modelo: `AsientoContable` (Header)

#### Numeración Fiscal
- **Consecutivo anual ininterrumpido**
- **Implementación MariaDB:** Uso de Sequences (Soportado nativamente desde MariaDB 10.3)
  ```sql
  CREATE SEQUENCE seq_asientos_2025;
  ```
- **Ventaja:** Garantiza que no haya huecos incluso si una transacción falla, superando al `AUTO_INCREMENT` tradicional

#### Máquina de Estados

| Estado | Descripción | ¿Editable? |
|--------|-------------|------------|
| `BORRADOR` | En construcción | ✅ SÍ |
| `CONFIRMADO` | Registrado oficialmente | ❌ Inmutable (Read-only) |
| `ANULADO` | Cancelado con contra-asiento | ❌ Inmutable |

### 3.3 Modelo: `DetalleAsiento` (Lines)

#### Constraints (MariaDB CHECK Constraints)

MariaDB soporta CHECK constraints desde la versión 10.2.1:

```sql
CONSTRAINT chk_debe_positivo CHECK (debe >= 0)
CONSTRAINT chk_haber_positivo CHECK (haber >= 0)
CONSTRAINT chk_imputacion_unica CHECK (NOT(debe > 0 AND haber > 0))
```

### 3.4 Atomicidad (Database Transactions)

El guardado es **"Todo o Nada"** usando el motor InnoDB:

```python
@transaction.atomic
def guardar_asiento_completo(cabecera, lineas):
    # Django inicia: START TRANSACTION
    cabecera.save()
    for linea in lineas:
        linea.save()
    # Django ejecuta: COMMIT
    # Si falla algo: ROLLBACK automático
```

---
---

## 4. Reglas de Negocio (Service Layer)

Lógica encapsulada en `AsientoService.py`.

### 4.1 Principio de Partida Doble
```python
# Validación estricta
assert SUM(Debe) == SUM(Haber), "Asiento desbalanceado"
# Tolerancia: 0.00 (Sin margen de error)
```

### 4.2 Validación de Bancarización (Anti-Lavado)

**Regla:** Si `Monto > 1000 USD` **Y** la cuenta es `1.1.1.01 (Caja)` → `ValidationError`

**Acción:** Obligar al usuario a usar cuentas del grupo `1.1.1.03 (Bancos)`

```python
LIMITE_BANCARIZACION = Decimal('1000.00')

def validar_bancarizacion(monto, cuenta):
    if monto > LIMITE_BANCARIZACION and cuenta.es_caja():
        raise ValidationError(
            f'Operaciones > ${LIMITE_BANCARIZACION} requieren bancarización. '
            f'Use una cuenta bancaria en lugar de Caja.'
        )
```

### 4.3 Periodo Contable

**Regla:** Impedir asientos en fechas donde el mes contable ya fue "Cerrado"

```python
def validar_periodo_abierto(fecha):
    if PeriodoContable.objects.filter(
        anio=fecha.year, 
        mes=fecha.month, 
        estado='CERRADO'
    ).exists():
        raise ValidationError('El periodo contable está cerrado')
```

---

---

## 5. Auditoría e Inmutabilidad (Security)

### 5.1 Soft Deletes & Reversiones

**⚠️ Regla de Oro:** Un asiento `CONFIRMADO` **JAMÁS** recibe un `DELETE SQL`.

#### Patrón de Anulación (Reversal)

1. Usuario solicita anular **Asiento #100**
2. Sistema genera **Asiento #101** (Tipo "Anulación")
3. El **#101** invierte los montos del **#100**:
   ```python
   for linea in asiento_100.lineas.all():
       DetalleAsiento.objects.create(
           asiento=asiento_101,
           cuenta=linea.cuenta,
           debe=linea.haber,    # ← Invertir
           haber=linea.debe     # ← Invertir
       )
   ```
4. El sistema marca el **#100** como `ANULADO` y setea `reversed_by_id = 101`

### 5.2 Trazabilidad (Logging)

**Campos de auditoría obligatorios:**
- `created_by`: Usuario creador
- `created_at`: Timestamp de creación
- `modified_by`: Último usuario que modificó
- `modified_at`: Timestamp de última modificación
- `ip_address`: Dirección IP del usuario

**Implementación:**
```python
# Middleware para capturar created_by, ip_address
# Uso de django-simple-history o tabla de auditoría manual
# para cambios críticos en el plan de cuentas
```

---

---

## 6. Reportería Dinámica y Performance

### 6.1 Motor de Cálculo (On-the-Fly)

**Principio:** ❌ **No almacenar saldos** → ✅ El saldo de una cuenta es siempre **calculado dinámicamente**.

#### Optimización SQL en MariaDB

**1. Índices compuestos B-Tree:**
```sql
CREATE INDEX idx_transaccion_cta_fecha 
ON transacciones (cuenta_id, fecha_contable);
```

**2. Recursive Common Table Expressions (CTE):**

MariaDB soporta `WITH RECURSIVE` desde la versión 10.2. Esto es vital para calcular el Balance General (sumar hijos hacia padres) en una sola consulta SQL eficiente:

```sql
WITH RECURSIVE arbol_cuentas AS (
    -- Caso base: cuentas hoja
    SELECT id, codigo, nombre, parent_id, saldo_calculado
    FROM plan_cuentas
    WHERE es_auxiliar = TRUE
    
    UNION ALL
    
    -- Caso recursivo: sumar saldos de hijos
    SELECT p.id, p.codigo, p.nombre, p.parent_id, 
           SUM(h.saldo_calculado) as saldo_calculado
    FROM plan_cuentas p
    JOIN arbol_cuentas h ON h.parent_id = p.id
    GROUP BY p.id
)
SELECT * FROM arbol_cuentas ORDER BY codigo;
```

### 6.2 Estrategia de Caché

**Problema:** Debido al uso de Python puro, cálculos masivos pueden ser lentos.

**Solución:**
- Utilizar `django-cachalot` o caché manual con **Redis**
- Almacenar el "Balance General" de **meses cerrados** (inmutables)
- Invalidar caché solo cuando se abra/modifique un periodo

```python
from django.core.cache import cache

def obtener_balance_general(empresa, fecha):
    cache_key = f'balance_{empresa.id}_{fecha.year}_{fecha.month}'
    
    balance = cache.get(cache_key)
    if balance is None:
        balance = calcular_balance_general(empresa, fecha)
        # Cachear por 1 hora (si periodo abierto) o indefinidamente (si cerrado)
        timeout = None if periodo_cerrado(fecha) else 3600
        cache.set(cache_key, balance, timeout)
    
    return balance
```

---

---

## 7. Estrategia de Migración "Excel Legacy"

Protocolo para importar `Contabilidad_EPS_2025_Completo.xlsx`.

### 7.1 ETL con Python 3.13 + Pandas

```python
import pandas as pd
from decimal import Decimal
from datetime import datetime

def importar_plan_cuentas(archivo_excel):
    """
    Script que limpia filas de totales y extrae 
    solo movimientos de cuentas auxiliares
    """
    df = pd.read_excel(archivo_excel, sheet_name='Plan de Cuentas')
    
    # Limpiar filas que son totales/subtotales
    df = df[~df['Codigo'].str.contains('TOTAL', na=False)]
    
    # Crear solo cuentas auxiliares (último nivel)
    for _, row in df.iterrows():
        if es_cuenta_auxiliar(row['Codigo']):
            PlanCuenta.objects.create(
                codigo=row['Codigo'],
                nombre=row['Descripcion'],
                tipo=determinar_tipo(row['Codigo']),
                naturaleza=determinar_naturaleza(row['Codigo']),
                es_auxiliar=True
            )

def importar_libro_diario(archivo_excel):
    """
    Detecta nombres en la columna 'Detalle' 
    para poblar la tabla EmpresaTercero
    """
    df = pd.read_excel(archivo_excel, sheet_name='Libro Diario')
    
    for asiento_num in df['Asiento'].unique():
        lineas_asiento = df[df['Asiento'] == asiento_num]
        
        # Extraer tercero del detalle si existe
        tercero = extraer_tercero_desde_texto(
            lineas_asiento.iloc[0]['Detalle']
        )
        
        # Crear asiento y líneas...
```

### 7.2 Saldos Iniciales

**Importancia:** El **Asiento #1** del Excel (01/01/2025) se importa como **"Asiento de Apertura"**.

```python
def crear_asiento_apertura(fecha_inicio, saldos_iniciales):
    """
    Registra los saldos iniciales como primer asiento del ejercicio
    """
    asiento = AsientoContable.objects.create(
        numero=1,
        fecha=fecha_inicio,
        descripcion="ASIENTO DE APERTURA - Saldos Iniciales",
        tipo='APERTURA',
        estado='CONFIRMADO'
    )
    
    for cuenta, saldo in saldos_iniciales.items():
        if cuenta.naturaleza == 'DEUDORA':
            DetalleAsiento.objects.create(
                asiento=asiento,
                cuenta=cuenta,
                debe=saldo,
                haber=Decimal('0.00')
            )
        else:  # ACREEDORA
            DetalleAsiento.objects.create(
                asiento=asiento,
                cuenta=cuenta,
                debe=Decimal('0.00'),
                haber=saldo
            )
```

---

---

## 8. Infraestructura (Debian 13 + uv)

Diseño de despliegue sugerido para entorno Linux moderno.

### 8.1 Sistema Base

| Componente | Especificación |
|------------|----------------|
| **OS** | Debian 13 "Trixie" (Testing) o Debian 12 Stable |
| **Python** | Python 3.13 (desde repositorios oficiales) |
| **Gestor de Paquetes** | `uv` (Reemplazo moderno de pip/poetry) |

**Instalación de uv:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Instalar dependencias del proyecto:**
```bash
# uv sync crea automáticamente .venv y instala todas las dependencias
uv sync
```

### 8.2 Base de Datos

**Paquete:** `mariadb-server`
```bash
sudo apt install mariadb-server libmariadb-dev
```

**Driver Python:** `mysqlclient` (ya incluido en pyproject.toml)
```bash
# La instalación del driver se hace automáticamente con:
uv sync
```

**Configuración óptima para InnoDB:**
```ini
# /etc/mysql/mariadb.conf.d/50-server.cnf
[mysqld]
default-storage-engine = InnoDB
innodb_buffer_pool_size = 2G
innodb_log_file_size = 512M
innodb_flush_log_at_trx_commit = 1  # Máxima durabilidad ACID
sql_mode = STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION
```

### 8.3 Servidor Web

**Stack recomendado:**
```
Nginx (reverse proxy) 
    ↓ Unix Socket
Gunicorn (WSGI server)
    ↓
Django Application
```

**Gunicorn con socket Unix:**
```bash
gunicorn config.wsgi:application \
    --bind unix:/run/gunicorn.sock \
    --workers 4 \
    --timeout 120
```

**Nginx config:**
```nginx
upstream django_app {
    server unix:/run/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name contabilidad.example.com;
    
    location /static/ {
        alias /var/www/contabilidad/static/;
    }
    
    location / {
        proxy_pass http://django_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 8.4 Seguridad

**Firewall con ufw:**
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

**Backups automáticos:**
```bash
#!/bin/bash
# /usr/local/bin/backup-mariadb.sh

FECHA=$(date +%Y%m%d_%H%M%S)
DESTINO="/backup/mariadb"

mariadb-dump \
    --single-transaction \
    --quick \
    --all-databases \
    | gzip > "$DESTINO/backup_$FECHA.sql.gz"

# Eliminar backups > 30 días
find $DESTINO -name "backup_*.sql.gz" -mtime +30 -delete
```

**Cron job (diario a las 2 AM):**
```bash
0 2 * * * /usr/local/bin/backup-mariadb.sh
```

---

---

## 9. Hoja de Ruta (Features Futuros)

### 9.1 Corto Plazo (Sprint 1-2)
- [ ] **Asientos Recurrentes:** Templates para nómina y alquileres
- [ ] **Libro Mayor por Cuenta:** Drill-down interactivo
- [ ] **Balance de Comprobación:** Vista mensual/trimestral

### 9.2 Mediano Plazo (Sprint 3-4)
- [ ] **Dashboard Financiero:** Gráficos consumiendo API REST
- [ ] **Estados Financieros:** Balance General y Estado de Resultados
- [ ] **Cierre Automático:** Proceso de cierre de periodo

### 9.3 Largo Plazo (Sprint 5+)
- [ ] **Facturación Electrónica:** Generación de XML firmados (XAdES-BES)
- [ ] **Integración Bancaria:** Conciliación automática
- [ ] **Multi-moneda:** Soporte para USD/EUR con tipos de cambio

---

## 10. Matriz de Cumplimiento

| Requerimiento | Implementación Técnica (Stack Python/MariaDB) | Estado |
|---------------|-----------------------------------------------|--------|
| **Jerarquía de Cuentas** | ForeignKey('self') + CTE Recursivo (MariaDB) | ✅ |
| **Partida Doble** | Sum(debe) == Sum(haber) en clean() | ✅ |
| **Auditoría** | Soft-delete + Contra-asientos | ✅ |
| **Integridad Referencial** | Motor InnoDB (Strict Mode) | ✅ |
| **Bancarización** | Regla de negocio Python (> $1000) | ✅ |
| **Performance** | Índices + uv para dependencias rápidas | ⏳ |
| **Reportes Dinámicos** | CTE + Caché Redis | 🔄 |
| **Multi-empresa** | Tenant aislado por empresa_id | ✅ |
| **API REST** | Django REST Framework | 📋 |

**Leyenda:**
- ✅ Implementado y probado
- ⏳ Implementación parcial
- 🔄 En desarrollo
- 📋 Planificado

---

## 📚 Referencias Técnicas

### Documentación Oficial
- [MariaDB WITH RECURSIVE](https://mariadb.com/kb/en/recursive-common-table-expressions-overview/)
- [Django Transactions](https://docs.djangoproject.com/en/5.0/topics/db/transactions/)
- [uv Package Manager](https://github.com/astral-sh/uv)

### Estándares Contables
- NIIF (Normas Internacionales de Información Financiera)
- GAAP (Generally Accepted Accounting Principles)
- NIC 1: Presentación de Estados Financieros

---

## 🔒 Aprobaciones

**Arquitecto de Software:** Proyecto Universitario - Ingeniería TI 2025  
**Fecha de última revisión:** 14 de diciembre de 2025  
**Versión:** 2.1.0  

---

**Este documento es la base técnica del proyecto. Toda implementación debe seguir estos estándares.**