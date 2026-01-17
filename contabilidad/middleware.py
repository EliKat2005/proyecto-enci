"""
Middleware personalizado para logging, performance y auditoría.
"""

import logging
import time

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("audit")
performance_logger = logging.getLogger("performance")


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware para monitorear tiempos de respuesta.
    Registra requests lentos (> 1 segundo) para identificar cuellos de botella.
    """

    def process_request(self, request):
        """Inicializa el timer al inicio del request."""
        request._start_time = time.time()

    def process_response(self, request, response):
        """Calcula el tiempo de respuesta y registra si es lento."""
        if hasattr(request, "_start_time"):
            duration = time.time() - request._start_time

            # Registrar requests lentos
            if duration > 1.0:  # Más de 1 segundo
                performance_logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration:.2f}s - User: {request.user}"
                )

            # Agregar header con tiempo de respuesta
            response["X-Response-Time"] = f"{duration:.3f}s"

        return response


class AuditLoggingMiddleware(MiddlewareMixin):
    """
    Middleware para auditoría de acciones críticas.
    Registra operaciones importantes con información del usuario.
    """

    # Endpoints a auditar
    AUDIT_PATHS = [
        "/contabilidad/api/",
        "/empresa/crear/",
        "/empresa/eliminar/",
        "/asiento/crear/",
        "/asiento/eliminar/",
    ]

    # Métodos HTTP a auditar (no GET)
    AUDIT_METHODS = ["POST", "PUT", "PATCH", "DELETE"]

    def process_response(self, request, response):
        """Registra acciones auditables."""
        # Solo auditar si es un método modificador
        if request.method not in self.AUDIT_METHODS:
            return response

        # Solo auditar rutas específicas
        should_audit = any(request.path.startswith(path) for path in self.AUDIT_PATHS)

        if should_audit and hasattr(request, "user") and request.user.is_authenticated:
            # Preparar información de auditoría
            log_data = {
                "user": request.user.username,
                "user_id": request.user.id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "ip": self.get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            }

            # Agregar información de empresa si está en el path
            if "empresa_id" in request.resolver_match.kwargs:
                log_data["empresa_id"] = request.resolver_match.kwargs["empresa_id"]

            # Log según el resultado
            if 200 <= response.status_code < 300:
                audit_logger.info(f"Action successful: {log_data}")
            elif 400 <= response.status_code < 500:
                audit_logger.warning(f"Action failed (client error): {log_data}")
            elif 500 <= response.status_code < 600:
                audit_logger.error(f"Action failed (server error): {log_data}")

        return response

    @staticmethod
    def get_client_ip(request):
        """Obtiene la IP real del cliente, considerando proxies."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware para agregar headers de seguridad.
    Mejora la seguridad del sitio contra ataques comunes.
    """

    def process_response(self, request, response):
        """Agrega headers de seguridad a todas las respuestas."""
        # Prevenir clickjacking
        response["X-Frame-Options"] = "DENY"

        # Prevenir MIME sniffing
        response["X-Content-Type-Options"] = "nosniff"

        # XSS Protection (legacy, pero útil para navegadores viejos)
        response["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy (antes Feature-Policy)
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=()"

        return response


class RequestIDMiddleware(MiddlewareMixin):
    """
    Middleware para agregar un ID único a cada request.
    Útil para trazabilidad y debugging.
    """

    def process_request(self, request):
        """Genera y asigna un ID único al request."""
        import uuid

        request.id = str(uuid.uuid4())

    def process_response(self, request, response):
        """Agrega el Request ID al header de respuesta."""
        if hasattr(request, "id"):
            response["X-Request-ID"] = request.id
        return response
