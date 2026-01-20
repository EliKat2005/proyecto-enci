"""
Serializers para las APIs de Machine Learning y Analytics.
"""

from rest_framework import serializers

from contabilidad.models import (
    AnomaliaDetectada,
    Empresa,
    EmpresaCuentaEmbedding,
    EmpresaMetrica,
    PrediccionFinanciera,
)


class EmpresaBasicSerializer(serializers.ModelSerializer):
    """Serializer básico para Empresa."""

    class Meta:
        model = Empresa
        fields = ["id", "nombre"]


class EmpresaMetricaSerializer(serializers.ModelSerializer):
    """Serializer para métricas financieras."""

    empresa = EmpresaBasicSerializer(read_only=True)
    empresa_id = serializers.PrimaryKeyRelatedField(
        queryset=Empresa.objects.all(), source="empresa", write_only=True
    )

    class Meta:
        model = EmpresaMetrica
        fields = [
            "id",
            "empresa",
            "empresa_id",
            "periodo_inicio",
            "periodo_fin",
            "fecha_calculo",
            # Métricas de liquidez
            "activo_corriente",
            "pasivo_corriente",
            "razon_corriente",
            "prueba_acida",
            # Métricas de rentabilidad
            "ingresos_totales",
            "gastos_totales",
            "utilidad_neta",
            "margen_neto",
            "roe",
            "roa",
            # Métricas de endeudamiento
            "total_activos",
            "total_pasivos",
            "total_patrimonio",
            "razon_endeudamiento",
            # Métricas operacionales
            "num_transacciones",
            "num_cuentas_activas",
        ]
        read_only_fields = ["id", "fecha_calculo"]


class EmpresaCuentaEmbeddingSerializer(serializers.ModelSerializer):
    """Serializer para embeddings de cuentas."""

    cuenta_codigo = serializers.CharField(source="cuenta.codigo", read_only=True)
    cuenta_descripcion = serializers.CharField(source="cuenta.descripcion", read_only=True)
    cuenta_tipo = serializers.CharField(source="cuenta.tipo", read_only=True)

    class Meta:
        model = EmpresaCuentaEmbedding
        fields = [
            "id",
            "cuenta",
            "cuenta_codigo",
            "cuenta_descripcion",
            "cuenta_tipo",
            "texto_fuente",
            "embedding_json",
            "modelo_usado",
            "dimension",
            "fecha_generacion",
        ]
        read_only_fields = ["id", "fecha_generacion"]


class EmbeddingSimilaritySerializer(serializers.Serializer):
    """Serializer para resultados de búsqueda por similaridad."""

    cuenta_id = serializers.IntegerField()
    codigo = serializers.CharField()
    descripcion = serializers.CharField()
    tipo = serializers.CharField()
    similaridad = serializers.FloatField()
    texto_fuente = serializers.CharField()


class EmbeddingClusterSerializer(serializers.Serializer):
    """Serializer para resultados de clustering."""

    cluster_id = serializers.IntegerField()
    cuentas = serializers.ListField(child=serializers.DictField())
    num_cuentas = serializers.IntegerField()
    distribucion_tipos = serializers.DictField()


class PrediccionFinancieraSerializer(serializers.ModelSerializer):
    """Serializer para predicciones financieras."""

    empresa = EmpresaBasicSerializer(read_only=True)
    empresa_id = serializers.PrimaryKeyRelatedField(
        queryset=Empresa.objects.all(), source="empresa", write_only=True
    )
    tipo_prediccion_display = serializers.CharField(
        source="get_tipo_prediccion_display", read_only=True
    )

    class Meta:
        model = PrediccionFinanciera
        fields = [
            "id",
            "empresa",
            "empresa_id",
            "tipo_prediccion",
            "tipo_prediccion_display",
            "fecha_prediccion",
            "valor_predicho",
            "limite_inferior",
            "limite_superior",
            "confianza",
            "modelo_usado",
            "metricas_modelo",
            "datos_entrenamiento",
            "fecha_generacion",
        ]
        read_only_fields = ["id", "fecha_generacion"]


class PrediccionTendenciaSerializer(serializers.Serializer):
    """Serializer para análisis de tendencias de predicciones."""

    tipo_prediccion = serializers.CharField()
    valores = serializers.ListField(child=serializers.FloatField())
    fechas = serializers.ListField(child=serializers.DateField())
    tendencia = serializers.CharField()
    cambio_porcentual = serializers.FloatField()
    promedio = serializers.FloatField()
    maximo = serializers.FloatField()
    minimo = serializers.FloatField()


