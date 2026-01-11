# ENCI - Sistema de Gestión Contable Empresarial

## Descripción

ECAE (Entorno de Contabilidad Académica Empresarial) es una plataforma web educativa diseñada para la enseñanza y práctica de contabilidad empresarial. Permite a docentes crear plantillas de empresas ficticias y a estudiantes practicar con libros contables completos.

## Características Principales

### Para Docentes
- ✅ Crear empresas plantilla con planes de cuentas personalizados
- ✅ Generar códigos de acceso para que estudiantes importen plantillas
- ✅ Supervisar el progreso de estudiantes
- ✅ Agregar comentarios en diferentes secciones (Plan de Cuentas, Libro Diario, Reportes)
- ✅ Activar/desactivar cuentas de estudiantes
- ✅ Dashboard con vista de estudiantes referidos

### Para Estudiantes
- ✅ Crear empresas propias para práctica autónoma
- ✅ Importar plantillas empresariales mediante códigos
- ✅ Gestionar plan de cuentas completo
- ✅ Registrar asientos contables en libro diario
- ✅ Recibir notificaciones cuando docentes comentan
- ✅ Controlar visibilidad de empresas para supervisores

### Sistema de Notificaciones
- ✅ Notificaciones in-app en tiempo real
- ✅ Badge visual de notificaciones no leídas
- ✅ Gestión de notificaciones (marcar como leída, eliminar)

### 🤖 Machine Learning e Inteligencia Artificial (Nuevo)

#### 📊 Analytics & Business Intelligence
- ✅ **Métricas financieras en tiempo real**: Liquidez, rentabilidad, endeudamiento, actividad
- ✅ **Análisis de tendencias**: Evolución de ingresos y gastos con promedios móviles
- ✅ **Top cuentas**: Ranking de cuentas más activas por movimientos
- ✅ **Composición patrimonial**: Distribución porcentual de activos, pasivos y patrimonio
- ✅ **Análisis jerárquico**: Estructura de cuentas con CTEs recursivos de MariaDB

#### 🧠 Embeddings y Búsqueda Semántica
- ✅ **Vectorización de cuentas**: Embeddings de 384 dimensiones con Sentence Transformers
- ✅ **Búsqueda semántica**: Encontrar cuentas similares por significado, no solo por nombre
- ✅ **Clustering automático**: Agrupación de cuentas con K-means
- ✅ **Recomendaciones inteligentes**: Sugerencias de cuentas basadas en descripción de transacciones

#### 🔮 Predicciones con Prophet
- ✅ **Forecasting financiero**: Predicción de Ingresos, Gastos, Flujo de Caja y Utilidades
- ✅ **Análisis de tendencias**: Identificación automática (creciente, decreciente, estable)
- ✅ **Métricas de error**: MAE, RMSE, MAPE para validar precisión
- ✅ **Intervalos de confianza**: Límites superiores e inferiores al 95%

#### 🚨 Detección de Anomalías
- ✅ **Isolation Forest**: Detección de montos atípicos con ML
- ✅ **Análisis de frecuencia**: Identificación de patrones de transacciones inusuales
- ✅ **Detección temporal**: Transacciones fuera de horario laboral
- ✅ **Patrones irregulares**: Números redondos, duplicados, secuencias sospechosas
- ✅ **Sistema de revisión**: Clasificación de falsos positivos y notas de auditoría

#### 🔌 REST APIs con DRF
- ✅ **20+ endpoints REST**: APIs completas para todos los módulos de ML/AI
- ✅ **Documentación automática**: Swagger UI y ReDoc con drf-spectacular
- ✅ **Autenticación**: Integración con sistema de permisos Django
- ✅ **Filtros avanzados**: Búsqueda y filtrado por múltiples criterios

📖 **Documentación detallada**: Ver [docs/API_ML_DOCUMENTATION.md](docs/API_ML_DOCUMENTATION.md) y [docs/EJEMPLOS_HTTPIE.md](docs/EJEMPLOS_HTTPIE.md)

## Tecnologías Utilizadas

### Backend & Base de Datos
- **Backend**: Django 5.2.8
- **Base de Datos**: MariaDB 11.8+ (con Window Functions, CTEs, JSON)
- **API REST**: Django REST Framework + drf-spectacular
- **Python**: 3.13+
- **Gestor de paquetes**: uv

### Machine Learning & AI
- **Embeddings**: Sentence Transformers (paraphrase-multilingual-MiniLM-L12-v2)
- **Predicciones**: Facebook Prophet
- **Detección de anomalías**: Scikit-learn (Isolation Forest)
- **Clustering**: K-means
- **Procesamiento**: PyTorch, NumPy, Pandas

