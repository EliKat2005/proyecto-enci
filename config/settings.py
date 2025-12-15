"""
Ajustes de Django para el proyecto ENCI.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# (BASE_DIR apunta a la raíz: /mnt/universidad/Base de Datos II/proyecto-enci)
BASE_DIR = Path(__file__).resolve().parent.parent


# --- AJUSTES DE SEGURIDAD ---
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# En entornos con dominios personalizados o HTTPS añade los orígenes aquí,
# por ejemplo: CSRF_TRUSTED_ORIGINS = ['https://tudominio.com']
CSRF_TRUSTED_ORIGINS = []


# --- APLICACIONES (APPS) ---
# Aquí registramos los módulos de Django.
INSTALLED_APPS = [
    # Apps de Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # APIs
    'rest_framework',
    'rest_framework.authtoken',
    'drf_spectacular',
    'corsheaders',
    
    # Nuestras Apps (las crearemos en la Etapa 3)
    'core.apps.CoreConfig',
    'contabilidad.apps.ContabilidadConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Directorio para plantillas HTML globales
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# --- BASE DE DATOS (¡LO MÁS IMPORTANTE!) ---
# Conectado a nuestro DDL de MariaDB.
# --------------------------------------------------------------------------
# ¡¡¡ ACCIÓN REQUERIDA !!!
# Edita estos valores con tus credenciales de MariaDB.
# --------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'enci'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        'TEST': {
            'CREATE_DB': False,
            'NAME': 'enci_test',
        }
    }
}


# --- VALIDACIÓN DE CONTRASEÑAS ---
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]


# --- INTERNACIONALIZACIÓN ---
# Ajustado para español y Ecuador
LANGUAGE_CODE = 'es-ec'
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True


# --- ARCHIVOS ESTÁTICOS (CSS, JavaScript, Imágenes) ---
STATIC_URL = 'static/'

# --- CONFIGURACIÓN DE MODELO DE USUARIO ---
# Más adelante, aquí definiremos nuestro modelo de perfil
# AUTH_USER_MODEL = 'core.User' # (No descomentar aún)

# --- REDIRECCIÓN DE LOGIN ---
# Aquí le decimos a Django a dónde ir DESPUÉS de un login exitoso.
# Usamos el 'name' de nuestra URL en core.urls
LOGIN_REDIRECT_URL = 'home'
# URL de login usada por `login_required` y otras utilidades.
# Puede ser el nombre de la URL ('login') o la ruta ('/login/').
LOGIN_URL = 'login'

# --------------------------------------------------------------------------
# ¡¡¡ ESTE ES EL NUEVO BLOQUE QUE ACABO DE AÑADIR !!!
# --------------------------------------------------------------------------
# Le decimos a Django que use nuestro "guardia" personalizado.
AUTHENTICATION_BACKENDS = [
    'core.backends.ActiveStudentBackend', # Nuestro guardia (Revisa 'esta_activo')
    'django.contrib.auth.backends.ModelBackend', # El guardia de Django (necesario para el Admin)
]

# --- TIPO DE CAMPO AUTO-INCREMENTAL ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- SEGURIDAD DE SESIONES ---
# Expirar la sesión al cerrar el navegador (útil para entornos de usuario compartido)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
# Edad de la cookie de sesión (2 semanas en producción)
SESSION_COOKIE_AGE = 1209600
# Nombre de la cookie de sesión (cambiar en producción para ofuscar)
SESSION_COOKIE_NAME = 'enci_sessionid'
# En producción habilitar estas opciones:
# SESSION_COOKIE_SECURE = True  # Solo HTTPS
# CSRF_COOKIE_SECURE = True     # Solo HTTPS
# SECURE_SSL_REDIRECT = True    # Forzar HTTPS

# --- CONFIGURACIÓN DE EMAIL ---
# Development: mostrar emails en la consola para pruebas
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'no-reply@enci.local'
# En producción configurar SMTP real:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'tu-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'tu-contraseña'

# --- CONFIGURACIÓN DE DJANGO REST FRAMEWORK ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# --- CONFIGURACIÓN DE SWAGGER/OPENAPI ---
SPECTACULAR_SETTINGS = {
    'TITLE': 'ENCI - Sistema de Gestión Contable API',
    'DESCRIPTION': 'API REST para gestión de contabilidad empresarial. Documentación completa de endpoints, serializers y autenticación.',
    'VERSION': '1.0.0',
    'CONTACT': {
        'name': 'Proyecto ENCI',
        'email': 'admin@enci.local',
    },
    'LICENSE': {
        'name': 'Licencia Académica',
        'url': 'https://creativecommons.org/licenses/by-nc-sa/4.0/',
    },
    'SERVERS': [
        {'url': 'http://localhost:9000', 'description': 'Development'},
        {'url': 'http://localhost:8000', 'description': 'Development (puerto alternativo)'},
    ],
}

# --- CONFIGURACIÓN DE CORS ---
CORS_ALLOWED_ORIGINS = os.getenv(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000'
).split(',')

CORS_ALLOW_CREDENTIALS = True

# --- CONFIGURACIÓN DE PYTEST ---
if 'pytest' in os.sys.modules or 'PYTEST_CURRENT_TEST' in os.environ:
    DATABASES['default']['NAME'] = 'enci_test'
    LOGGING = {'version': 1, 'disable_existing_loggers': False}