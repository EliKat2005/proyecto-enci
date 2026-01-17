# 🎯 Quick Wins Activados - Guía de Uso

## ✅ Implementación Completada

Se han activado los Quick Wins identificados en el análisis del proyecto:

### 1. **Seguridad**
- ✅ Rate Limiting (Throttling)
- ✅ Permisos Granulares
- ✅ Security Headers

### 2. **Monitoring & Observability**
- ✅ Performance Monitoring
- ✅ Auditoría de Acciones
- ✅ Logging Profesional
- ✅ Request ID Tracing

### 3. **Infraestructura**
- ✅ Sentry (configuración lista, requiere DSN)
- ✅ Rotación de Logs
- ✅ Múltiples Handlers

---

## 📦 Dependencias Instaladas

```bash
# Ya instaladas con uv
✅ sentry-sdk==2.49.0
✅ python-json-logger==4.0.0
```

---

## 🔧 Configuración Aplicada

### **1. Middleware (config/settings.py)**

Se agregaron 4 middleware en orden correcto:

```python
MIDDLEWARE = [
    # ... middleware estándar de Django ...
    "contabilidad.middleware.RequestIDMiddleware",           # UUID para cada request
    "contabilidad.middleware.PerformanceMonitoringMiddleware",  # Monitorea requests lentos
    "contabilidad.middleware.AuditLoggingMiddleware",        # Auditoría de acciones críticas
    "contabilidad.middleware.SecurityHeadersMiddleware",     # Headers de seguridad
]
```

**Funcionalidades:**
- `RequestIDMiddleware`: Genera UUID único para cada request y lo agrega a los headers (`X-Request-ID`)
- `PerformanceMonitoringMiddleware`:
  - Mide tiempo de respuesta
  - Loguea requests que tardan >1 segundo
  - Agrega header `X-Response-Time` (en milisegundos)
- `AuditLoggingMiddleware`:
  - Loguea POST/PUT/PATCH/DELETE
  - Incluye usuario, IP, empresa_id, path
  - Formato JSON estructurado
- `SecurityHeadersMiddleware`:
  - X-Frame-Options: DENY
  - X-Content-Type-Options: nosniff
  - X-XSS-Protection: 1; mode=block
  - Referrer-Policy: strict-origin-when-cross-origin
  - Permissions-Policy: geolocation=(), microphone=()

### **2. Throttling (Rate Limiting)**

Configuración en `REST_FRAMEWORK`:

```python
"DEFAULT_THROTTLE_RATES": {
    "anon": "100/hour",      # Usuarios anónimos
    "user": "1000/hour",     # Usuarios autenticados
    "ml_api": "500/hour",    # APIs ML generales
    "heavy_ml": "100/hour",  # APIs ML pesadas
    "embedding": "200/day",  # Generación de embeddings
    "prediction": "50/day",  # Predicciones con Prophet
}
```

**Aplicado a:**
- ✅ `AnalyticsViewSet` → MLAPIThrottle (500/hora)
- ✅ `PredictionsViewSet` → PredictionThrottle (50/día)
- ✅ `EmbeddingsViewSet` → EmbeddingThrottle (200/día)
- ✅ `AnomaliesViewSet` → MLAPIThrottle (500/hora)
- ✅ `AdvancedMLViewSet` → MLAPIThrottle + HeavyMLThrottle (100/hora para operaciones pesadas)

### **3. Permissions (Autorización Granular)**

Aplicado `IsEmpresaOwnerOrSupervisor` a todos los ViewSets de ML:

**Lógica:**
- **Propietario (owner)**: Lectura y escritura completa
- **Supervisor con acceso**: Solo lectura (GET, HEAD, OPTIONS)
- **Sin acceso**: 403 Forbidden

### **4. Logging Profesional**

**Loggers configurados:**
1. `django` → logs/django.log (10MB, 5 archivos)
2. `django.request` → logs/error.log (10MB, 5 archivos)
3. `audit` → logs/audit.log (50MB, 10 archivos, JSON)
4. `performance` → logs/performance.log (10MB, 5 archivos)
5. `ml` → logs/ml.log (20MB, 5 archivos)
6. `contabilidad` → logs/contabilidad.log (20MB, 5 archivos)
7. `core` → logs/core.log (20MB, 5 archivos)

