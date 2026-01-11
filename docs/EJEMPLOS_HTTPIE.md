# Ejemplos de Uso de las APIs de ML/AI con HTTPie

Este archivo contiene ejemplos prácticos usando HTTPie para probar todos los endpoints de ML/AI.

## Instalación de HTTPie

```bash
# Con pip
pip install httpie

# Con apt (Ubuntu/Debian)
sudo apt install httpie

# Con brew (macOS)
brew install httpie
```

## Configuración Inicial

### 1. Iniciar el servidor
```bash
python manage.py runserver
```

### 2. Iniciar sesión (obtener session cookie)
```bash
# Método 1: Iniciar sesión desde el navegador
# Abre http://localhost:8000/admin/ y inicia sesión
# Luego exporta la cookie de sesión:
export SESSION_ID="tu_session_id_aqui"

# Método 2: Usar el script de Python
python scripts/test_ml_apis.py
```

### 3. Usar las APIs con la sesión
```bash
# Todas las peticiones incluyen la cookie de sesión
http GET :8000/api/ml/analytics/metricas/1/ \
  "Cookie:sessionid=$SESSION_ID"
```

---

## 📊 ANALYTICS - Análisis Financiero

### Calcular Métricas Financieras
```bash
# Sin filtros de fecha (todo el historial)
http GET :8000/api/ml/analytics/metricas/1/ \
  "Cookie:sessionid=$SESSION_ID"

# Con rango de fechas
http GET :8000/api/ml/analytics/metricas/1/ \
  fecha_inicio==2024-01-01 \
  fecha_fin==2024-12-31 \
  "Cookie:sessionid=$SESSION_ID"

# Respuesta esperada:
# {
#     "empresa": {...},
#     "metricas": {
#         "liquidez_corriente": 2.45,
#         "rentabilidad_activos": 0.15,
#         ...
#     }
# }
```

### Tendencias de Ingresos y Gastos
```bash
# Últimos 12 meses (default)
http GET :8000/api/ml/analytics/tendencias/1/ \
  "Cookie:sessionid=$SESSION_ID"

# Últimos 6 meses
http GET :8000/api/ml/analytics/tendencias/1/ \
  meses==6 \
  "Cookie:sessionid=$SESSION_ID"

# Respuesta: Lista de tendencias mensuales con promedios móviles
```

### Top Cuentas por Movimiento
```bash
# Top 10 cuentas (default)
http GET :8000/api/ml/analytics/top-cuentas/1/ \
  "Cookie:sessionid=$SESSION_ID"

# Top 20 cuentas con rango de fechas
http GET :8000/api/ml/analytics/top-cuentas/1/ \
  limit==20 \
  fecha_inicio==2024-01-01 \
  fecha_fin==2024-12-31 \
  "Cookie:sessionid=$SESSION_ID"

# Respuesta: Ranking de cuentas con total de movimientos y saldos
```

### Composición Patrimonial
```bash
# Composición actual
http GET :8000/api/ml/analytics/composicion/1/ \
  "Cookie:sessionid=$SESSION_ID"

# Composición a una fecha específica
http GET :8000/api/ml/analytics/composicion/1/ \
  fecha==2024-12-31 \
  "Cookie:sessionid=$SESSION_ID"

# Respuesta: Distribución porcentual de activos, pasivos y patrimonio
```

### Análisis Jerárquico de Cuentas
```bash
# Profundidad 3 niveles (default)
http GET :8000/api/ml/analytics/jerarquico/1/ \
  "Cookie:sessionid=$SESSION_ID"

# Profundidad 5 niveles
http GET :8000/api/ml/analytics/jerarquico/1/ \
  nivel_max==5 \
  "Cookie:sessionid=$SESSION_ID"

# Respuesta: Árbol jerárquico de cuentas con saldos agregados
```

---

## 🧠 EMBEDDINGS - Búsqueda Semántica

### Generar Embeddings
```bash
# Generar embeddings (solo cuentas nuevas)
http POST :8000/api/ml/embeddings/generar/1/ \
  "Cookie:sessionid=$SESSION_ID"

# Regenerar todos los embeddings (force=true)
http POST :8000/api/ml/embeddings/generar/1/ \
  force:=true \
  "Cookie:sessionid=$SESSION_ID"

# Respuesta:
# {
#     "success": true,
#     "embeddings_nuevos": 45,
#     "embeddings_actualizados": 5,
#     "total": 50,
#     "modelo_usado": "paraphrase-multilingual-MiniLM-L12-v2"
# }
```

### Búsqueda Semántica
```bash
# Buscar cuentas similares a un texto
http POST :8000/api/ml/embeddings/buscar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  texto="gastos de publicidad y marketing" \
  limit:=10 \
  min_similarity:=0.6

# Respuesta: Lista de cuentas ordenadas por similitud
# [
#     {
#         "cuenta": {"codigo": "6401", "nombre": "Gastos de Publicidad"},
#         "similarity": 0.92
#     },
#     ...
# ]
```