class AnomaliaDetectadaSerializer(serializers.ModelSerializer):
    """Serializer para anomalías detectadas."""

    empresa = EmpresaBasicSerializer(read_only=True)
    empresa_id = serializers.PrimaryKeyRelatedField(
        queryset=Empresa.objects.all(), source="empresa", write_only=True
    )
    tipo_anomalia_display = serializers.CharField(
        source="get_tipo_anomalia_display", read_only=True
    )
    revisada_por_username = serializers.CharField(
        source="revisada_por.username", read_only=True, allow_null=True
    )

    class Meta:
        model = AnomaliaDetectada
        fields = [
            "id",
            "empresa",
            "empresa_id",
            "asiento_id",
            "transaccion_id",
            "tipo_anomalia",
            "tipo_anomalia_display",
            "severidad",
            "score_anomalia",
            "descripcion",
            "algoritmo_usado",
            "fecha_deteccion",
            "revisada",
            "es_falso_positivo",
            "notas_revision",
            "fecha_revision",
            "revisada_por",
            "revisada_por_username",
        ]
        read_only_fields = ["id", "fecha_deteccion"]


class AnomaliaEstadisticasSerializer(serializers.Serializer):
    """Serializer para estadísticas de anomalías."""

    total = serializers.IntegerField()
    sin_revisar = serializers.IntegerField()
    revisadas = serializers.IntegerField()
    falsos_positivos = serializers.IntegerField()
    por_tipo = serializers.DictField()
    por_severidad = serializers.DictField()
    recientes = AnomaliaDetectadaSerializer(many=True)


class MetricasFinancierasSerializer(serializers.Serializer):
    """Serializer para métricas financieras calculadas en tiempo real."""

    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()
    liquidez = serializers.DictField()
    rentabilidad = serializers.DictField()
    endeudamiento = serializers.DictField()
    actividad = serializers.DictField()


class TendenciaIngresosGastosSerializer(serializers.Serializer):
    """Serializer para tendencias de ingresos y gastos."""

    periodos = serializers.ListField(child=serializers.CharField())
    ingresos = serializers.ListField(child=serializers.FloatField())
    gastos = serializers.ListField(child=serializers.FloatField())
    ingresos_ma = serializers.ListField(child=serializers.FloatField())
    gastos_ma = serializers.ListField(child=serializers.FloatField())
    crecimiento_ingresos = serializers.ListField(child=serializers.FloatField())
    crecimiento_gastos = serializers.ListField(child=serializers.FloatField())


class TopCuentasSerializer(serializers.Serializer):
    """Serializer para ranking de cuentas."""

    cuenta_id = serializers.IntegerField()
    codigo = serializers.CharField()
    descripcion = serializers.CharField()
    tipo = serializers.CharField()
    monto_total = serializers.FloatField()
    num_transacciones = serializers.IntegerField()
    ranking = serializers.IntegerField()


class ComposicionPatrimonialSerializer(serializers.Serializer):
    """Serializer para composición patrimonial."""

    tipo = serializers.CharField()
    monto = serializers.FloatField()
    porcentaje = serializers.FloatField()
    num_cuentas = serializers.IntegerField()


class AnalisisJerarquicoSerializer(serializers.Serializer):
    """Serializer para análisis jerárquico de cuentas."""

    cuenta_id = serializers.IntegerField()
    codigo = serializers.CharField()
    descripcion = serializers.CharField()
    tipo = serializers.CharField()
    nivel = serializers.IntegerField()
    padre_id = serializers.IntegerField(allow_null=True)
    saldo = serializers.FloatField()
    num_transacciones = serializers.IntegerField()
    hijos = serializers.ListField(child=serializers.DictField())


class BusquedaSemanticaRequestSerializer(serializers.Serializer):
    """Serializer para request de búsqueda semántica."""

    texto = serializers.CharField(required=True, min_length=3)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50)
    min_similarity = serializers.FloatField(default=0.5, min_value=0.0, max_value=1.0)


class RecomendacionCuentasRequestSerializer(serializers.Serializer):
    """Serializer para request de recomendación de cuentas."""

    descripcion_transaccion = serializers.CharField(required=True, min_length=3)
    top_k = serializers.IntegerField(default=5, min_value=1, max_value=20)


class GenerarPrediccionesRequestSerializer(serializers.Serializer):
    """Serializer para request de generación de predicciones."""

    tipo_prediccion = serializers.ChoiceField(
        choices=["INGR", "GAST", "FLUJ", "UTIL", "TODOS"], default="TODOS"
    )
    dias_historicos = serializers.IntegerField(default=365, min_value=30, max_value=730)
    dias_futuros = serializers.IntegerField(default=30, min_value=1, max_value=365)


