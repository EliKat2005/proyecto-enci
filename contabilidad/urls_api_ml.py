"""
URLs para las APIs de Machine Learning y Analytics.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from contabilidad.api_ml import (
    AnalyticsViewSet,
    AnomaliesViewSet,
    EmbeddingsViewSet,
    PredictionsViewSet,
)

# Crear router para ViewSets
router = DefaultRouter()
router.register(r"predictions", PredictionsViewSet, basename="predictions")
router.register(r"embeddings", EmbeddingsViewSet, basename="embeddings")
router.register(r"anomalies", AnomaliesViewSet, basename="anomalies")

# URLs personalizadas para AnalyticsViewSet (usa actions en lugar de ModelViewSet)
analytics_patterns = [
    path(
        "metricas/<int:empresa_id>/",
        AnalyticsViewSet.as_view({"get": "calcular_metricas"}),
        name="analytics-metricas",
    ),
    path(
        "tendencias/<int:empresa_id>/",
        AnalyticsViewSet.as_view({"get": "tendencias_ingresos_gastos"}),
        name="analytics-tendencias",
    ),
    path(
        "top-cuentas/<int:empresa_id>/",
        AnalyticsViewSet.as_view({"get": "top_cuentas"}),
        name="analytics-top-cuentas",
    ),
    path(
        "composicion/<int:empresa_id>/",
        AnalyticsViewSet.as_view({"get": "composicion_patrimonial"}),
        name="analytics-composicion",
    ),
    path(
        "jerarquico/<int:empresa_id>/",
        AnalyticsViewSet.as_view({"get": "analisis_jerarquico"}),
        name="analytics-jerarquico",
    ),
]

app_name = "api_ml"

urlpatterns = [
    # Analytics endpoints (custom actions)
    path("analytics/", include(analytics_patterns)),
    # ViewSets con router
    path("", include(router.urls)),
]