### Recomendar Cuentas
```bash
# Recomendar cuentas para una transacción
http POST :8000/api/ml/embeddings/recomendar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  descripcion_transaccion="Pago de factura de luz" \
  top_k:=5

# Respuesta: Top 5 cuentas recomendadas
```

### Obtener Clusters
```bash
# 5 clusters (default)
http GET :8000/api/ml/embeddings/clusters/1/ \
  "Cookie:sessionid=$SESSION_ID"

# 8 clusters personalizados
http GET :8000/api/ml/embeddings/clusters/1/ \
  n_clusters==8 \
  "Cookie:sessionid=$SESSION_ID"

# Respuesta: Clusters con cuentas agrupadas
```

### Listar Embeddings
```bash
# Listar todos los embeddings de la empresa
http GET :8000/api/ml/embeddings/ \
  empresa==1 \
  "Cookie:sessionid=$SESSION_ID"

# Ver detalle de un embedding
http GET :8000/api/ml/embeddings/123/ \
  "Cookie:sessionid=$SESSION_ID"
```

---

## 🔮 PREDICTIONS - Predicciones Financieras

### Generar Predicciones
```bash
# Generar predicción de INGRESOS
http POST :8000/api/ml/predictions/generar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  tipo_prediccion="INGRESOS" \
  dias_historicos:=90 \
  dias_futuros:=30

# Generar predicción de GASTOS
http POST :8000/api/ml/predictions/generar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  tipo_prediccion="GASTOS" \
  dias_historicos:=60 \
  dias_futuros:=15

# Generar predicción de FLUJO_CAJA
http POST :8000/api/ml/predictions/generar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  tipo_prediccion="FLUJO_CAJA" \
  dias_historicos:=90 \
  dias_futuros:=30

# Generar predicción de UTILIDADES
http POST :8000/api/ml/predictions/generar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  tipo_prediccion="UTILIDADES" \
  dias_historicos:=120 \
  dias_futuros:=60

# Generar TODAS las predicciones (no enviar tipo_prediccion)
http POST :8000/api/ml/predictions/generar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  dias_historicos:=90 \
  dias_futuros:=30

# Respuesta:
# [
#     {
#         "tipo_prediccion": "INGRESOS",
#         "fecha_prediccion": "2025-01-15",
#         "valor_predicho": 125000.50,
#         "limite_inferior": 115000.00,
#         "limite_superior": 135000.00,
#         "confianza": 0.95,
#         "mae": 5234.12,
#         "tendencia": "creciente"
#     },
#     ...
# ]
```

### Análisis de Tendencia
```bash
# Tendencia de ingresos (30 días)
http GET :8000/api/ml/predictions/tendencia/1/ \
  tipo==INGRESOS \
  dias==30 \
  "Cookie:sessionid=$SESSION_ID"

# Tendencia de gastos (15 días)
http GET :8000/api/ml/predictions/tendencia/1/ \
  tipo==GASTOS \
  dias==15 \
  "Cookie:sessionid=$SESSION_ID"

# Respuesta:
# {
#     "valores": [125000, 127500, ...],
#     "fechas": ["2025-01-01", ...],
#     "tendencia": "creciente",
#     "cambio_porcentual": 8.5
# }
```

### Listar y Gestionar Predicciones
```bash
# Listar todas las predicciones
http GET :8000/api/ml/predictions/ \
  "Cookie:sessionid=$SESSION_ID"

# Filtrar por empresa y tipo
http GET :8000/api/ml/predictions/ \
  empresa==1 \
  tipo_prediccion==INGRESOS \
  "Cookie:sessionid=$SESSION_ID"

# Ver detalle de una predicción
http GET :8000/api/ml/predictions/123/ \
  "Cookie:sessionid=$SESSION_ID"

# Eliminar predicción
http DELETE :8000/api/ml/predictions/123/ \
  "Cookie:sessionid=$SESSION_ID"
```

---

## 🚨 ANOMALIES - Detección de Anomalías

### Detectar Anomalías
```bash
# Detectar anomalías de MONTO
http POST :8000/api/ml/anomalies/detectar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  tipo="MONTO" \
  dias_historicos:=90 \
  contamination:=0.1

# Detectar anomalías de FRECUENCIA
http POST :8000/api/ml/anomalies/detectar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  tipo="FRECUENCIA" \
  dias_historicos:=60

# Detectar anomalías TEMPORALES
http POST :8000/api/ml/anomalies/detectar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  tipo="TEMPORAL" \
  dias_historicos:=30

# Detectar anomalías de PATRON
http POST :8000/api/ml/anomalies/detectar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  tipo="PATRON" \
  dias_historicos:=90

# Detectar TODAS las anomalías (no enviar tipo)
http POST :8000/api/ml/anomalies/detectar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  dias_historicos:=90 \
  contamination:=0.1

# Respuesta:
# {
#     "success": true,
#     "anomalias_detectadas": 23,
#     "por_severidad": {
#         "CRITICA": 3,
#         "ALTA": 8,
#         "MEDIA": 10,
#         "BAJA": 2
#     }
# }
```

