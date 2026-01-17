"""
API REST para servicios ML avanzados (FASES 2-4).
Incluye: Búsqueda optimizada, Vector storage, ML nativo en SQL.
"""

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from contabilidad.ml_advanced import AdvancedMLService
from contabilidad.ml_optimized import OptimizedAnalyticsService
from contabilidad.models import Empresa
from contabilidad.permissions import IsEmpresaOwnerOrSupervisor
from contabilidad.serializers import (
    AccountCorrelationSerializer,
    AutocompleteResultSerializer,
    AutocompleteSerializer,
    BusquedaBooleanSerializer,
    EMAForecastRequestSerializer,
    EMAForecastResultSerializer,
    EmbeddingSimilaritySerializer,
    FinancialHealthScoreSerializer,
    RealtimeDashboardSerializer,
    VectorMigrationResultSerializer,
    VectorMigrationSerializer,
)
from contabilidad.throttling import HeavyMLThrottle, MLAPIThrottle


class AdvancedMLViewSet(viewsets.ViewSet):
    """
    API para servicios ML avanzados - FASES 2-4.

    Incluye:
    - Búsqueda con operadores booleanos
    - Autocompletado inteligente
    - Migración a VECTOR storage
    - Score de salud financiera
    - Correlaciones de cuentas
    - Predicciones con EMA
    - Dashboard en tiempo real
    """

    permission_classes = [IsAuthenticated, IsEmpresaOwnerOrSupervisor]
    throttle_classes = [MLAPIThrottle, HeavyMLThrottle]

    # ==================== FASE 2: BÚSQUEDA OPTIMIZADA ====================

    @extend_schema(
        summary="Búsqueda con operadores booleanos",
        description='Búsqueda FULLTEXT con operadores: +palabra (debe tener), -palabra (no debe tener), "frase exacta", palabra*',
        request=BusquedaBooleanSerializer,
        responses={200: EmbeddingSimilaritySerializer(many=True)},
        parameters=[OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @action(detail=False, methods=["post"], url_path="busqueda-boolean/(?P<empresa_id>[^/.]+)")
    def busqueda_boolean(self, request, empresa_id=None):
        """Búsqueda con operadores booleanos avanzados."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        serializer = BusquedaBooleanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = AdvancedMLService(empresa)

        resultados = service.search_with_boolean_operators(
            query=data["query"], limit=data["limit"], mode=data["mode"]
        )

        return Response(
            {
                "query": data["query"],
                "mode": data["mode"],
                "total": len(resultados),
                "results": resultados,
            }
        )

    @extend_schema(
        summary="Autocompletado de cuentas",
        description="Autocompletado ultrarrápido para búsqueda de cuentas por prefijo",
        request=AutocompleteSerializer,
        responses={200: AutocompleteResultSerializer(many=True)},
        parameters=[OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @action(detail=False, methods=["post"], url_path="autocomplete/(?P<empresa_id>[^/.]+)")
    def autocomplete(self, request, empresa_id=None):
        """Autocompletado de cuentas."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        serializer = AutocompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = AdvancedMLService(empresa)

        resultados = service.autocomplete_search(
            partial_query=data["partial_query"], limit=data["limit"]
        )

        return Response(
            {
                "partial_query": data["partial_query"],
                "total": len(resultados),
                "suggestions": resultados,
            }
        )

    # ==================== FASE 2: DETECCIÓN AVANZADA DE ANOMALÍAS ====================

    @extend_schema(
        summary="Detectar anomalías con percentiles",
        description="Detección de anomalías usando percentiles (más robusto que Z-score)",
        parameters=[
            OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter("dias", OpenApiTypes.INT, OpenApiParameter.QUERY, default=90),
            OpenApiParameter(
                "percentil_bajo", OpenApiTypes.FLOAT, OpenApiParameter.QUERY, default=0.01
            ),
            OpenApiParameter(
                "percentil_alto", OpenApiTypes.FLOAT, OpenApiParameter.QUERY, default=0.99
            ),
        ],
    )
    @action(detail=False, methods=["get"], url_path="anomalias-percentiles/(?P<empresa_id>[^/.]+)")
    def anomalias_percentiles(self, request, empresa_id=None):
        """Detecta anomalías usando percentiles."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        dias = int(request.query_params.get("dias", 90))
        percentil_bajo = float(request.query_params.get("percentil_bajo", 0.01))
        percentil_alto = float(request.query_params.get("percentil_alto", 0.99))

        service = OptimizedAnalyticsService(empresa)

        anomalias = service.detect_anomalies_with_percentiles(
            dias=dias, percentil_bajo=percentil_bajo, percentil_alto=percentil_alto
        )

        return Response(
            {
                "dias_analizados": dias,
                "percentil_bajo": percentil_bajo,
                "percentil_alto": percentil_alto,
                "total_anomalias": len(anomalias),
                "anomalias": anomalias,
            }
        )

    @extend_schema(
        summary="Clustering de cuentas por patrón",
        description="Segmenta cuentas en clusters según patrones de uso",
        parameters=[OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @action(detail=False, methods=["get"], url_path="clustering/(?P<empresa_id>[^/.]+)")
    def clustering(self, request, empresa_id=None):
        """Clustering automático de cuentas."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        service = OptimizedAnalyticsService(empresa)
        clusters = service.cluster_cuentas_por_patron()

        # Agrupar por cluster
        clusters_agrupados = {}
        for cuenta in clusters:
            cluster_name = cuenta["cluster"]
            if cluster_name not in clusters_agrupados:
                clusters_agrupados[cluster_name] = []
            clusters_agrupados[cluster_name].append(cuenta)

        return Response(
            {
                "total_cuentas": len(clusters),
                "num_clusters": len(clusters_agrupados),
                "clusters": clusters_agrupados,
                "resumen": {nombre: len(cuentas) for nombre, cuentas in clusters_agrupados.items()},
            }
        )

    # ==================== FASE 3: VECTOR STORAGE ====================

    @extend_schema(
        summary="Migrar a VECTOR storage",
        description="Migra embeddings JSON a tipo VECTOR nativo de MariaDB 11.6+ (dry_run por defecto)",
        request=VectorMigrationSerializer,
        responses={200: VectorMigrationResultSerializer},
        parameters=[OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @action(detail=False, methods=["post"], url_path="migrate-to-vector/(?P<empresa_id>[^/.]+)")
    def migrate_to_vector(self, request, empresa_id=None):
        """Migra embeddings a tipo VECTOR nativo."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        serializer = VectorMigrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = AdvancedMLService(empresa)

        resultado = service.migrate_to_vector_storage(dry_run=data["dry_run"])

        return Response(resultado)

    # ==================== FASE 4: ML NATIVO EN SQL ====================

    @extend_schema(
        summary="Score de salud financiera",
        description="Calcula score automático de salud financiera (0-100) usando múltiples factores",
        parameters=[OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH)],
        responses={200: FinancialHealthScoreSerializer},
    )
    @action(detail=False, methods=["get"], url_path="health-score/(?P<empresa_id>[^/.]+)")
    def health_score(self, request, empresa_id=None):
        """Calcula score de salud financiera."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        service = AdvancedMLService(empresa)
        score = service.calculate_financial_health_score()

        return Response(score)

    @extend_schema(
        summary="Correlaciones de cuentas",
        description="Analiza correlaciones entre cuentas (cuentas que se mueven juntas)",
        parameters=[
            OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter(
                "min_correlacion",
                OpenApiTypes.FLOAT,
                OpenApiParameter.QUERY,
                default=0.7,
                description="Correlación mínima (0-1)",
            ),
        ],
        responses={200: AccountCorrelationSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="correlaciones/(?P<empresa_id>[^/.]+)")
    def correlaciones(self, request, empresa_id=None):
        """Analiza correlaciones entre cuentas."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        min_correlacion = float(request.query_params.get("min_correlacion", 0.7))
        service = AdvancedMLService(empresa)

        correlaciones = service.analyze_account_correlations(min_correlacion=min_correlacion)

        return Response(
            {
                "min_correlacion": min_correlacion,
                "total_pares": len(correlaciones),
                "correlaciones": correlaciones,
            }
        )

    @extend_schema(
        summary="Predicción con EMA",
        description="Predicción usando Media Móvil Exponencial (más reactivo que media simple)",
        request=EMAForecastRequestSerializer,
        responses={200: EMAForecastResultSerializer},
        parameters=[OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH)],
    )
    @action(detail=False, methods=["post"], url_path="predict-ema/(?P<empresa_id>[^/.]+)")
    def predict_ema(self, request, empresa_id=None):
        """Predicción con Media Móvil Exponencial."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        serializer = EMAForecastRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = AdvancedMLService(empresa)

        prediccion = service.predict_with_exponential_moving_average(
            tipo_cuenta=data["tipo_cuenta"],
            dias_futuros=data["dias_futuros"],
            alpha=data["alpha"],
        )

        return Response(prediccion)

    @extend_schema(
        summary="Predicción con regresión lineal SQL",
        description="Predicción ligera usando regresión lineal calculada 100% en SQL (muy rápida)",
        parameters=[
            OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter(
                "tipo_cuenta",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["INGRESO", "GASTO", "COSTO"],
            ),
            OpenApiParameter(
                "dias_historicos", OpenApiTypes.INT, OpenApiParameter.QUERY, default=90
            ),
            OpenApiParameter("dias_futuros", OpenApiTypes.INT, OpenApiParameter.QUERY, default=30),
        ],
    )
    @action(detail=False, methods=["get"], url_path="predict-linear/(?P<empresa_id>[^/.]+)")
    def predict_linear(self, request, empresa_id=None):
        """Predicción con regresión lineal SQL."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        tipo_cuenta = request.query_params.get("tipo_cuenta", "INGRESO")
        dias_historicos = int(request.query_params.get("dias_historicos", 90))
        dias_futuros = int(request.query_params.get("dias_futuros", 30))

        service = OptimizedAnalyticsService(empresa)

        prediccion = service.predict_with_linear_regression_sql(
            tipo_cuenta=tipo_cuenta, dias_historicos=dias_historicos, dias_futuros=dias_futuros
        )

        return Response(prediccion)

    @extend_schema(
        summary="Dashboard en tiempo real",
        description="Métricas de dashboard calculadas 100% en SQL (sin cache, sin Python) para tiempo real",
        parameters=[OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH)],
        responses={200: RealtimeDashboardSerializer},
    )
    @action(detail=False, methods=["get"], url_path="realtime-dashboard/(?P<empresa_id>[^/.]+)")
    def realtime_dashboard(self, request, empresa_id=None):
        """Dashboard en tiempo real."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        service = AdvancedMLService(empresa)
        metricas = service.realtime_dashboard_metrics()

        return Response(metricas)
