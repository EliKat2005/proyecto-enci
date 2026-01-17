"""
Configuración de logging avanzado para el proyecto.
Usar este archivo en settings.py para configurar múltiples loggers.

LOGGING = get_logging_config(DEBUG=DEBUG, LOG_DIR='logs/')
"""

import logging
import os
from pathlib import Path


def get_logging_config(DEBUG=False, LOG_DIR="logs/"):
    """
    Genera la configuración de logging para Django.

    Args:
        DEBUG: Si está en modo debug
        LOG_DIR: Directorio para guardar logs

    Returns:
        dict: Configuración de logging para LOGGING en settings.py
    """
    # Crear directorio de logs si no existe
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
                "style": "{",
            },
            "simple": {
                "format": "{levelname} {asctime} {message}",
                "style": "{",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "filters": {
            "require_debug_false": {
                "()": "django.utils.log.RequireDebugFalse",
            },
            "require_debug_true": {
                "()": "django.utils.log.RequireDebugTrue",
            },
        },
        "handlers": {
            # Console output
            "console": {
                "level": "INFO" if not DEBUG else "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "simple",
            },
            # Archivo general
            "file": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "enci.log"),
                "maxBytes": 1024 * 1024 * 10,  # 10 MB
                "backupCount": 5,
                "formatter": "verbose",
            },
            # Archivo de errores
            "error_file": {
                "level": "ERROR",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "error.log"),
                "maxBytes": 1024 * 1024 * 10,  # 10 MB
                "backupCount": 5,
                "formatter": "verbose",
            },
            # Archivo de auditoría
            "audit_file": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "audit.log"),
                "maxBytes": 1024 * 1024 * 50,  # 50 MB (más grande)
                "backupCount": 10,
                "formatter": "json",  # JSON para parsing fácil
            },
            # Archivo de performance
            "performance_file": {
                "level": "WARNING",  # Solo requests lentos
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "performance.log"),
                "maxBytes": 1024 * 1024 * 20,  # 20 MB
                "backupCount": 5,
                "formatter": "verbose",
            },
            # Archivo de ML/AI
            "ml_file": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOG_DIR, "ml.log"),
                "maxBytes": 1024 * 1024 * 20,  # 20 MB
                "backupCount": 5,
                "formatter": "verbose",
            },
            # Email para errores críticos (solo en producción)
            "mail_admins": {
                "level": "ERROR",
                "class": "django.utils.log.AdminEmailHandler",
                "filters": ["require_debug_false"],
                "formatter": "verbose",
            },
        },
        "loggers": {
            # Logger general de Django
            "django": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
            # Errores de Django
            "django.request": {
                "handlers": ["error_file", "mail_admins"],
                "level": "ERROR",
                "propagate": False,
            },
            # DB queries (solo en debug)
            "django.db.backends": {
                "handlers": ["console"],
                "level": "DEBUG" if DEBUG else "INFO",
                "propagate": False,
            },
            # Logger de auditoría
            "audit": {
                "handlers": ["audit_file", "console"],
                "level": "INFO",
                "propagate": False,
            },
            # Logger de performance
            "performance": {
                "handlers": ["performance_file", "console"],
                "level": "WARNING",
                "propagate": False,
            },
            # Logger de ML/AI
            "ml": {
                "handlers": ["ml_file", "console"],
                "level": "INFO",
                "propagate": False,
            },
            # Logger de la app contabilidad
            "contabilidad": {
                "handlers": ["file", "console", "error_file"],
                "level": "DEBUG" if DEBUG else "INFO",
                "propagate": False,
            },
            # Logger de la app core
            "core": {
                "handlers": ["file", "console", "error_file"],
                "level": "DEBUG" if DEBUG else "INFO",
                "propagate": False,
            },
        },
        # Root logger
        "root": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
    }

    return config


# Configuración de Sentry para producción
def setup_sentry(dsn, environment="production", traces_sample_rate=0.1):
    """
    Configura Sentry para error tracking.

    Args:
        dsn: DSN de Sentry (obtener de sentry.io)
        environment: Entorno (production, staging, development)
        traces_sample_rate: % de transacciones a tracear (0.0 - 1.0)

    Uso en settings.py:
        if not DEBUG:
            setup_sentry(
                dsn=os.getenv('SENTRY_DSN'),
                environment='production',
                traces_sample_rate=0.1
            )
    """
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        # Configurar integración de logging
        logging_integration = LoggingIntegration(
            level=logging.INFO,  # Capturar logs nivel INFO+
            event_level=logging.ERROR,  # Enviar a Sentry solo ERROR+
        )

        sentry_sdk.init(
            dsn=dsn,
            integrations=[
                DjangoIntegration(),
                logging_integration,
            ],
            # Porcentaje de transacciones a tracear
            traces_sample_rate=traces_sample_rate,
            # No enviar información personal por defecto
            send_default_pii=False,
            # Entorno
            environment=environment,
            # Release (usar git commit hash o version)
            # release="enci@1.0.0",
        )

        print(f"✅ Sentry configurado para {environment}")

    except ImportError:
        print("⚠️ sentry-sdk no instalado. Instalar con: pip install sentry-sdk")
    except Exception as e:
        print(f"❌ Error configurando Sentry: {e}")


# Ejemplo de uso en código
"""
import logging

# Logger general
logger = logging.getLogger(__name__)
logger.info("Mensaje informativo")
logger.error("Error crítico", exc_info=True)

# Logger de auditoría
audit_logger = logging.getLogger('audit')
audit_logger.info(f"Usuario {user.id} modificó asiento {asiento.id}")

# Logger de performance
performance_logger = logging.getLogger('performance')
performance_logger.warning(f"Query lenta: {query} tomó {duration}s")

# Logger de ML
ml_logger = logging.getLogger('ml')
ml_logger.info(f"Generando predicciones para empresa {empresa_id}")
"""
