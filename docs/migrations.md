# Guía de Migraciones Django

## Contexto

Este proyecto usa Django con MySQL y ha implementado:
1. **DEFAULT_AUTO_FIELD global:** `django.db.models.BigAutoField` en `config/settings.py`.
2. **Conversión INT→BIGINT:** Migración personalizada que convierte todas las PKs y FKs de `INT` a `BIGINT`.
3. **Squash de migraciones:** Compactación de migraciones antiguas para instalaciones nuevas (reducción de historial).

---

## 1. Configuración Global (Ya Hecha)

### DEFAULT_AUTO_FIELD

En [config/settings.py](../config/settings.py#L137):
```python
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

### Apps Override

- [core/apps.py](../core/apps.py#L4-L11): `default_auto_field = 'django.db.models.BigAutoField'`
- [contabilidad/apps.py](../contabilidad/apps.py#L4-L9): `default_auto_field = 'django.db.models.BigAutoField'`

No sobrescriben a `AutoField`, sino que refuerzan la configuración global.

---

## 2. Conversión INT→BIGINT

### Migración Implementada

- **Archivo:** `contabilidad/migrations/0016_convert_int_pk_to_bigint.py`
- **Función:** Detecta dinámicamente PK `id` en `INT` y las convierte a `BIGINT`, junto con todas sus FKs referenciadas.
- **Seguridad:** Preserva `ON DELETE/UPDATE` rules y nulabilidad de columnas.
- **Re-ejecutable:** Segura de ejecutar varias veces; si ya es `BIGINT` se omite.

### Verificación

Ejecuta el script de verificación para confirmar que no quedan `INT` PKs ni FKs:
```bash
uv run python scripts/verify_bigint.py
```

**Salida esperada:**
```
-- Verificación PK 'id' con tipo INT --
OK: No hay PK 'id' con INT.

-- Verificación FKs que no son BIGINT --
OK: Todas las FKs referenciadas son BIGINT.
```

---

## 3. Squash de Migraciones

### Migraciones Squashed

Migraciones viejas fueron "aplastadas" (compactadas) en nuevas migraciones squashed:

- **contabilidad:** `0001_squashed_0016_convert_int_pk_to_bigint.py` reemplaza `0001_initial` hasta `0016_convert_int_pk_to_bigint`
- **core:** `0001_squashed_0006_migrate_existing_data_to_grupos.py` reemplaza `0001_initial` hasta `0006_migrate_existing_data_to_grupos`

### Cómo Funciona

- Cada squashed contiene `replaces = [...]` que lista las migraciones que reemplaza.
- En bases **ya migradas:** Las migraciones antiguas se marcan como "aplicadas" sin re-ejecutar. Django usa la squashed para bases nuevas.
- En bases **nuevas:** Se aplica solo la squashed, ahorrando tiempo y reduciendo historial.

### Funciones RunPython Inlined

Las funciones que corren en base de datos durante migraciones fueron copiadas dentro de las squashed:
- `migrate_data_to_grupos()` en core squashed
- `convert_int_pk_fk_to_bigint()` en contabilidad squashed
- `fix_transactions_with_both_positive()` en contabilidad squashed

Esto evita referencias rotas a módulos de migraciones antiguas.

---

## 4. Operaciones Diarias

### Verificar Estado

```bash
# Ver todas las migraciones aplicadas
uv run python manage.py showmigrations

# Verificar que no hay issues
uv run python manage.py check

# Aplicar nuevas migraciones (si existen)
uv run python manage.py migrate
```

### Crear Nueva Migración

```bash
# Si cambias un modelo
uv run python manage.py makemigrations

# Revisar el SQL generado (opcional)
uv run python manage.py sqlmigrate contabilidad <numero>

# Aplicar
uv run python manage.py migrate
```

---

## 5. Respaldo y Restauración de Base de Datos

### Respaldo Completo

**Siempre antes de aplicar migraciones en producción:**

```bash
# Cargar variables de entorno
set -a; source .env; set +a

# Dump con CREATE DATABASE (recomendado)
mysqldump -h "$DB_HOST" -u "$DB_USER" -p --databases "$DB_NAME" > backup_$(date +%F).sql

# O dump solo de tablas (más compacto)
mysqldump -h "$DB_HOST" -u "$DB_USER" -p "$DB_NAME" > backup_$(date +%F).sql
```

**Verificar que las variables están cargadas:**
```bash
echo "DB_HOST=$DB_HOST DB_USER=$DB_USER DB_NAME=$DB_NAME"
```

### Restauración

**Si el dump fue con `--databases`:**
```bash
set -a; source .env; set +a
mysql -h "$DB_HOST" -u "$DB_USER" -p < backup_2026-01-06.sql
```

**Si el dump fue solo de tablas:**
```bash
set -a; source .env; set +a
mysql -h "$DB_HOST" -u "$DB_USER" -p "$DB_NAME" < backup_2026-01-06.sql
```

### Verificar Base Restaurada

```bash
set -a; source .env; set +a
mysql -h "$DB_HOST" -u "$DB_USER" -p -D "$DB_NAME" -e "SHOW TABLES; SELECT COUNT(*) FROM django_migrations;"
```

---

## 6. Limpieza Futura de Migraciones Antiguas

### Cuándo Hacerlo

**Cuando TODOS los entornos (desarrollo, staging, producción) estén confirmados con las migraciones squashed aplicadas.**

Esto puede ser después de varias semanas o meses, según tu política de despliegue.

### Pasos

1. **Crea una rama dedicada:**
   ```bash
   git checkout -b cleanup-migrations
   ```

2. **Haz respaldo de DB:**
   ```bash
   set -a; source .env; set +a
   mysqldump -h "$DB_HOST" -u "$DB_USER" -p --databases "$DB_NAME" > backup_$(date +%F)_pre_cleanup.sql
   ```

3. **Elimina migraciones antiguas:**
   - Borra los archivos de `contabilidad/migrations/0001_initial.py` hasta `0016_convert_int_pk_to_bigint.py` (excepto la squashed).
   - Borra los archivos de `core/migrations/0001_initial.py` hasta `0006_migrate_existing_data_to_grupos.py` (excepto la squashed).

4. **Edita las squashed para quitar `replaces`:**

   **contabilidad/migrations/0001_squashed_0016_convert_int_pk_to_bigint.py:**
   - Quita la línea: `replaces = [(...), ...]`
   - Deja en blanco o solo el `class Migration`.

   **core/migrations/0001_squashed_0006_migrate_existing_data_to_grupos.py:**
   - Quita la línea: `replaces = [(...), ...]`

5. **Verifica en base limpia:**
   ```bash
   # Crea una DB de prueba o usa DB vacía
   uv run python manage.py migrate
   uv run python manage.py showmigrations  # Debe mostrar las squashed sin "reemplazos"
   uv run python manage.py check
   ```

6. **Abre Pull Request y despliega:**
   ```bash
   git add contabilidad/migrations/0001_squashed_0016_convert_int_pk_to_bigint.py \
           core/migrations/0001_squashed_0006_migrate_existing_data_to_grupos.py
   git commit -m "Cleanup: elimina migraciones antiguas, mantiene squashed como baseline"
   git push origin cleanup-migrations
   ```
   
   - Abre PR, revisa cambios.
   - Despliega coordinadamente (en CI/CD o manualmente).
   - **Nota:** Las bases ya migradas no se ven afectadas; las squashed ya estaban registradas.

7. **Limpia respaldos antiguos (opcional):**
   ```bash
   rm backup_*.sql
   ```

---

## 7. Troubleshooting

### Error: "MySQL OperationalError 1005 (errno 150)"

**Causa:** Incompatibilidad entre tipos de PKs (`INT`) y FKs (`BIGINT`).

**Solución:**
1. Verifica que `DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'` en settings.
2. Ejecuta `scripts/verify_bigint.py` para detectar FKs mismatch.
3. Re-ejecuta la migración `0016_convert_int_pk_to_bigint.py`:
   ```bash
   uv run python manage.py migrate contabilidad 0016_convert_int_pk_to_bigint
   ```

### Error: "Invalid Decimal Literal" en Migraciones Squashed

**Causa:** Migraciones antiguas con referencias rotas a módulos (ej. `core.migrations.0006_migrate_existing_data_to_grupos.migrate_data_to_grupos`).

**Solución:** Las funciones RunPython deben estar inlined en la squashed. Verifica que contienen:
- `def migrate_data_to_grupos(...)`
- `def convert_int_pk_fk_to_bigint(...)`
- `def reverse_migration(...)`
- Y `RunPython` las referencia localmente (sin módulo).

---

## Referencias

- [Django Migrations Docs](https://docs.djangoproject.com/en/5.2/topics/migrations/)
- [Django Squash Migrations](https://docs.djangoproject.com/en/5.2/topics/migrations/#squashing-migrations)
- [MySQL BIGINT vs INT](https://dev.mysql.com/doc/refman/8.0/en/integer-types.html)
