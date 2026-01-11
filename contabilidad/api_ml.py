"""
API REST para Machine Learning y Analytics.

Endpoints:
- /api/ml/analytics/ - Análisis financieros y métricas
- /api/ml/predictions/ - Predicciones financieras
- /api/ml/embeddings/ - Búsqueda semántica y recomendaciones
- /api/ml/anomalies/ - Detección y gestión de anomalías
"""

from datetime import date, timedelta

from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from contabilidad.analytics import AnalyticsService
from contabilidad.ml_anomalies import AnomalyService
from contabilidad.ml_embeddings import EmbeddingService
from contabilidad.ml_predictions import PredictionService
from contabilidad.models import (
    AnomaliaDetectada,
    Empresa,
    EmpresaCuentaEmbedding,
    PrediccionFinanciera,
)
from contabilidad.serializers import (
    AnalisisJerarquicoSerializer,
    AnomaliaDetectadaSerializer,
    AnomaliaEstadisticasSerializer,
    BusquedaSemanticaRequestSerializer,
    ComposicionPatrimonialSerializer,
    DetectarAnomaliasRequestSerializer,
    EmbeddingClusterSerializer,
    EmbeddingSimilaritySerializer,
    EmpresaCuentaEmbeddingSerializer,
    EmpresaMetricaSerializer,
    GenerarPrediccionesRequestSerializer,
    MetricasFinancierasSerializer,
    PrediccionFinancieraSerializer,
    PrediccionTendenciaSerializer,
    RecomendacionCuentasRequestSerializer,
    RevisarAnomaliaSerializer,
    TendenciaIngresosGastosSerializer,
    TopCuentasSerializer,
)


