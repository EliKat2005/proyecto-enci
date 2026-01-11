# APIs de Machine Learning e Inteligencia Artificial

Esta documentación describe los endpoints REST disponibles para las funcionalidades de ML/AI del sistema ENCI.

## 📚 Documentación Interactiva

Accede a la documentación completa e interactiva:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## 🔑 Autenticación

Todos los endpoints requieren autenticación. Incluye el token de sesión en las peticiones:

```bash
# Usando cookies de sesión Django
curl -X GET http://localhost:8000/api/ml/analytics/metricas/1/ \
  --cookie "sessionid=YOUR_SESSION_ID"

# O usando Django REST Framework Token Authentication
curl -X GET http://localhost:8000/api/ml/analytics/metricas/1/ \
  -H "Authorization: Token YOUR_API_TOKEN"
```

## 📊 Analytics - Análisis Financiero

### 1. Calcular Métricas Financieras

Calcula ratios financieros en tiempo real (liquidez, rentabilidad, endeudamiento, actividad).

```http
GET /api/ml/analytics/metricas/{empresa_id}/
```

**Parámetros de consulta:**
- `fecha_inicio` (opcional): Fecha inicio período (YYYY-MM-DD)
- `fecha_fin` (opcional): Fecha fin período (YYYY-MM-DD)

**Ejemplo:**
```bash
curl -X GET "http://localhost:8000/api/ml/analytics/metricas/1/?fecha_inicio=2024-01-01&fecha_fin=2024-12-31" \
  -H "Authorization: Token YOUR_TOKEN"
```

**Respuesta:**
```json
{
  "empresa": {
    "id": 1,
    "nombre": "Mi Empresa S.A.",
    "ruc": "20123456789"
  },
  "fecha_inicio": "2024-01-01",
  "fecha_fin": "2024-12-31",
  "metricas": {
    "liquidez_corriente": 2.45,
    "liquidez_acida": 1.87,
    "rentabilidad_activos": 0.15,
    "rentabilidad_patrimonio": 0.23,
    "margen_neto": 0.12,
    "endeudamiento_total": 0.35,
    "cobertura_intereses": 4.5,
    "rotacion_activos": 1.25,
    "ciclo_conversion_efectivo": 45
  },
  "interpretacion": {
    "liquidez": "Buena - La empresa puede cubrir sus obligaciones",
    "rentabilidad": "Adecuada - ROA del 15%",
    "endeudamiento": "Bajo - Endeudamiento del 35%"
  }
}
```

### 2. Tendencias de Ingresos y Gastos

Analiza la evolución temporal de ingresos y gastos con promedios móviles.

```http
GET /api/ml/analytics/tendencias/{empresa_id}/
```

**Parámetros:**
- `meses` (opcional, default=12): Número de meses históricos

**Ejemplo:**
```bash
curl -X GET "http://localhost:8000/api/ml/analytics/tendencias/1/?meses=6"
```

**Respuesta:**
```json
{
  "empresa": {...},
  "periodo_meses": 6,
  "tendencias": [
    {
      "mes": "2024-07",
      "ingresos": 125000.50,
      "gastos": 87500.25,
      "margen": 37500.25,
      "margen_porcentaje": 30.0,
      "promedio_movil_ingresos": 118000.00,
      "promedio_movil_gastos": 85000.00
    },
    ...
  ],
  "resumen": {
    "total_ingresos": 750000.00,
    "total_gastos": 525000.00,
    "margen_promedio": 28.5,
    "tendencia_ingresos": "creciente",
    "tendencia_gastos": "estable"
  }
}
```

### 3. Top Cuentas por Movimiento

Ranking de cuentas más activas por número y monto de transacciones.

```http
GET /api/ml/analytics/top-cuentas/{empresa_id}/
```

**Parámetros:**
- `limit` (opcional, default=10): Número de cuentas a retornar
- `fecha_inicio`, `fecha_fin` (opcional): Filtrar por período

**Respuesta:**
```json
{
  "empresa": {...},
  "top_cuentas": [
    {
      "cuenta_codigo": "1011",
      "cuenta_nombre": "Caja General",
      "total_movimientos": 450,
      "total_debe": 1250000.00,
      "total_haber": 1100000.00,
      "saldo_neto": 150000.00,
      "ranking": 1
    },
    ...
  ]
}
```

