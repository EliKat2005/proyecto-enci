# Recuperación del Servidor de Producción

## 🚨 Problema
El servidor de producción en Azure falló al aplicar la migración 0025 con el error:
```
MySQLdb.OperationalError: (1005, "Can't create table `enci`.`contabilidad_empresa_asiento` (errno: 150 'Foreign key constraint is incorrectly formed')")
```

## ✅ Solución Implementada

Se agregó `db_constraint=False` a **TODOS** los ForeignKey que apuntan a `settings.AUTH_USER_MODEL` en:
- **contabilidad/models.py**: 13 campos
- **core/models.py**: 10 campos

Esto previene que Django intente crear constraints de base de datos reales, evitando el error 150.

### Correcciones adicionales (commit 8b2c390):
- **Error de logout**: Cambiar `redirect("core:home")` a `redirect("home")` - core no tiene namespace registrado
- **Rol de registro**: Cambiar widget de campo `role` de `RadioSelect` a `HiddenInput` para capturar correctamente el parámetro `?role=docente` de la URL

## 📋 Pasos para Recuperar el Servidor

### 1. Conectarse al servidor Azure
```bash
ssh azureuser@srv-ecae-debian
```

### 2. Navegar al directorio del proyecto
```bash
cd ~/proyecto-enci
```

### 3. Eliminar las migraciones problemáticas generadas automáticamente
```bash
# Eliminar migración 0025 de contabilidad (si existe)
rm -f contabilidad/migrations/0025_*.py

# Eliminar migración 0011 de core (si existe)
rm -f core/migrations/0011_alter_*.py

# Verificar que se eliminaron
ls -la contabilidad/migrations/
ls -la core/migrations/
```

### 4. Actualizar el código desde GitHub
```bash
git pull origin main
```

### 5. Sincronizar dependencias
```bash
uv sync
```

### 6. Verificar que NO se generen migraciones nuevas
```bash
uv run python manage.py makemigrations --dry-run
```

**Resultado esperado:**
```
No changes detected
```

### 7. Aplicar migraciones (debería estar OK)
```bash
uv run python manage.py migrate
```

**Resultado esperado:**
```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions, core, contabilidad
Running migrations:
  No migrations to apply.
```

### 8. Reiniciar el servicio gunicorn
```bash
sudo systemctl restart gunicorn
```

### 9. Verificar que el servicio esté corriendo
```bash
sudo systemctl status gunicorn
```

### 10. Verificar los logs si hay problemas
```bash
# Logs de gunicorn
sudo journalctl -u gunicorn -n 50 --no-pager

# Logs de la aplicación Django
tail -f ~/proyecto-enci/logs/django.log
```

## 🔍 Verificación Final

### Probar la aplicación
Abre el navegador y accede a la URL de producción. Verifica que:
- ✅ El sitio carga correctamente
- ✅ Puedes hacer login
- ✅ Las empresas se listan correctamente
- ✅ Puedes crear asientos contables
- ✅ No hay errores en los logs

## 📝 Explicación Técnica

### ¿Por qué ocurrió el error 150?

1. Los modelos Django tenían ForeignKey a `settings.AUTH_USER_MODEL` **sin** el parámetro `db_constraint=False`
2. Django detectó esto como "cambios" y generó automáticamente la migración 0025
3. Esta migración intentó crear constraints de base de datos reales
4. MariaDB rechazó la creación de constraints con error 150 porque:
   - Posible diferencia de tipos entre columnas (INT vs BIGINT)
   - Posible problema con referencias a la tabla auth_user
   - Los datos existentes podrían violar la constraint

### ¿Qué hace db_constraint=False?

- Deshabilita la creación de constraints de base de datos a nivel de MySQL/MariaDB
- Django sigue validando la integridad referencial a nivel de aplicación
- Previene el error 150 en entornos de producción
- Es una práctica común en proyectos Django con bases de datos MySQL/MariaDB

### ¿Por qué necesitamos db_constraint=False?

En este proyecto:
- Se convirtieron todas las PKs de INT a BIGINT (migración 0016)
- Se convirtieron todas las FKs a user de INT a BIGINT (migración 0024)
- Sin embargo, Django seguía queriendo crear constraints reales
- MariaDB rechaza constraints cuando hay problemas de tipos o referencias
- La solución es usar `db_constraint=False` para evitar constraints de BD

## ⚠️ Importante

**NO ejecutar `makemigrations` en el servidor de producción**

Las migraciones se deben generar y probar en desarrollo, luego:
1. Commit a Git
2. Push a GitHub
3. Pull en producción
4. Migrate en producción

Ejecutar `makemigrations` en producción puede generar migraciones incorrectas o inconsistentes con el código.

## 📞 Si Algo Falla

Si los pasos anteriores no funcionan:

1. **Revisar logs detallados:**
   ```bash
   sudo journalctl -u gunicorn -n 100 --no-pager
   ```

2. **Verificar estado de la base de datos:**
   ```bash
   uv run python manage.py showmigrations
   ```

3. **Probar conexión a la base de datos:**
   ```bash
   uv run python manage.py dbshell
   ```

4. **Rollback de emergencia:**
   Si nada funciona, contactar al administrador del sistema para hacer rollback de la base de datos al último backup.

---

**Commits de la solución:**  
- 98a2380: Agregar db_constraint=False a todos los ForeignKey a user  
- 8b2c390: Corregir error logout y captura de rol en registro

**Fecha:** 2026-01-20  
**Autor:** GitHub Copilot
