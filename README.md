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

## Tecnologías Utilizadas

- **Backend**: Django 5.2.8
- **Base de Datos**: MariaDB/MySQL
- **Frontend**: Tailwind CSS
- **Python**: 3.13+
- **Gestor de paquetes**: uv

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