### 4. Composición Patrimonial

Distribución porcentual de activos, pasivos y patrimonio.

```http
GET /api/ml/analytics/composicion/{empresa_id}/
```

**Parámetros:**
- `fecha` (opcional): Fecha de corte (YYYY-MM-DD)

**Respuesta:**
```json
{
  "empresa": {...},
  "fecha_corte": "2024-12-31",
  "composicion": [
    {
      "tipo": "Activo",
      "subtipo": "Activo Corriente",
      "monto": 500000.00,
      "porcentaje": 35.0
    },
    {
      "tipo": "Activo",
      "subtipo": "Activo No Corriente",
      "monto": 700000.00,
      "porcentaje": 49.0
    },
    ...
  ],
  "totales": {
    "total_activo": 1200000.00,
    "total_pasivo": 420000.00,
    "total_patrimonio": 780000.00
  }
}
```

### 5. Análisis Jerárquico de Cuentas

Estructura de cuentas con saldos agregados por niveles (usando CTEs recursivos).

```http
GET /api/ml/analytics/jerarquico/{empresa_id}/
```

**Parámetros:**
- `nivel_max` (opcional, default=3): Profundidad máxima del árbol

**Respuesta:**
```json
{
  "empresa": {...},
  "nivel_max": 3,
  "jerarquia": [
    {
      "nivel": 1,
      "codigo": "1",
      "nombre": "ACTIVO",
      "saldo": 1200000.00,
      "hijos": [
        {
          "nivel": 2,
          "codigo": "10",
          "nombre": "ACTIVO CORRIENTE",
          "saldo": 500000.00,
          "padre": "1"
        }
      ]
    }
  ]
}
```

## 🔮 Predictions - Predicciones con Prophet

### 1. Generar Predicciones

Crea predicciones financieras usando el modelo Prophet de Facebook.

```http
POST /api/ml/predictions/generar/{empresa_id}/
```

**Body:**
```json
{
  "tipo_prediccion": "INGRESOS",  // INGRESOS, GASTOS, FLUJO_CAJA, UTILIDADES, o null para todas
  "dias_historicos": 90,
  "dias_futuros": 30
}
```

**Tipos de predicción:**
- `INGRESOS`: Predicción de ingresos futuros
- `GASTOS`: Predicción de gastos futuros
- `FLUJO_CAJA`: Predicción de flujo de caja neto
- `UTILIDADES`: Predicción de utilidades (ingresos - gastos)
- `null`: Genera las 4 predicciones

**Respuesta:**
```json
[
  {
    "id": 123,
    "empresa": {...},
    "tipo_prediccion": "INGRESOS",
    "tipo_prediccion_display": "Ingresos",
    "fecha_prediccion": "2025-01-15",
    "valor_predicho": 125000.50,
    "limite_inferior": 115000.00,
    "limite_superior": 135000.00,
    "confianza": 0.95,
    "modelo_usado": "prophet",
    "mae": 5234.12,
    "rmse": 7891.45,
    "mape": 4.2,
    "tendencia": "creciente",
    "dias_historicos": 90,
    "dias_futuros": 30,
    "created_at": "2025-01-01T10:30:00Z"
  }
]
```

### 2. Análisis de Tendencia

Analiza la tendencia de predicciones existentes.

```http
GET /api/ml/predictions/tendencia/{empresa_id}/
```

**Parámetros:**
- `tipo` (requerido): INGRESOS, GASTOS, FLUJO_CAJA, UTILIDADES
- `dias` (opcional, default=30): Días a analizar

**Respuesta:**
```json
{
  "empresa": {...},
  "tipo_prediccion": "INGRESOS",
  "dias_analizados": 30,
  "valores": [125000, 127500, 130000, ...],
  "fechas": ["2025-01-01", "2025-01-02", ...],
  "estadisticas": {
    "promedio": 127500.00,
    "maximo": 135000.00,
    "minimo": 120000.00,
    "desviacion_estandar": 4250.50
  },
  "tendencia": "creciente",
  "cambio_porcentual": 8.5
}
```