**Ubicación:** `/mnt/universidad/Base de Datos II/proyecto-enci/logs/`

**Rotación automática:** Cuando un archivo alcanza su tamaño máximo, se renombra y se crea uno nuevo.

---

## 🚀 Uso y Testing

### **1. Verificar Middleware**

#### Test de Request ID
```bash
# Hacer una request y verificar el header X-Request-ID
curl -I http://localhost:8000/api/empresas/ -H "Authorization: Token YOUR_TOKEN"

# Buscar en los logs el request_id
grep "request_id" logs/django.log
```

#### Test de Performance Monitoring
```bash
# Hacer una request lenta (predicciones, embeddings)
curl -X POST http://localhost:8000/api/ml/predictions/generar/1/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tipo_prediccion": "TODOS", "dias_historicos": 180, "dias_futuros": 60}'

# Verificar el header X-Response-Time
# Buscar en logs/performance.log requests >1s
tail -f logs/performance.log
```

#### Test de Auditoría
```bash
# Crear una transacción (POST)
curl -X POST http://localhost:8000/api/empresas/1/transacciones/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fecha": "2026-01-17", "cuenta_debe": 1, "cuenta_haber": 2, "monto": 100.00, "concepto": "Test"}'

# Verificar en logs/audit.log
tail -f logs/audit.log | jq .
```

#### Test de Security Headers
```bash
# Verificar headers de seguridad
curl -I http://localhost:8000/

# Deberías ver:
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Referrer-Policy: strict-origin-when-cross-origin
```

### **2. Verificar Throttling (Rate Limiting)**

#### Test de ML API Throttle
```bash
# Script para hacer 510 requests rápidas (debería fallar después de 500)
for i in {1..510}; do
  curl -s http://localhost:8000/api/ml/analytics/metricas/1/ \
    -H "Authorization: Token YOUR_TOKEN" \
    | jq -r '.detail // "OK"'

  if [ $i -eq 501 ]; then
    echo "Request #501 debería fallar con throttle..."
  fi
done
```

**Respuesta esperada después del límite:**
```json
{
  "detail": "Request was throttled. Expected available in 3600 seconds."
}
```

#### Test de Prediction Throttle (50/día)
```bash
# 51 predicciones en un día (debería fallar en la #51)
for i in {1..51}; do
  echo "Predicción #$i"
  curl -X POST http://localhost:8000/api/ml/predictions/generar/1/ \
    -H "Authorization: Token YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"tipo_prediccion": "INGRESOS", "dias_historicos": 90, "dias_futuros": 30}' \
    | jq -r '.detail // "Generada"'
done
```

#### Test de Embedding Throttle (200/día)
```bash
# 201 generaciones de embeddings (debería fallar en la #201)
for i in {1..201}; do
  echo "Embedding #$i"
  curl -X POST http://localhost:8000/api/ml/embeddings/generar/1/ \
    -H "Authorization: Token YOUR_TOKEN" | jq -r '.detail // "OK"'
done
```

### **3. Verificar Permissions**

#### Test de Owner (Full Access)
```bash
# Como owner, debería poder hacer POST/PUT/DELETE
curl -X POST http://localhost:8000/api/ml/anomalies/detectar/1/ \
  -H "Authorization: Token OWNER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"metodos": ["isolation_forest"], "dias_analizar": 90}'
```

#### Test de Supervisor (Read Only)
```bash
# Como supervisor, GET debería funcionar
curl http://localhost:8000/api/ml/analytics/metricas/1/ \
  -H "Authorization: Token SUPERVISOR_TOKEN"

# Pero POST debería fallar con 403
curl -X POST http://localhost:8000/api/ml/anomalies/detectar/1/ \
  -H "Authorization: Token SUPERVISOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"metodos": ["isolation_forest"], "dias_analizar": 90}'

# Respuesta esperada:
# {"detail": "No tiene permiso para realizar esta acción."}
```

### **4. Verificar Logging**

#### Ver logs en tiempo real
```bash
# Todos los logs en una sola terminal
tail -f logs/*.log

# Solo errores
tail -f logs/error.log

# Solo auditoría (JSON)
tail -f logs/audit.log | jq .

# Solo performance (requests lentos)
tail -f logs/performance.log

# Solo ML operations
tail -f logs/ml.log
```