### Estadísticas de Anomalías
```bash
# Obtener estadísticas generales
http GET :8000/api/ml/anomalies/estadisticas/1/ \
  "Cookie:sessionid=$SESSION_ID"

# Respuesta:
# {
#     "total_anomalias": 45,
#     "sin_revisar": 23,
#     "revisadas": 22,
#     "falsos_positivos": 8,
#     "por_tipo": {...},
#     "por_severidad": {...},
#     "tasa_falsos_positivos": 0.18
# }
```

### Listar y Filtrar Anomalías
```bash
# Listar todas las anomalías
http GET :8000/api/ml/anomalies/ \
  "Cookie:sessionid=$SESSION_ID"

# Filtrar por tipo
http GET :8000/api/ml/anomalies/ \
  tipo==MONTO \
  "Cookie:sessionid=$SESSION_ID"

# Filtrar por severidad
http GET :8000/api/ml/anomalies/ \
  severidad==ALTA \
  "Cookie:sessionid=$SESSION_ID"

# Filtrar sin revisar
http GET :8000/api/ml/anomalies/ \
  revisada==false \
  "Cookie:sessionid=$SESSION_ID"

# Combinación de filtros
http GET :8000/api/ml/anomalies/ \
  empresa==1 \
  tipo==MONTO \
  severidad==CRITICA \
  revisada==false \
  "Cookie:sessionid=$SESSION_ID"

# Ver detalle de una anomalía
http GET :8000/api/ml/anomalies/123/ \
  "Cookie:sessionid=$SESSION_ID"
```

### Revisar Anomalías
```bash
# Marcar como revisada (legítima)
http POST :8000/api/ml/anomalies/123/revisar/ \
  "Cookie:sessionid=$SESSION_ID" \
  es_falso_positivo:=false \
  notas="Anomalía confirmada - requiere investigación"

# Marcar como falso positivo
http POST :8000/api/ml/anomalies/456/revisar/ \
  "Cookie:sessionid=$SESSION_ID" \
  es_falso_positivo:=true \
  notas="Transacción legítima - compra de activo fijo"

# Respuesta:
# {
#     "id": 123,
#     "revisada": true,
#     "es_falso_positivo": false,
#     "notas_revision": "...",
#     "revisada_por": {...}
# }
```

---

## 📚 DOCUMENTACIÓN

### Ver Schema OpenAPI
```bash
# Descargar schema JSON
http GET :8000/api/schema/ > api_schema.json

# Ver en formato YAML
http GET :8000/api/schema/ Accept:application/yaml > api_schema.yaml
```

### Acceder a Swagger UI
```bash
# Abrir en navegador
open http://localhost:8000/api/docs/

# O con xdg-open en Linux
xdg-open http://localhost:8000/api/docs/
```

### Acceder a ReDoc
```bash
# Abrir en navegador
open http://localhost:8000/api/redoc/

# O con xdg-open en Linux
xdg-open http://localhost:8000/api/redoc/
```

---

## 🔄 FLUJOS COMPLETOS

### Flujo 1: Análisis Financiero Completo
```bash
# 1. Métricas actuales
http GET :8000/api/ml/analytics/metricas/1/ \
  "Cookie:sessionid=$SESSION_ID"

# 2. Tendencias del año
http GET :8000/api/ml/analytics/tendencias/1/ \
  meses==12 \
  "Cookie:sessionid=$SESSION_ID"

# 3. Top 20 cuentas
http GET :8000/api/ml/analytics/top-cuentas/1/ \
  limit==20 \
  "Cookie:sessionid=$SESSION_ID"

# 4. Composición patrimonial
http GET :8000/api/ml/analytics/composicion/1/ \
  "Cookie:sessionid=$SESSION_ID"

# 5. Análisis jerárquico
http GET :8000/api/ml/analytics/jerarquico/1/ \
  nivel_max==3 \
  "Cookie:sessionid=$SESSION_ID"
```

### Flujo 2: Predicciones y Tendencias
```bash
# 1. Generar predicciones de ingresos
http POST :8000/api/ml/predictions/generar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  tipo_prediccion="INGRESOS" \
  dias_historicos:=90 \
  dias_futuros:=30

# 2. Analizar tendencia
http GET :8000/api/ml/predictions/tendencia/1/ \
  tipo==INGRESOS \
  dias==30 \
  "Cookie:sessionid=$SESSION_ID"

# 3. Listar todas las predicciones
http GET :8000/api/ml/predictions/ \
  empresa==1 \
  "Cookie:sessionid=$SESSION_ID"
```