### 3. CRUD de Predicciones

Endpoints estándar de Django REST Framework:

- `GET /api/ml/predictions/` - Listar predicciones
- `GET /api/ml/predictions/{id}/` - Obtener detalle
- `POST /api/ml/predictions/` - Crear predicción manual
- `PUT /api/ml/predictions/{id}/` - Actualizar
- `PATCH /api/ml/predictions/{id}/` - Actualización parcial
- `DELETE /api/ml/predictions/{id}/` - Eliminar

## 🧠 Embeddings - Búsqueda Semántica

### 1. Generar Embeddings

Genera vectores de 384 dimensiones para todas las cuentas de una empresa.

```http
POST /api/ml/embeddings/generar/{empresa_id}/
```

**Parámetros:**
- `force` (opcional, default=false): Regenerar embeddings existentes

**Respuesta:**
```json
{
  "success": true,
  "empresa": {...},
  "embeddings_nuevos": 45,
  "embeddings_actualizados": 5,
  "total": 50,
  "tiempo_procesamiento": "2.3s",
  "modelo_usado": "paraphrase-multilingual-MiniLM-L12-v2",
  "dimension": 384
}
```

### 2. Búsqueda Semántica

Busca cuentas similares usando embeddings vectoriales.

```http
POST /api/ml/embeddings/buscar/{empresa_id}/
```

**Body:**
```json
{
  "texto": "gastos de publicidad y marketing",
  "limit": 10,
  "min_similarity": 0.6
}
```

**Respuesta:**
```json
[
  {
    "cuenta": {
      "id": 45,
      "codigo": "6401",
      "nombre": "Gastos de Publicidad"
    },
    "similarity": 0.92,
    "embedding_id": 123
  },
  {
    "cuenta": {
      "id": 46,
      "codigo": "6402",
      "nombre": "Gastos de Marketing Digital"
    },
    "similarity": 0.88,
    "embedding_id": 124
  }
]
```

### 3. Recomendar Cuentas

Recomienda cuentas contables basado en descripción de transacción.

```http
POST /api/ml/embeddings/recomendar/{empresa_id}/
```

**Body:**
```json
{
  "descripcion_transaccion": "Pago de factura de luz del mes de diciembre",
  "top_k": 5
}
```

**Respuesta:**
```json
[
  {
    "cuenta": {
      "id": 67,
      "codigo": "6301",
      "nombre": "Servicios Básicos - Electricidad"
    },
    "similarity": 0.95,
    "embedding_id": 145,
    "razon": "Alta similitud semántica con descripción"
  }
]
```

### 4. Obtener Clusters

Agrupa cuentas automáticamente usando K-means.

```http
GET /api/ml/embeddings/clusters/{empresa_id}/
```

**Parámetros:**
- `n_clusters` (opcional, default=5): Número de clusters

**Respuesta:**
```json
[
  {
    "cluster_id": 0,
    "cluster_nombre": "Gastos Operacionales",
    "cuentas": [
      {
        "id": 45,
        "codigo": "6001",
        "nombre": "Sueldos y Salarios"
      },
      ...
    ],
    "centroid": [0.123, -0.456, ...],  // Vector 384-dim
    "tamaño": 12
  }
]
```

### 5. CRUD de Embeddings

- `GET /api/ml/embeddings/` - Listar embeddings
- `GET /api/ml/embeddings/{id}/` - Obtener detalle
- `DELETE /api/ml/embeddings/{id}/` - Eliminar

## 🚨 Anomalies - Detección de Anomalías

### 1. Detectar Anomalías

Ejecuta detección de anomalías usando Isolation Forest.

```http
POST /api/ml/anomalies/detectar/{empresa_id}/
```

**Body:**
```json
{
  "tipo": "MONTO",  // MONTO, FRECUENCIA, TEMPORAL, PATRON, o null para todos
  "dias_historicos": 90,
  "contamination": 0.1
}
```

**Tipos de anomalía:**
- `MONTO`: Montos atípicos (Isolation Forest)
- `FRECUENCIA`: Frecuencia inusual de transacciones
- `TEMPORAL`: Transacciones fuera de horario
- `PATRON`: Patrones contables irregulares
- `null`: Ejecuta todos los tipos