class AnalyticsViewSet(viewsets.ViewSet):
    """
    API para análisis financieros y métricas en tiempo real.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Calcular métricas financieras",
        description="Calcula métricas financieras (liquidez, rentabilidad, endeudamiento) para un periodo",
        parameters=[
            OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter("fecha_inicio", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("fecha_fin", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        ],
        responses={200: MetricasFinancierasSerializer},
    )
    @action(detail=False, methods=["get"], url_path="metricas/(?P<empresa_id>[^/.]+)")
    def calcular_metricas(self, request, empresa_id=None):
        """Calcula métricas financieras para un periodo."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        # Parámetros de fecha
        fecha_inicio = request.query_params.get("fecha_inicio")
        fecha_fin = request.query_params.get("fecha_fin", date.today().isoformat())

        if not fecha_inicio:
            # Por defecto último mes
            fecha_fin_date = date.fromisoformat(fecha_fin)
            fecha_inicio = (fecha_fin_date - timedelta(days=30)).isoformat()

        service = AnalyticsService(empresa)
        metrica = service.calcular_metricas_periodo(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

        if metrica:
            serializer = EmpresaMetricaSerializer(metrica)
            return Response(serializer.data)
        else:
            return Response(
                {"error": "No se pudieron calcular las métricas"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        summary="Obtener tendencias de ingresos y gastos",
        description="Obtiene tendencias históricas con promedios móviles y tasas de crecimiento",
        parameters=[
            OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter("meses", OpenApiTypes.INT, OpenApiParameter.QUERY, default=12),
        ],
        responses={200: TendenciaIngresosGastosSerializer},
    )
    @action(detail=False, methods=["get"], url_path="tendencias/(?P<empresa_id>[^/.]+)")
    def tendencias_ingresos_gastos(self, request, empresa_id=None):
        """Obtiene tendencias de ingresos y gastos."""
        empresa = get_object_or_404(Empresa, id=empresa_id)
        meses = int(request.query_params.get("meses", 12))

        service = AnalyticsService(empresa)
        tendencias = service.get_tendencia_ingresos_gastos(meses=meses)

        serializer = TendenciaIngresosGastosSerializer(tendencias)
        return Response(serializer.data)

    @extend_schema(
        summary="Top cuentas por movimiento",
        description="Obtiene ranking de cuentas con mayor actividad",
        parameters=[
            OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter("limit", OpenApiTypes.INT, OpenApiParameter.QUERY, default=10),
            OpenApiParameter("fecha_inicio", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("fecha_fin", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        ],
        responses={200: TopCuentasSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="top-cuentas/(?P<empresa_id>[^/.]+)")
    def top_cuentas(self, request, empresa_id=None):
        """Obtiene top cuentas por movimiento."""
        empresa = get_object_or_404(Empresa, id=empresa_id)
        limit = int(request.query_params.get("limit", 10))
        fecha_inicio = request.query_params.get("fecha_inicio")
        fecha_fin = request.query_params.get("fecha_fin")

        service = AnalyticsService(empresa)
        top = service.get_top_cuentas_movimiento(
            limit=limit, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin
        )

        serializer = TopCuentasSerializer(top, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Composición patrimonial",
        description="Obtiene distribución porcentual de la estructura financiera",
        parameters=[
            OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter("fecha", OpenApiTypes.DATE, OpenApiParameter.QUERY),
        ],
        responses={200: ComposicionPatrimonialSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="composicion/(?P<empresa_id>[^/.]+)")
    def composicion_patrimonial(self, request, empresa_id=None):
        """Obtiene composición patrimonial."""
        empresa = get_object_or_404(Empresa, id=empresa_id)
        fecha = request.query_params.get("fecha")

        service = AnalyticsService(empresa)
        composicion = service.get_composicion_patrimonial(fecha=fecha)

        serializer = ComposicionPatrimonialSerializer(composicion, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Análisis jerárquico de cuentas",
        description="Obtiene análisis jerárquico recursivo del plan de cuentas con saldos",
        parameters=[
            OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter("nivel_max", OpenApiTypes.INT, OpenApiParameter.QUERY, default=3),
        ],
        responses={200: AnalisisJerarquicoSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="jerarquico/(?P<empresa_id>[^/.]+)")
    def analisis_jerarquico(self, request, empresa_id=None):
        """Obtiene análisis jerárquico de cuentas."""
        empresa = get_object_or_404(Empresa, id=empresa_id)
        nivel_max = int(request.query_params.get("nivel_max", 3))

        service = AnalyticsService(empresa)
        jerarquia = service.get_analisis_jerarquico_cuentas(nivel_max=nivel_max)

        serializer = AnalisisJerarquicoSerializer(jerarquia, many=True)
        return Response(serializer.data)


class PredictionsViewSet(viewsets.ModelViewSet):
    """
    API para predicciones financieras con Prophet.
    """

    serializer_class = PrediccionFinancieraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtra predicciones por empresa del usuario."""
        return PrediccionFinanciera.objects.filter(
            empresa__grupo__miembros=self.request.user
        ).select_related("empresa")

    @extend_schema(
        summary="Generar predicciones",
        description="Genera predicciones financieras usando Prophet",
        request=GenerarPrediccionesRequestSerializer,
        responses={200: PrediccionFinancieraSerializer(many=True)},
    )
    @action(detail=False, methods=["post"], url_path="generar/(?P<empresa_id>[^/.]+)")
    def generar(self, request, empresa_id=None):
        """Genera predicciones para una empresa."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        # Validar request
        serializer = GenerarPrediccionesRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = PredictionService(empresa)

        if data["tipo_prediccion"] == "TODOS":
            resultados = service.generar_todas_predicciones(
                dias_historicos=data["dias_historicos"],
                dias_futuros=data["dias_futuros"],
            )

            # Obtener predicciones guardadas
            predicciones = PrediccionFinanciera.objects.filter(
                empresa=empresa,
                fecha_generacion__gte=date.today() - timedelta(days=1),
            )

            return Response(
                {
                    "success": True,
                    "resultados": resultados,
                    "predicciones": PrediccionFinancieraSerializer(predicciones, many=True).data,
                }
            )
        else:
            resultado = service.generar_predicciones(
                tipo_prediccion=data["tipo_prediccion"],
                dias_historicos=data["dias_historicos"],
                dias_futuros=data["dias_futuros"],
                guardar=True,
            )

            if resultado["success"]:
                # Obtener predicciones guardadas
                predicciones = PrediccionFinanciera.objects.filter(
                    empresa=empresa,
                    tipo_prediccion=data["tipo_prediccion"],
                    fecha_generacion__gte=date.today() - timedelta(days=1),
                )

                return Response(
                    {
                        "success": True,
                        "resultado": resultado,
                        "predicciones": PrediccionFinancieraSerializer(
                            predicciones, many=True
                        ).data,
                    }
                )
            else:
                return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        summary="Análisis de tendencia",
        description="Analiza tendencias de predicciones guardadas",
        parameters=[
            OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter(
                "tipo",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                enum=["INGR", "GAST", "FLUJ", "UTIL"],
            ),
            OpenApiParameter("dias", OpenApiTypes.INT, OpenApiParameter.QUERY, default=30),
        ],
        responses={200: PrediccionTendenciaSerializer},
    )
    @action(detail=False, methods=["get"], url_path="tendencia/(?P<empresa_id>[^/.]+)")
    def analisis_tendencia(self, request, empresa_id=None):
        """Analiza tendencias de predicciones."""
        empresa = get_object_or_404(Empresa, id=empresa_id)
        tipo = request.query_params.get("tipo", "INGR")
        dias = int(request.query_params.get("dias", 30))

        fecha_inicio = date.today()
        fecha_fin = fecha_inicio + timedelta(days=dias)

        predicciones = PrediccionFinanciera.objects.filter(
            empresa=empresa,
            tipo_prediccion=tipo,
            fecha_prediccion__gte=fecha_inicio,
            fecha_prediccion__lte=fecha_fin,
        ).order_by("fecha_prediccion")

        if not predicciones.exists():
            return Response(
                {"error": "No hay predicciones disponibles"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Calcular tendencia
        valores = [float(p.valor_predicho) for p in predicciones]
        fechas = [p.fecha_prediccion for p in predicciones]

        primera_mitad = sum(valores[: len(valores) // 2]) / (len(valores) // 2)
        segunda_mitad = sum(valores[len(valores) // 2 :]) / (len(valores) - len(valores) // 2)
        cambio = (
            ((segunda_mitad - primera_mitad) / primera_mitad * 100) if primera_mitad != 0 else 0
        )

        if cambio > 5:
            tendencia = f"Creciente (+{cambio:.1f}%)"
        elif cambio < -5:
            tendencia = f"Decreciente ({cambio:.1f}%)"
        else:
            tendencia = f"Estable ({cambio:+.1f}%)"

        data = {
            "tipo_prediccion": tipo,
            "valores": valores,
            "fechas": fechas,
            "tendencia": tendencia,
            "cambio_porcentual": cambio,
            "promedio": sum(valores) / len(valores),
            "maximo": max(valores),
            "minimo": min(valores),
        }

        serializer = PrediccionTendenciaSerializer(data)
        return Response(serializer.data)


class EmbeddingsViewSet(viewsets.ModelViewSet):
    """
    API para búsqueda semántica y embeddings de cuentas.
    """

    serializer_class = EmpresaCuentaEmbeddingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtra embeddings por empresa del usuario."""
        return EmpresaCuentaEmbedding.objects.filter(
            cuenta__empresa__grupo__miembros=self.request.user
        ).select_related("cuenta")

    @extend_schema(
        summary="Generar embeddings",
        description="Genera embeddings para todas las cuentas de una empresa",
        parameters=[
            OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter(
                "force",
                OpenApiTypes.BOOL,
                OpenApiParameter.QUERY,
                default=False,
                description="Regenerar embeddings existentes",
            ),
        ],
        responses={200: {"type": "object"}},
    )
    @action(detail=False, methods=["post"], url_path="generar/(?P<empresa_id>[^/.]+)")
    def generar(self, request, empresa_id=None):
        """Genera embeddings para una empresa."""
        empresa = get_object_or_404(Empresa, id=empresa_id)
        force = request.query_params.get("force", "false").lower() == "true"

        service = EmbeddingService()
        nuevos, actualizados = service.generar_embeddings_empresa(empresa, force_regenerate=force)

        return Response(
            {
                "success": True,
                "empresa": empresa.nombre,
                "embeddings_nuevos": nuevos,
                "embeddings_actualizados": actualizados,
                "total": nuevos + actualizados,
            }
        )

    @extend_schema(
        summary="Búsqueda semántica",
        description="Busca cuentas similares usando búsqueda semántica",
        request=BusquedaSemanticaRequestSerializer,
        responses={200: EmbeddingSimilaritySerializer(many=True)},
    )
    @action(detail=False, methods=["post"], url_path="buscar/(?P<empresa_id>[^/.]+)")
    def buscar_semantica(self, request, empresa_id=None):
        """Búsqueda semántica de cuentas."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        # Validar request
        serializer = BusquedaSemanticaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = EmbeddingService()

        resultados = service.buscar_por_texto(
            texto_busqueda=data["texto"],
            empresa=empresa,
            limit=data["limit"],
            min_similarity=data["min_similarity"],
        )

        return Response(resultados)

    @extend_schema(
        summary="Recomendar cuentas",
        description="Recomienda cuentas contables para una transacción",
        request=RecomendacionCuentasRequestSerializer,
        responses={200: EmbeddingSimilaritySerializer(many=True)},
    )
    @action(detail=False, methods=["post"], url_path="recomendar/(?P<empresa_id>[^/.]+)")
    def recomendar_cuentas(self, request, empresa_id=None):
        """Recomienda cuentas para una transacción."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        # Validar request
        serializer = RecomendacionCuentasRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = EmbeddingService()

        recomendaciones = service.recomendar_cuentas(
            descripcion_transaccion=data["descripcion_transaccion"],
            empresa=empresa,
            top_k=data["top_k"],
        )

        return Response(recomendaciones)

    @extend_schema(
        summary="Clustering de cuentas",
        description="Agrupa cuentas similares usando K-means",
        parameters=[
            OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH),
            OpenApiParameter("n_clusters", OpenApiTypes.INT, OpenApiParameter.QUERY, default=5),
        ],
        responses={200: EmbeddingClusterSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="clusters/(?P<empresa_id>[^/.]+)")
    def obtener_clusters(self, request, empresa_id=None):
        """Obtiene clusters de cuentas similares."""
        empresa = get_object_or_404(Empresa, id=empresa_id)
        n_clusters = int(request.query_params.get("n_clusters", 5))

        service = EmbeddingService()
        clusters = service.obtener_clusters_cuentas(empresa, n_clusters=n_clusters)

        serializer = EmbeddingClusterSerializer(clusters, many=True)
        return Response(serializer.data)


class AnomaliesViewSet(viewsets.ModelViewSet):
    """
    API para detección y gestión de anomalías.
    """

    serializer_class = AnomaliaDetectadaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtra anomalías por empresa del usuario."""
        queryset = AnomaliaDetectada.objects.filter(
            empresa__grupo__miembros=self.request.user
        ).select_related("empresa", "revisada_por")

        # Filtros opcionales
        tipo = self.request.query_params.get("tipo")
        severidad = self.request.query_params.get("severidad")
        revisada = self.request.query_params.get("revisada")

        if tipo:
            queryset = queryset.filter(tipo_anomalia=tipo)
        if severidad:
            queryset = queryset.filter(severidad=severidad)
        if revisada is not None:
            queryset = queryset.filter(revisada=revisada.lower() == "true")

        return queryset.order_by("-fecha_deteccion")

    @extend_schema(
        summary="Detectar anomalías",
        description="Ejecuta detección de anomalías usando ML",
        request=DetectarAnomaliasRequestSerializer,
        responses={200: {"type": "object"}},
    )
    @action(detail=False, methods=["post"], url_path="detectar/(?P<empresa_id>[^/.]+)")
    def detectar(self, request, empresa_id=None):
        """Detecta anomalías en una empresa."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        # Validar request
        serializer = DetectarAnomaliasRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        service = AnomalyService(empresa)

        if data["tipo"] == "TODOS":
            resultado = service.detectar_todas_anomalias(
                dias_historicos=data["dias_historicos"], guardar=True
            )
        elif data["tipo"] == "MONTO":
            resultado = service.detectar_anomalias_monto(
                dias_historicos=data["dias_historicos"],
                contamination=data["contamination"],
                guardar=True,
            )
        elif data["tipo"] == "FRECUENCIA":
            resultado = service.detectar_anomalias_frecuencia(
                dias_historicos=data["dias_historicos"], guardar=True
            )
        elif data["tipo"] == "TEMPORAL":
            resultado = service.detectar_anomalias_temporales(
                dias_historicos=data["dias_historicos"], guardar=True
            )
        elif data["tipo"] == "PATRON":
            resultado = service.detectar_anomalias_patrones(
                dias_historicos=data["dias_historicos"], guardar=True
            )

        return Response(resultado)

    @extend_schema(
        summary="Estadísticas de anomalías",
        description="Obtiene estadísticas generales de anomalías",
        parameters=[
            OpenApiParameter("empresa_id", OpenApiTypes.INT, OpenApiParameter.PATH),
        ],
        responses={200: AnomaliaEstadisticasSerializer},
    )
    @action(detail=False, methods=["get"], url_path="estadisticas/(?P<empresa_id>[^/.]+)")
    def estadisticas(self, request, empresa_id=None):
        """Obtiene estadísticas de anomalías."""
        empresa = get_object_or_404(Empresa, id=empresa_id)

        total = AnomaliaDetectada.objects.filter(empresa=empresa).count()
        sin_revisar = AnomaliaDetectada.objects.filter(empresa=empresa, revisada=False).count()
        revisadas = total - sin_revisar
        falsos_positivos = AnomaliaDetectada.objects.filter(
            empresa=empresa, es_falso_positivo=True
        ).count()

        # Por tipo
        por_tipo = {}
        for tipo in ["MONTO", "FREQ", "PTRN", "CONT", "TEMP"]:
            count = AnomaliaDetectada.objects.filter(empresa=empresa, tipo_anomalia=tipo).count()
            if count > 0:
                por_tipo[tipo] = count

        # Por severidad
        por_severidad = {}
        for sev in ["CRITICA", "ALTA", "MEDIA", "BAJA"]:
            count = AnomaliaDetectada.objects.filter(empresa=empresa, severidad=sev).count()
            if count > 0:
                por_severidad[sev] = count

        # Recientes
        recientes = AnomaliaDetectada.objects.filter(empresa=empresa).order_by("-fecha_deteccion")[
            :5
        ]

        data = {
            "total": total,
            "sin_revisar": sin_revisar,
            "revisadas": revisadas,
            "falsos_positivos": falsos_positivos,
            "por_tipo": por_tipo,
            "por_severidad": por_severidad,
            "recientes": recientes,
        }

        serializer = AnomaliaEstadisticasSerializer(data)
        return Response(serializer.data)

    @extend_schema(
        summary="Revisar anomalía",
        description="Marca una anomalía como revisada",
        request=RevisarAnomaliaSerializer,
        responses={200: AnomaliaDetectadaSerializer},
    )
    @action(detail=True, methods=["post"], url_path="revisar")
    def revisar(self, request, pk=None):
        """Marca una anomalía como revisada."""
        anomalia = self.get_object()

        # Validar request
        serializer = RevisarAnomaliaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        # Actualizar anomalía
        anomalia.revisada = True
        anomalia.es_falso_positivo = data["es_falso_positivo"]
        anomalia.notas_revision = data.get("notas", "")
        anomalia.revisada_por = request.user
        anomalia.save()

        response_serializer = AnomaliaDetectadaSerializer(anomalia)
        return Response(response_serializer.data)
