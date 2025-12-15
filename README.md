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
- MariaDB/MySQL
- uv (gestor de paquetes Python)

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

3. **Configurar base de datos**

Editar `config/settings.py` y actualizar las credenciales de la base de datos:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'enci',
        'USER': 'tu_usuario',
        'PASSWORD': 'tu_contraseña',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
```

4. **Ejecutar migraciones**
```bash
uv run python manage.py migrate
```

5. **Crear superusuario**
```bash
uv run python manage.py createsuperuser
```

6. **Ejecutar servidor de desarrollo**
```bash
uv run python manage.py runserver
```

El proyecto estará disponible en `http://127.0.0.1:8000/`

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