**Respuesta:**
```json
{
  "success": true,
  "empresa": {...},
  "tipo_analizado": "MONTO",
  "dias_historicos": 90,
  "transacciones_analizadas": 1250,
  "anomalias_detectadas": 23,
  "por_severidad": {
    "CRITICA": 3,
    "ALTA": 8,
    "MEDIA": 10,
    "BAJA": 2
  },
  "tiempo_procesamiento": "1.2s",
  "modelo_usado": "isolation_forest"
}
```

### 2. Estadísticas de Anomalías

Obtiene resumen estadístico de anomalías detectadas.

```http
GET /api/ml/anomalies/estadisticas/{empresa_id}/
```

**Respuesta:**
```json
{
  "empresa": {...},
  "total_anomalias": 45,
  "sin_revisar": 23,
  "revisadas": 22,
  "falsos_positivos": 8,
  "por_tipo": {
    "MONTO": 15,
    "FRECUENCIA": 12,
    "TEMPORAL": 10,
    "PATRON": 8
  },
  "por_severidad": {
    "CRITICA": 5,
    "ALTA": 12,
    "MEDIA": 18,
    "BAJA": 10
  },
  "recientes": [
    {
      "id": 123,
      "tipo": "MONTO",
      "severidad": "ALTA",
      "score": 0.85,
      "descripcion": "Monto atípico detectado",
      "created_at": "2025-01-01T10:30:00Z"
    }
  ],
  "tasa_falsos_positivos": 0.18
}
```

### 3. Revisar Anomalía

Marca una anomalía como revisada.

```http
POST /api/ml/anomalies/{id}/revisar/
```

**Body:**
```json
{
  "es_falso_positivo": true,
  "notas": "Transacción legítima - compra de activo fijo"
}
```

**Respuesta:**
```json
{
  "id": 123,
  "tipo": "MONTO",
  "severidad": "ALTA",
  "score": 0.85,
  "revisada": true,
  "es_falso_positivo": true,
  "notas_revision": "Transacción legítima - compra de activo fijo",
  "revisada_por": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com"
  },
  "revisada_en": "2025-01-01T11:00:00Z"
}
```

### 4. CRUD de Anomalías

- `GET /api/ml/anomalies/` - Listar anomalías (con filtros)
- `GET /api/ml/anomalies/{id}/` - Obtener detalle
- `DELETE /api/ml/anomalies/{id}/` - Eliminar

**Filtros disponibles:**
- `tipo`: MONTO, FRECUENCIA, TEMPORAL, PATRON
- `severidad`: BAJA, MEDIA, ALTA, CRITICA
- `revisada`: true/false
- `es_falso_positivo`: true/false

**Ejemplo:**
```bash
curl -X GET "http://localhost:8000/api/ml/anomalies/?tipo=MONTO&severidad=ALTA&revisada=false"
```

## 🧪 Ejemplos de Uso Completo

### Flujo 1: Análisis Financiero Completo

```bash
# 1. Calcular métricas actuales
curl -X GET "http://localhost:8000/api/ml/analytics/metricas/1/"

# 2. Ver tendencias de los últimos 12 meses
curl -X GET "http://localhost:8000/api/ml/analytics/tendencias/1/?meses=12"

# 3. Identificar cuentas más activas
curl -X GET "http://localhost:8000/api/ml/analytics/top-cuentas/1/?limit=20"

# 4. Analizar composición patrimonial
curl -X GET "http://localhost:8000/api/ml/analytics/composicion/1/"
```

### Flujo 2: Predicciones Financieras

```bash
# 1. Generar predicciones de ingresos
curl -X POST "http://localhost:8000/api/ml/predictions/generar/1/" \
  -H "Content-Type: application/json" \
  -d '{"tipo_prediccion": "INGRESOS", "dias_historicos": 90, "dias_futuros": 30}'

# 2. Analizar tendencia
curl -X GET "http://localhost:8000/api/ml/predictions/tendencia/1/?tipo=INGRESOS&dias=30"

# 3. Listar todas las predicciones
curl -X GET "http://localhost:8000/api/ml/predictions/?empresa=1&tipo_prediccion=INGRESOS"
```