### Frontend
- **CSS Framework**: Tailwind CSS
- **Templates**: Django Templates

## Estructura del Proyecto

```
proyecto-enci/
├── config/              # Configuración de Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/                # App principal (usuarios, auth, notificaciones)
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── admin.py
│   └── templatetags/
├── contabilidad/        # App de gestión contable
│   ├── models.py
│   ├── views.py
│   └── admin.py
├── templates/           # Plantillas HTML
│   ├── base.html
│   ├── core/
│   └── contabilidad/
├── manage.py
├── pyproject.toml
└── README.md
```

## Instalación

### Requisitos Previos

- Python 3.13+
- uv (gestor de paquetes Python)
- MariaDB/MariaDB Server instalado localmente

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone <url-del-repositorio>
cd proyecto-enci
```

2. **Crear entorno virtual e instalar dependencias**
```bash
uv sync
```

3. **Crear BD y usuario en MariaDB**

Accede al prompt de MariaDB como root:
```bash
sudo mariadb -u root
```
Dentro del prompt SQL:
```sql
CREATE DATABASE enci CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'enci'@'127.0.0.1' IDENTIFIED BY 'strong-password';
GRANT ALL PRIVILEGES ON enci.* TO 'enci'@'127.0.0.1';
FLUSH PRIVILEGES;
EXIT;
```

4. **Configurar entorno (.env)**
Define estas variables en `.env`:
```env
DB_ENGINE=django.db.backends.mysql
DB_NAME=enci
DB_USER=enci
DB_PASSWORD=strong-password
DB_HOST=127.0.0.1
DB_PORT=3306
```

5. **Ejecutar migraciones (MariaDB)**
```bash
uv run python manage.py migrate --no-input
```

6. **Crear superusuario**
```bash
uv run python manage.py createsuperuser --username admin --email admin@local.test
```

7. **Ejecutar servidor de desarrollo (MariaDB)**
```bash
uv run python manage.py runserver 8000
```

El proyecto estará disponible en `http://127.0.0.1:8000/`

### Tests con MariaDB

Crea una BD de pruebas y credenciales (opcional, recomendado):
```sql
CREATE DATABASE enci_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON enci_test.* TO 'enci'@'127.0.0.1';
FLUSH PRIVILEGES;
```
En `.env` añade (si usas distinto usuario para tests, ajusta):
```env
DB_TEST_NAME=enci_test
# DB_TEST_USER=enci
# DB_TEST_PASSWORD=strong-password
```
Ejecuta tests:
```bash
uv run pytest -xvs
```

## Uso

### Como Administrador
1. Acceder a `/admin/` con las credenciales del superusuario
2. Gestionar usuarios, perfiles y permisos
3. Revisar audit logs del sistema

### Como Docente
1. Registrarse seleccionando el rol "Docente"
2. Esperar activación por un administrador
3. Crear empresas plantilla desde el dashboard
4. Generar códigos de acceso para estudiantes
5. Supervisar y comentar el trabajo de estudiantes

### Como Estudiante
1. Registrarse con el rol "Estudiante"
2. Usar código de invitación del docente (si aplica)
3. Esperar activación
4. Crear empresas o importar plantillas
5. Trabajar en libros contables

## 🚀 APIs REST de Machine Learning

El sistema incluye APIs REST completas para todas las funcionalidades de ML/AI. Ver documentación detallada en:

- 📖 [Documentación Completa de APIs](docs/API_ML_DOCUMENTATION.md)
- 💡 [Ejemplos con HTTPie](docs/EJEMPLOS_HTTPIE.md)

### Endpoints Disponibles

#### Analytics (5 endpoints)
```bash
GET /api/ml/analytics/metricas/{empresa_id}/          # Métricas financieras
GET /api/ml/analytics/tendencias/{empresa_id}/        # Tendencias de ingresos/gastos
GET /api/ml/analytics/top-cuentas/{empresa_id}/       # Top cuentas por actividad
GET /api/ml/analytics/composicion/{empresa_id}/       # Composición patrimonial
GET /api/ml/analytics/jerarquico/{empresa_id}/        # Análisis jerárquico
```

#### Embeddings (4+ endpoints)
```bash
POST /api/ml/embeddings/generar/{empresa_id}/         # Generar embeddings
POST /api/ml/embeddings/buscar/{empresa_id}/          # Búsqueda semántica
POST /api/ml/embeddings/recomendar/{empresa_id}/      # Recomendaciones
GET  /api/ml/embeddings/clusters/{empresa_id}/        # Clustering K-means
GET  /api/ml/embeddings/                              # Listar embeddings
```

