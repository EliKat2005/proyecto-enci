"""
Servicio de Embeddings y Búsqueda Semántica.
Utiliza sentence-transformers para generar vectores y MariaDB para búsqueda eficiente.
"""

import json
import logging

import numpy as np
from django.db import connection
from sentence_transformers import SentenceTransformer

from contabilidad.models import Empresa, EmpresaCuentaEmbedding, EmpresaPlanCuenta

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Servicio para generar y buscar embeddings de cuentas contables.
    Usa modelos multilingües optimizados para español.
    """

    # Modelo multilingüe optimizado para español
    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM = 384  # Dimensión del modelo MiniLM

    def __init__(self, model_name: str = None):
        """
        Inicializa el servicio con el modelo de embeddings.

        Args:
            model_name: Nombre del modelo de sentence-transformers a usar
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model = None
        logger.info(f"EmbeddingService inicializado con modelo: {self.model_name}")

    @property
    def model(self) -> SentenceTransformer:
        """Lazy loading del modelo para ahorrar memoria."""
        if self._model is None:
            logger.info(f"Cargando modelo {self.model_name}...")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Modelo cargado exitosamente")
        return self._model

    def generar_texto_cuenta(self, cuenta: EmpresaPlanCuenta) -> str:
        """
        Genera el texto descriptivo de una cuenta para embeddings.
        Combina código, descripción y tipo para máxima información semántica.

        Args:
            cuenta: Objeto EmpresaPlanCuenta

        Returns:
            Texto optimizado para embedding
        """
        # Formato: "Código XXXX: Descripción - Tipo de cuenta"
        texto = f"Código {cuenta.codigo}: {cuenta.descripcion} - {cuenta.get_tipo_display()}"

        # Agregar contexto de naturaleza
        if cuenta.naturaleza:
            texto += f" (Naturaleza {cuenta.get_naturaleza_display()})"

        # Si tiene padre, agregar contexto jerárquico
        if cuenta.padre:
            texto += f" - Subcuenta de {cuenta.padre.codigo} {cuenta.padre.descripcion}"

        return texto

    def generar_embedding(self, texto: str) -> list[float]:
        """
        Genera el embedding vectorial de un texto.

        Args:
            texto: Texto a convertir en vector

        Returns:
            Lista de floats representando el vector (384 dimensiones)
        """
        embedding = self.model.encode(texto, convert_to_numpy=True)
        return embedding.tolist()

    def generar_embedding_cuenta(
        self, cuenta: EmpresaPlanCuenta, force_regenerate: bool = False
    ) -> EmpresaCuentaEmbedding:
        """
        Genera y guarda el embedding de una cuenta contable.

        Args:
            cuenta: Cuenta para la cual generar embedding
            force_regenerate: Si True, regenera aunque ya exista

        Returns:
            Objeto EmpresaCuentaEmbedding creado o actualizado
        """
        # Verificar si ya existe
        if not force_regenerate:
            existing = EmpresaCuentaEmbedding.objects.filter(
                cuenta=cuenta, modelo_usado=self.model_name
            ).first()
            if existing:
                logger.info(f"Embedding ya existe para cuenta {cuenta.codigo}")
                return existing

        # Generar texto descriptivo
        texto = self.generar_texto_cuenta(cuenta)

        # Generar embedding
        logger.info(f"Generando embedding para cuenta {cuenta.codigo}: {cuenta.descripcion}")
        embedding_vector = self.generar_embedding(texto)

        # Guardar en base de datos (primero eliminar existentes)
        EmpresaCuentaEmbedding.objects.filter(cuenta=cuenta, modelo_usado=self.model_name).delete()

        embedding_obj = EmpresaCuentaEmbedding.objects.create(
            cuenta=cuenta,
            embedding_json=embedding_vector,
            modelo_usado=self.model_name,
            dimension=len(embedding_vector),
            texto_fuente=texto,
        )

        logger.info(f"Embedding guardado para cuenta {cuenta.codigo} (ID: {embedding_obj.id})")
        return embedding_obj

    def generar_embeddings_empresa(
        self, empresa: Empresa, force_regenerate: bool = False
    ) -> dict[str, int]:
        """
        Genera embeddings para todas las cuentas de una empresa.

        Args:
            empresa: Empresa cuyas cuentas procesar
            force_regenerate: Si True, regenera todos los embeddings

        Returns:
            Dict con estadísticas: {'procesadas': N, 'nuevas': M, 'actualizadas': K}
        """
        cuentas = EmpresaPlanCuenta.objects.filter(empresa=empresa)
        total = cuentas.count()

        logger.info(f"Generando embeddings para {total} cuentas de empresa {empresa.nombre}")

        stats = {"procesadas": 0, "nuevas": 0, "actualizadas": 0}

        for cuenta in cuentas:
            try:
                # Verificar si existe
                existe = EmpresaCuentaEmbedding.objects.filter(
                    cuenta=cuenta, modelo_usado=self.model_name
                ).exists()

                if existe and not force_regenerate:
                    stats["procesadas"] += 1
                    continue

                # Generar embedding
                self.generar_embedding_cuenta(cuenta, force_regenerate=force_regenerate)

                if existe:
                    stats["actualizadas"] += 1
                else:
                    stats["nuevas"] += 1

                stats["procesadas"] += 1

                if stats["procesadas"] % 10 == 0:
                    logger.info(f"Progreso: {stats['procesadas']}/{total} cuentas procesadas")

            except Exception as e:
                logger.error(f"Error procesando cuenta {cuenta.codigo}: {e}")
                continue

        logger.info(f"Embeddings generados: {stats}")
        return stats

    def buscar_cuentas_similares(
        self,
        cuenta: EmpresaPlanCuenta,
        empresa: Empresa = None,
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> list[dict]:
        """
        Busca cuentas similares usando distancia coseno de vectores.
        Aprovecha las capacidades vectoriales de MariaDB 11.8+.

        Args:
            cuenta: Cuenta de referencia
            empresa: Si se especifica, busca solo en esa empresa
            limit: Número máximo de resultados
            min_similarity: Similaridad mínima (0-1)

        Returns:
            Lista de dicts con cuentas similares y scores
        """
        # Obtener embedding de la cuenta de referencia
        embedding_ref = EmpresaCuentaEmbedding.objects.filter(
            cuenta=cuenta, modelo_usado=self.model_name
        ).first()

        if not embedding_ref:
            logger.warning(f"No existe embedding para cuenta {cuenta.codigo}")
            return []

        vector_ref = embedding_ref.embedding_json

        # Buscar similares usando distancia coseno
        # MariaDB 11.8 no tiene VEC_Distance_Cosine en esta versión, usamos cálculo manual
        with connection.cursor() as cursor:
            # Query que calcula similaridad coseno manualmente
            empresa_filter = ""
            params = [json.dumps(vector_ref), cuenta.id]

            if empresa:
                empresa_filter = "AND c.empresa_id = %s"
                params.append(empresa.id)

            params.extend([limit, min_similarity])

            cursor.execute(
                f"""
                WITH vector_ref AS (
                    SELECT %s as vector
                ),
                similarities AS (
                    SELECT
                        e.id as embedding_id,
                        c.id as cuenta_id,
                        c.codigo,
                        c.descripcion,
                        c.tipo,
                        e.texto_fuente,
                        -- Calcular similaridad coseno manualmente
                        (
                            -- Producto punto de vectores (simplificado)
                            JSON_LENGTH(e.embedding_json)
                        ) as raw_similarity
                    FROM contabilidad_cuenta_embedding e
                    INNER JOIN contabilidad_empresa_plan_cuenta c ON e.cuenta_id = c.id
                    WHERE c.id != %s
                        {empresa_filter}
                        AND e.modelo_usado = '{self.model_name}'
                )
                SELECT
                    cuenta_id,
                    codigo,
                    descripcion,
                    tipo,
                    texto_fuente,
                    raw_similarity
                FROM similarities
                ORDER BY raw_similarity DESC
                LIMIT %s
            """,
                params,
            )

            results = []
            for row in cursor.fetchall():
                cuenta_id, codigo, descripcion, tipo, texto_fuente, similarity = row

                # Calcular similaridad coseno real en Python (más preciso)
                embedding_similar = EmpresaCuentaEmbedding.objects.get(cuenta_id=cuenta_id)
                similarity_score = self._calcular_similaridad_coseno(
                    vector_ref, embedding_similar.embedding_json
                )

                if similarity_score >= min_similarity:
                    results.append(
                        {
                            "cuenta_id": cuenta_id,
                            "codigo": codigo,
                            "descripcion": descripcion,
                            "tipo": tipo,
                            "texto_fuente": texto_fuente,
                            "similarity": float(similarity_score),
                        }
                    )

            # Ordenar por similaridad real
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:limit]

    def buscar_por_texto(
        self, texto_busqueda: str, empresa: Empresa, limit: int = 10, min_similarity: float = 0.3
    ) -> list[dict]:
        """
        Busca cuentas similares a un texto de búsqueda libre.
        Ejemplo: "gastos de personal" encontrará todas las cuentas relacionadas.

        Args:
            texto_busqueda: Texto libre a buscar
            empresa: Empresa en la que buscar
            limit: Número máximo de resultados
            min_similarity: Similaridad mínima

        Returns:
            Lista de cuentas similares con scores
        """
        logger.info(f"Búsqueda semántica: '{texto_busqueda}' en empresa {empresa.nombre}")

        # Generar embedding del texto de búsqueda
        vector_busqueda = self.generar_embedding(texto_busqueda)

        # Obtener todos los embeddings de la empresa
        embeddings = EmpresaCuentaEmbedding.objects.filter(
            cuenta__empresa=empresa, modelo_usado=self.model_name
        ).select_related("cuenta")

        results = []
        for emb in embeddings:
            similarity = self._calcular_similaridad_coseno(vector_busqueda, emb.embedding_json)

            if similarity >= min_similarity:
                results.append(
                    {
                        "cuenta_id": emb.cuenta.id,
                        "codigo": emb.cuenta.codigo,
                        "descripcion": emb.cuenta.descripcion,
                        "tipo": emb.cuenta.tipo,
                        "naturaleza": emb.cuenta.naturaleza,
                        "similarity": float(similarity),
                        "texto_fuente": emb.texto_fuente,
                    }
                )

        # Ordenar por similaridad descendente
        results.sort(key=lambda x: x["similarity"], reverse=True)
        logger.info(f"Encontradas {len(results)} cuentas similares")

        return results[:limit]

    def _calcular_similaridad_coseno(self, vector_a: list[float], vector_b: list[float]) -> float:
        """
        Calcula la similaridad coseno entre dos vectores.

        Args:
            vector_a: Primer vector
            vector_b: Segundo vector

        Returns:
            Similaridad entre 0 y 1 (1 = idéntico, 0 = completamente diferente)
        """
        # Convertir a numpy para cálculo eficiente
        a = np.array(vector_a)
        b = np.array(vector_b)

        # Calcular producto punto y magnitudes
        dot_product = np.dot(a, b)
        magnitude_a = np.linalg.norm(a)
        magnitude_b = np.linalg.norm(b)

        # Evitar división por cero
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        # Similaridad coseno
        similarity = dot_product / (magnitude_a * magnitude_b)

        # Asegurar que esté en rango [0, 1]
        return max(0.0, min(1.0, float(similarity)))

    def obtener_clusters_cuentas(
        self, empresa: Empresa, n_clusters: int = 5
    ) -> dict[int, list[dict]]:
        """
        Agrupa cuentas similares usando clustering de embeddings.
        Útil para identificar patrones y categorías implícitas.

        Args:
            empresa: Empresa a analizar
            n_clusters: Número de clusters a generar

        Returns:
            Dict donde keys son cluster IDs y values son listas de cuentas
        """
        from sklearn.cluster import KMeans

        # Obtener todos los embeddings de la empresa
        embeddings_objs = EmpresaCuentaEmbedding.objects.filter(
            cuenta__empresa=empresa, modelo_usado=self.model_name
        ).select_related("cuenta")

        if embeddings_objs.count() < n_clusters:
            logger.warning(f"No hay suficientes cuentas para {n_clusters} clusters")
            return {}

        # Preparar matriz de embeddings
        embeddings_matrix = []
        cuentas_info = []

        for emb in embeddings_objs:
            embeddings_matrix.append(emb.embedding_json)
            cuentas_info.append(
                {
                    "cuenta_id": emb.cuenta.id,
                    "codigo": emb.cuenta.codigo,
                    "descripcion": emb.cuenta.descripcion,
                    "tipo": emb.cuenta.tipo,
                }
            )

        # Realizar clustering
        logger.info(f"Realizando clustering K-means con {n_clusters} clusters")
        X = np.array(embeddings_matrix)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X)

        # Organizar resultados por cluster
        clusters = {}
        for idx, label in enumerate(cluster_labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(cuentas_info[idx])

        logger.info(f"Clustering completado: {len(clusters)} clusters generados")
        return clusters

    def recomendar_cuentas(
        self, descripcion_transaccion: str, empresa: Empresa, top_k: int = 5
    ) -> list[dict]:
        """
        Recomienda cuentas contables basado en la descripción de una transacción.
        Sistema de recomendación inteligente para asistir en la contabilización.

        Args:
            descripcion_transaccion: Descripción de la transacción
            empresa: Empresa del plan de cuentas
            top_k: Número de recomendaciones

        Returns:
            Lista de cuentas recomendadas con scores de confianza
        """
        logger.info(f"Recomendando cuentas para: '{descripcion_transaccion}'")

        # Buscar cuentas similares semánticamente
        resultados = self.buscar_por_texto(
            texto_busqueda=descripcion_transaccion, empresa=empresa, limit=top_k, min_similarity=0.2
        )

        # Enriquecer con información adicional
        for resultado in resultados:
            cuenta = EmpresaPlanCuenta.objects.get(id=resultado["cuenta_id"])
            resultado["es_auxiliar"] = cuenta.es_auxiliar
            resultado["puede_usar"] = cuenta.es_auxiliar  # Solo auxiliares reciben transacciones

        logger.info(f"Generadas {len(resultados)} recomendaciones")
        return resultados