### Flujo 3: Búsqueda Semántica
```bash
# 1. Generar embeddings
http POST :8000/api/ml/embeddings/generar/1/ \
  "Cookie:sessionid=$SESSION_ID"

# 2. Buscar cuentas similares
http POST :8000/api/ml/embeddings/buscar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  texto="gastos administrativos" \
  limit:=10

# 3. Recomendar cuentas
http POST :8000/api/ml/embeddings/recomendar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  descripcion_transaccion="Pago de alquiler de oficina"

# 4. Ver clusters
http GET :8000/api/ml/embeddings/clusters/1/ \
  n_clusters==8 \
  "Cookie:sessionid=$SESSION_ID"
```

### Flujo 4: Detección y Gestión de Anomalías
```bash
# 1. Detectar todas las anomalías
http POST :8000/api/ml/anomalies/detectar/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  dias_historicos:=90

# 2. Ver estadísticas
http GET :8000/api/ml/anomalies/estadisticas/1/ \
  "Cookie:sessionid=$SESSION_ID"

# 3. Listar anomalías críticas sin revisar
http GET :8000/api/ml/anomalies/ \
  empresa==1 \
  severidad==CRITICA \
  revisada==false \
  "Cookie:sessionid=$SESSION_ID"

# 4. Revisar una anomalía
http POST :8000/api/ml/anomalies/123/revisar/ \
  "Cookie:sessionid=$SESSION_ID" \
  es_falso_positivo:=false \
  notas="Anomalía confirmada"
```

---

## 💡 Tips y Trucos

### Usar archivo de configuración HTTPie
```bash
# Crear ~/.httpie/config.json
{
    "default_options": [
        "--session=enci-session",
        "--print=HhBb"
    ]
}
```

### Guardar sesión
```bash
# Primera petición guarda la sesión
http --session=enci :8000/admin/login/ \
  username=admin password=admin

# Siguientes peticiones usan la sesión guardada
http --session=enci GET :8000/api/ml/analytics/metricas/1/
```

### Formatear JSON de salida
```bash
# Usar jq para formatear
http GET :8000/api/ml/analytics/metricas/1/ | jq '.'

# Extraer solo las métricas
http GET :8000/api/ml/analytics/metricas/1/ | jq '.metricas'

# Contar anomalías detectadas
http POST :8000/api/ml/anomalies/detectar/1/ | jq '.anomalias_detectadas'
```

### Variables de entorno
```bash
# Definir URL base y session
export API_BASE="http://localhost:8000"
export SESSION_ID="tu_session_id"

# Usar en peticiones
http GET $API_BASE/api/ml/analytics/metricas/1/ \
  "Cookie:sessionid=$SESSION_ID"
```

---

## 🐛 Troubleshooting

### Error 401 Unauthorized
```bash
# Solución: Obtener nueva sesión
http POST :8000/admin/login/ \
  username=admin password=admin

# O verificar que la cookie sea válida
http GET :8000/api/ml/analytics/metricas/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  --verbose
```

### Error 403 Forbidden
```bash
# Verificar que el usuario pertenezca al grupo de la empresa
# Solución: Cambiar a otra empresa o agregar usuario al grupo
```

### Error 404 Not Found
```bash
# Verificar que la URL esté correcta
# Verificar que el ID de empresa exista
http GET :8000/api/empresas/ | jq '.[].id'
```

### Error 400 Bad Request
```bash
# Ver detalle del error
http POST :8000/api/ml/predictions/generar/1/ \
  tipo_prediccion="INVALID" \
  --verbose

# Revisar documentación de parámetros
open http://localhost:8000/api/docs/
```

---

## 📊 Exportar Resultados

### Guardar respuestas en archivos
```bash
# Guardar métricas
http GET :8000/api/ml/analytics/metricas/1/ \
  "Cookie:sessionid=$SESSION_ID" \
  > metricas.json

# Guardar predicciones
http POST :8000/api/ml/predictions/generar/1/ \
  tipo_prediccion="INGRESOS" \
  dias_historicos:=90 \
  dias_futuros:=30 \
  "Cookie:sessionid=$SESSION_ID" \
  > predicciones_ingresos.json

# Guardar anomalías
http GET :8000/api/ml/anomalies/ \
  empresa==1 \
  severidad==ALTA \
  "Cookie:sessionid=$SESSION_ID" \
  > anomalias_alta.json
```

---

¡Explora la API y aprovecha el poder del Machine Learning en tu sistema contable! 🚀
