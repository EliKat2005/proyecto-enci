"""
Configuración de ejemplo para producción del proyecto ENCI.

IMPORTANTE: 
- Copiar este archivo a settings_production.py
- NO versionar settings_production.py (debe estar en .gitignore)
- Actualizar todos los valores marcados con TODO
"""

from .settings import *  # noqa

# TODO: Cambiar a False en producción
DEBUG = False

# TODO: Generar una clave secreta única y fuerte
# Puedes usar: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = 'CAMBIAR-POR-CLAVE-SECRETA-LARGA-Y-ALEATORIA-DE-50+-CARACTERES'

# TODO: Agregar tu dominio
ALLOWED_HOSTS = [
    'tudominio.com',
    'www.tudominio.com',
    # Agregar más dominios si es necesario
]

# TODO: Agregar tus orígenes CSRF si usas subdominios o HTTPS
CSRF_TRUSTED_ORIGINS = [
    'https://tudominio.com',
    'https://www.tudominio.com',
]

# --- SEGURIDAD HTTPS/SSL ---
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# --- BASE DE DATOS PRODUCCIÓN ---
# TODO: Actualizar con credenciales de producción
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'enci_production',
        'USER': 'enci_user',
        'PASSWORD': 'PASSWORD-FUERTE-AQUI',
        'HOST': 'localhost',  # o IP del servidor de BD
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
        'CONN_MAX_AGE': 600,  # Conexiones persistentes por 10 minutos
    }
}

# --- EMAIL SMTP PRODUCCIÓN ---
# TODO: Configurar con tu proveedor SMTP
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # o tu servidor SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'tu-email@dominio.com'
EMAIL_HOST_PASSWORD = 'tu-password-de-aplicacion'
DEFAULT_FROM_EMAIL = 'ENCI <no-reply@tudominio.com>'
SERVER_EMAIL = 'admin@tudominio.com'

# --- ARCHIVOS ESTÁTICOS ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# --- ARCHIVOS MEDIA ---
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- LOGGING ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['mail_admins', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# --- ADMINS ---
# TODO: Agregar administradores que recibirán emails de errores
ADMINS = [
    ('Admin Name', 'admin@tudominio.com'),
]

MANAGERS = ADMINS

# --- CACHÉ (Opcional - Mejorar rendimiento) ---
# Descomentar y configurar si usas Redis o Memcached
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379/1',
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         },
#         'KEY_PREFIX': 'enci',
#         'TIMEOUT': 300,
#     }
# }

# --- SESIÓN ---
SESSION_COOKIE_AGE = 1209600  # 2 semanas
SESSION_COOKIE_NAME = 'enci_sessionid_prod'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# --- OTRAS CONFIGURACIONES DE SEGURIDAD ---
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# --- COMPRESIÓN DE RESPUESTAS (Opcional) ---
# MIDDLEWARE.insert(0, 'django.middleware.gzip.GZipMiddleware')
