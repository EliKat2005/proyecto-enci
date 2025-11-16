"""
Ajustes de Django para el proyecto ENCI.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# (BASE_DIR apunta a la raíz: /mnt/universidad/Base de Datos II/proyecto-enci)
BASE_DIR = Path(__file__).resolve().parent.parent


# --- AJUSTES DE SEGURIDAD ---
# ¡IMPORTANTE! Cambia esto en producción.
SECRET_KEY = 'django-insecure-tu-clave-secreta-aqui-reemplazame'

# ¡IMPORTANTE! Cambia esto en producción.
DEBUG = True

ALLOWED_HOSTS = []


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
    
    # Nuestras Apps (las crearemos en la Etapa 3)
    'core.apps.CoreConfig',
    'contabilidad.apps.ContabilidadConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
        'ENGINE': 'django.db.backends.mysql', # El driver para MariaDB es el de MySQL
        'NAME': 'enci', # El nombre de tu base de datos
        'USER': 'elikat', # Tu usuario de MariaDB (ej: 'root' o 'tu_usuario')
        'PASSWORD': 'ZoHg$0q6ld9Iqq', # Tu contraseña de MariaDB
        'HOST': '127.0.0.1', # O 'localhost'
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
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

# --- TIPO DE CAMPO AUTO-INCREMENTAL ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'