#### Análisis de logs
```bash
# Top 10 endpoints más lentos
grep "response_time_ms" logs/performance.log | \
  jq -r '.response_time_ms + " " + .path' | \
  sort -rn | head -10

# Contar requests por usuario
grep "username" logs/audit.log | jq -r '.username' | sort | uniq -c

# Contar acciones por tipo
grep "method" logs/audit.log | jq -r '.method' | sort | uniq -c

# Buscar errores de ML
grep "ERROR" logs/ml.log
```

---

## 🔐 Configuración de Sentry (Opcional)

Para activar Sentry en **producción**:

### 1. Crear cuenta en Sentry.io
- Ir a https://sentry.io
- Crear proyecto Django
- Copiar el DSN

### 2. Configurar variables de entorno (.env)
```bash
# En producción
DEBUG=False
SENTRY_DSN=https://your-key@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### 3. Verificar configuración
```bash
# Django automáticamente inicializa Sentry si DEBUG=False y SENTRY_DSN está presente
uv run python manage.py check --deploy
```

### 4. Test de Sentry
```python
# En Django shell
python manage.py shell

>>> import sentry_sdk
>>> sentry_sdk.capture_message("Test desde Django")
>>> 1/0  # Debería enviar error a Sentry
```

---

## 📊 Métricas de Impacto

### **Antes (sin Quick Wins)**
- ❌ Sin límite de requests (riesgo de abuso)
- ❌ Sin auditoría de acciones críticas
- ❌ Sin monitoreo de performance
- ❌ Sin trazabilidad de requests
- ❌ Sin headers de seguridad
- ❌ Logs básicos sin rotación
- ❌ Sin tracking de errores

### **Después (con Quick Wins)**
- ✅ Rate limiting configurable por tipo de API
- ✅ Auditoría completa en JSON
- ✅ Detección automática de requests lentos
- ✅ Request ID para debugging end-to-end
- ✅ Headers de seguridad (OWASP)
- ✅ 7 loggers especializados con rotación
- ✅ Sentry listo para producción

---

## 🐛 Troubleshooting

### **Logs no se crean**
```bash
# Verificar que el directorio existe y tiene permisos
ls -la logs/
mkdir -p logs/
chmod 755 logs/
```

### **Throttling muy agresivo**
```bash
# Ajustar en config/settings.py
"DEFAULT_THROTTLE_RATES": {
    "ml_api": "1000/hour",  # Aumentar límite
}
```

### **Sentry no envía errores**
```bash
# Verificar que DEBUG=False
echo $DEBUG

# Verificar que SENTRY_DSN está configurado
echo $SENTRY_DSN

# Test manual
python manage.py shell
>>> import sentry_sdk
>>> sentry_sdk.capture_message("Test")
```

### **Headers de seguridad causan problemas con iframe**
```python
# En contabilidad/middleware.py
# Cambiar X-Frame-Options si necesitas embeds
response["X-Frame-Options"] = "SAMEORIGIN"  # En lugar de DENY
```

---

## 📚 Referencias

- [contabilidad/throttling.py](../contabilidad/throttling.py) - Clases de rate limiting
- [contabilidad/permissions.py](../contabilidad/permissions.py) - Permisos granulares
- [contabilidad/middleware.py](../contabilidad/middleware.py) - Middleware de monitoring
- [config/logging_config.py](../config/logging_config.py) - Configuración de logging
- [docs/OPORTUNIDADES_MEJORA.md](./OPORTUNIDADES_MEJORA.md) - Análisis completo del proyecto

---

## ✅ Checklist de Verificación

- [x] Dependencias instaladas (sentry-sdk, python-json-logger)
- [x] Middleware agregado a MIDDLEWARE
- [x] Throttling configurado en REST_FRAMEWORK
- [x] Permissions aplicados a ViewSets
- [x] Logging configurado
- [x] Variables de entorno documentadas (.env)
- [x] Django check pasa sin errores críticos
- [ ] Tests manuales de throttling
- [ ] Tests manuales de permissions
- [ ] Tests manuales de auditoría
- [ ] Configuración de Sentry en producción

---

**¡Quick Wins activados y listos para usar!** 🎉
