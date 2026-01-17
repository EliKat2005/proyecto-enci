"""
Throttling personalizado para APIs ML/AI.
Implementa rate limiting específico para endpoints costosos computacionalmente.
"""

from rest_framework.throttling import UserRateThrottle


class MLAPIThrottle(UserRateThrottle):
    """
    Rate limit específico para endpoints ML/AI.
    Por defecto: 500 requests por hora por usuario.
    """

    scope = "ml_api"


class HeavyMLThrottle(UserRateThrottle):
    """
    Rate limit más restrictivo para operaciones ML pesadas.
    Por defecto: 100 requests por hora por usuario.

    Usar en endpoints como:
    - Generación de embeddings
    - Predicciones con Prophet
    - Clustering
    - Migración a VECTOR
    """

    scope = "ml_heavy"


class EmbeddingThrottle(UserRateThrottle):
    """
    Rate limit para generación de embeddings.
    Por defecto: 200 requests por día por usuario.
    """

    scope = "embedding_generation"


class PredictionThrottle(UserRateThrottle):
    """
    Rate limit para predicciones con Prophet.
    Por defecto: 50 requests por día por usuario.
    """

    scope = "prediction_generation"