class DetectarAnomaliasRequestSerializer(serializers.Serializer):
    """Serializer para request de detección de anomalías."""

    tipo = serializers.ChoiceField(
        choices=["MONTO", "FRECUENCIA", "TEMPORAL", "PATRON", "TODOS"], default="TODOS"
    )
    dias_historicos = serializers.IntegerField(default=180, min_value=30, max_value=730)
    contamination = serializers.FloatField(default=0.05, min_value=0.01, max_value=0.5)


class RevisarAnomaliaSerializer(serializers.Serializer):
    """Serializer para revisar una anomalía."""

    es_falso_positivo = serializers.BooleanField(default=False)
    notas = serializers.CharField(required=False, allow_blank=True)


# ==================== SERIALIZERS PARA SERVICIOS AVANZADOS (FASES 2-4) ====================


class BusquedaBooleanSerializer(serializers.Serializer):
    """Serializer para búsqueda con operadores booleanos."""

    query = serializers.CharField(required=True, help_text='Query con operadores (+, -, *, "")')
    limit = serializers.IntegerField(default=10, min_value=1, max_value=100)
    mode = serializers.ChoiceField(
        choices=["NATURAL", "BOOLEAN", "QUERY_EXPANSION"],
        default="NATURAL",
        help_text="Modo de búsqueda FULLTEXT",
    )


class AutocompleteSerializer(serializers.Serializer):
    """Serializer para autocompletado."""

    partial_query = serializers.CharField(required=True, help_text="Query parcial")
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50)


class AutocompleteResultSerializer(serializers.Serializer):
    """Serializer para resultado de autocompletado."""

    id = serializers.IntegerField()
    codigo = serializers.CharField()
    descripcion = serializers.CharField()
    tipo = serializers.CharField()
    es_auxiliar = serializers.BooleanField()
    label = serializers.CharField()
    uso_frecuencia = serializers.IntegerField()


class VectorMigrationSerializer(serializers.Serializer):
    """Serializer para migración a VECTOR storage."""

    dry_run = serializers.BooleanField(default=True)


class VectorMigrationResultSerializer(serializers.Serializer):
    """Serializer para resultado de migración."""

    success = serializers.BooleanField()
    version = serializers.CharField(required=False)
    mensaje = serializers.CharField()
    embeddings_migrados = serializers.IntegerField(required=False)
    embeddings_a_migrar = serializers.IntegerField(required=False)
    indice_creado = serializers.BooleanField(required=False)
    pasos_siguientes = serializers.ListField(child=serializers.CharField(), required=False)


class FinancialHealthScoreSerializer(serializers.Serializer):
    """Serializer para score de salud financiera."""

    score_total = serializers.FloatField()
    clasificacion = serializers.CharField()
    factores = serializers.DictField()
    metricas_base = serializers.DictField()


class AccountCorrelationSerializer(serializers.Serializer):
    """Serializer para correlación de cuentas."""

    cuenta_1 = serializers.IntegerField()
    codigo_1 = serializers.CharField()
    descripcion_1 = serializers.CharField()
    tipo_1 = serializers.CharField()
    cuenta_2 = serializers.IntegerField()
    codigo_2 = serializers.CharField()
    descripcion_2 = serializers.CharField()
    tipo_2 = serializers.CharField()
    dias_comunes = serializers.IntegerField()
    coef_correlacion = serializers.FloatField()


class EMAForecastRequestSerializer(serializers.Serializer):
    """Serializer para predicción con EMA."""

    tipo_cuenta = serializers.ChoiceField(choices=["INGRESO", "GASTO", "COSTO"])
    dias_futuros = serializers.IntegerField(default=30, min_value=1, max_value=365)
    alpha = serializers.FloatField(default=0.3, min_value=0.1, max_value=0.5)


class EMAForecastResultSerializer(serializers.Serializer):
    """Serializer para resultado de EMA."""

    success = serializers.BooleanField()
    tipo_cuenta = serializers.CharField()
    dias_historicos = serializers.IntegerField(required=False)
    dias_futuros = serializers.IntegerField(required=False)
    alpha = serializers.FloatField(required=False)
    ema_actual = serializers.FloatField(required=False)
    prediccion_diaria = serializers.FloatField(required=False)
    prediccion_total = serializers.FloatField(required=False)
    intervalo_confianza = serializers.DictField(required=False)
    historico = serializers.ListField(required=False)
    error = serializers.CharField(required=False)


class RealtimeDashboardSerializer(serializers.Serializer):
    """Serializer para dashboard en tiempo real."""

    timestamp = serializers.CharField()
    has_data = serializers.BooleanField()
    periodo_dias = serializers.IntegerField(required=False)
    ultima_actividad = serializers.CharField(required=False, allow_null=True)
    metricas = serializers.DictField(required=False)
    actividad = serializers.DictField(required=False)
    mensaje = serializers.CharField(required=False)