### Flujo 3: Búsqueda Semántica

```bash
# 1. Generar embeddings (primera vez)
curl -X POST "http://localhost:8000/api/ml/embeddings/generar/1/"

# 2. Buscar cuentas similares
curl -X POST "http://localhost:8000/api/ml/embeddings/buscar/1/" \
  -H "Content-Type: application/json" \
  -d '{"texto": "gastos de oficina", "limit": 5}'

# 3. Obtener recomendaciones
curl -X POST "http://localhost:8000/api/ml/embeddings/recomendar/1/" \
  -H "Content-Type: application/json" \
  -d '{"descripcion_transaccion": "Pago de factura de internet"}'

# 4. Visualizar clusters
curl -X GET "http://localhost:8000/api/ml/embeddings/clusters/1/?n_clusters=8"
```

### Flujo 4: Detección y Gestión de Anomalías

```bash
# 1. Detectar todas las anomalías
curl -X POST "http://localhost:8000/api/ml/anomalies/detectar/1/" \
  -H "Content-Type: application/json" \
  -d '{"dias_historicos": 90}'

# 2. Ver estadísticas
curl -X GET "http://localhost:8000/api/ml/anomalies/estadisticas/1/"

# 3. Listar anomalías críticas sin revisar
curl -X GET "http://localhost:8000/api/ml/anomalies/?empresa=1&severidad=CRITICA&revisada=false"

# 4. Revisar una anomalía
curl -X POST "http://localhost:8000/api/ml/anomalies/123/revisar/" \
  -H "Content-Type: application/json" \
  -d '{"es_falso_positivo": false, "notas": "Anomalía confirmada - requiere investigación"}'
```

## 📊 Códigos de Estado HTTP

- `200 OK`: Operación exitosa
- `201 Created`: Recurso creado exitosamente
- `400 Bad Request`: Error de validación o parámetros incorrectos
- `401 Unauthorized`: No autenticado
- `403 Forbidden`: No tiene permisos para acceder
- `404 Not Found`: Recurso no encontrado
- `500 Internal Server Error`: Error del servidor

## 🔒 Permisos y Seguridad

- Todos los endpoints requieren autenticación (`IsAuthenticated`)
- Los usuarios solo pueden acceder a datos de empresas de su grupo
- Las anomalías marcadas como revisadas incluyen información del usuario que las revisó
- Los embeddings y predicciones están vinculados a empresas específicas

## 🚀 Mejores Prácticas

1. **Generar embeddings una vez**: Los embeddings son costosos, genéralos solo cuando cambien las cuentas
2. **Usar filtros**: Aprovecha los filtros en los endpoints de listado para reducir carga
3. **Cachear predicciones**: Las predicciones son válidas por períodos de tiempo
4. **Revisar anomalías regularmente**: Mantén un flujo de revisión constante
5. **Monitorear métricas**: Usa los endpoints de analytics periódicamente para dashboards

## 📝 Notas Técnicas

- **Embeddings**: Modelo `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones)
- **Predicciones**: Facebook Prophet con estacionalidad yearly, weekly, daily
- **Anomalías**: Isolation Forest con `contamination=0.1` por defecto
- **Analytics**: SQL optimizado con CTEs recursivos y Window Functions

## 🐛 Troubleshooting

### Error: "No embeddings found"
```bash
# Solución: Generar embeddings primero
curl -X POST "http://localhost:8000/api/ml/embeddings/generar/1/"
```

### Error: "Not enough historical data"
```bash
# Solución: Reducir días históricos o agregar más transacciones
curl -X POST ".../predictions/generar/1/" \
  -d '{"dias_historicos": 30, "dias_futuros": 7}'
```

### Error: "Contamination must be between 0 and 1"
```bash
# Solución: Usar valor válido (0.05 - 0.2 recomendado)
curl -X POST ".../anomalies/detectar/1/" \
  -d '{"contamination": 0.1}'
```

## 📚 Recursos Adicionales

- [Documentación de Prophet](https://facebook.github.io/prophet/)
- [Sentence Transformers](https://www.sbert.net/)
- [Isolation Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [drf-spectacular](https://drf-spectacular.readthedocs.io/)