#### Predictions (2+ endpoints)
```bash
POST /api/ml/predictions/generar/{empresa_id}/        # Generar predicciones
GET  /api/ml/predictions/tendencia/{empresa_id}/      # Análisis de tendencia
GET  /api/ml/predictions/                             # Listar predicciones
```

#### Anomalies (3+ endpoints)
```bash
POST /api/ml/anomalies/detectar/{empresa_id}/         # Detectar anomalías
GET  /api/ml/anomalies/estadisticas/{empresa_id}/     # Estadísticas
POST /api/ml/anomalies/{id}/revisar/                  # Revisar anomalía
GET  /api/ml/anomalies/                               # Listar con filtros
```

### Documentación Interactiva

Una vez iniciado el servidor, accede a:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

### Ejemplo de Uso Rápido

```bash
# 1. Calcular métricas financieras
curl -X GET "http://localhost:8000/api/ml/analytics/metricas/1/" \
  --cookie "sessionid=YOUR_SESSION_ID"

# 2. Generar predicciones de ingresos
curl -X POST "http://localhost:8000/api/ml/predictions/generar/1/" \
  -H "Content-Type: application/json" \
  -d '{"tipo_prediccion": "INGRESOS", "dias_historicos": 90, "dias_futuros": 30}'

# 3. Buscar cuentas similares
curl -X POST "http://localhost:8000/api/ml/embeddings/buscar/1/" \
  -H "Content-Type: application/json" \
  -d '{"texto": "gastos de oficina", "limit": 5}'

# 4. Detectar anomalías
curl -X POST "http://localhost:8000/api/ml/anomalies/detectar/1/" \
  -H "Content-Type: application/json" \
  -d '{"dias_historicos": 90}'
```

### Script de Prueba Automatizado

```bash
# Probar todos los endpoints automáticamente
python scripts/test_ml_apis.py
```

## Modelos de Datos Principales

### Core App
- **UserProfile**: Extiende User de Django con roles (Admin, Docente, Estudiante)
- **Invitation**: Códigos de invitación generados por docentes
- **Referral**: Vínculo entre estudiantes y docentes
- **Notification**: Notificaciones del sistema
- **AuditLog**: Registro de auditoría de acciones

### Contabilidad App
- **Empresa**: Empresas ficticias (plantillas o copias)
- **EmpresaPlanCuenta**: Plan de cuentas por empresa
- **EmpresaAsiento**: Asientos contables
- **EmpresaTransaccion**: Líneas de detalle de asientos
- **EmpresaSupervisor**: Relación empresa-docente supervisor
- **EmpresaComment**: Comentarios de docentes en empresas

## Seguridad

- ✅ Autenticación personalizada con verificación de estado activo
- ✅ Control de acceso basado en roles
- ✅ Protección CSRF habilitada
- ✅ Registro de auditoría de acciones críticas
- ✅ Sesiones seguras con expiración al cerrar navegador

## Optimizaciones Implementadas

- ✅ Uso de `select_related()` y `prefetch_related()` para reducir queries N+1
- ✅ Índices de base de datos en campos clave
- ✅ Paginación de listas largas
- ✅ Raw ID fields en admin para mejor rendimiento
- ✅ Caché de consultas frecuentes

## Contribuir

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## Licencia

Proyecto académico - Universidad [Nombre]

## Contacto

Proyecto de Base de Datos II

---

**Nota**: Este es un proyecto educativo. No usar en producción sin las debidas configuraciones de seguridad adicionales.

## Guía de Desarrollo

- Dependencias: uv gestiona el entorno. No usar pip.
- Estilo: Ruff (formateo y lint). Estándares definidos en pyproject.toml.
- Hooks: pre-commit opcional para validar antes de cada commit.

### Primeros pasos

```bash
# Instalar dependencias
uv sync

# Copiar variables de entorno
cp .env.example .env

# Verificar configuración de Django
uv run python manage.py check
```

### Formateo y Lint

```bash
# Revisar y corregir problemas automáticamente
uv run ruff check . --fix

# Formatear código
uv run ruff format .
```

Para instalar los hooks de pre-commit:

```bash
uv run pre-commit install
```

### Pruebas

```bash
# Ejecutar tests
uv run pytest -q
```

Si usas MariaDB/MySQL, asegúrate de que el usuario tenga permisos para crear la base de datos de pruebas o configura `DB_*` en `.env`.

### Notas de mantenimiento

- Archivos temporales, caches, entornos y backups SQL están excluidos por `.gitignore`.
- Evita versionar `__pycache__`, `*.egg-info`, y dumps SQL en el root.
- Consulta `CONTABILIDAD_BEST_PRACTICES.md` para prácticas funcionales del dominio.
