"""
Semantic Vector Embedding & Cosine Similarity Service.

Provides dense vector semantic comparison between candidate resume text
and job description content using SentenceTransformers with an adaptive
mathematical fallback for lightweight and fast test environments.
"""

import math
import re
from collections import Counter

try:
    import numpy as np
except ImportError:
    np = None

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    Computes semantic similarity between text documents.
    Uses SentenceTransformers ('all-MiniLM-L6-v2') when available,
    with an optimized vectorized TF-IDF cosine similarity fallback.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.embedding_model_name
        self._model = None
        self._model_load_attempted = False
        self._cache: dict[str, list[float]] = {}

    def _lazy_load_model(self) -> None:
        """Lazy load SentenceTransformers model on first real inference."""
        if self._model_load_attempted:
            return

        self._model_load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading SentenceTransformer model: '%s'...", self.model_name)
            self._model = SentenceTransformer(self.model_name)
            logger.info("SentenceTransformer model loaded successfully.")
        except Exception as exc:
            logger.warning(
                "Could not load SentenceTransformer (%s). Falling back to vectorized cosine engine: %s",
                self.model_name,
                exc,
            )
            self._model = None

    def get_embedding(self, text: str) -> list[float]:
        """
        Generate dense embedding vector for input text with caching.
        """
        cleaned = text.strip()
        if not cleaned:
            return [0.0] * 384

        cache_key = hash(cleaned[:1000])
        if cache_key in self._cache:
            return self._cache[cache_key]

        self._lazy_load_model()

        if self._model is not None:
            try:
                vector = self._model.encode(cleaned, normalize_embeddings=True)
                emb_list = vector.tolist()
                self._cache[cache_key] = emb_list
                return emb_list
            except Exception as exc:
                logger.error("SentenceTransformer inference failed: %s. Using fallback.", exc)

        # Fallback pseudo-dense normalized embedding
        emb = self._compute_fallback_vector(cleaned)
        self._cache[cache_key] = emb
        return emb

    def calculate_similarity(self, text_a: str, text_b: str) -> float:
        """
        Calculates cosine similarity between two texts (normalized from 0.0 to 1.0).
        """
        if not text_a.strip() or not text_b.strip():
            return 0.0

        self._lazy_load_model()

        if self._model is not None:
            try:
                emb_a = np.array(self.get_embedding(text_a))
                emb_b = np.array(self.get_embedding(text_b))
                # Cosine similarity of unit vectors is their dot product
                dot_product = float(np.dot(emb_a, emb_b))
                # Clip to [0.0, 1.0] range
                return max(0.0, min(1.0, (dot_product + 1.0) / 2.0 if dot_product < 0 else dot_product))
            except Exception as exc:
                logger.error("Cosine calculation failed on dense vectors: %s. Using fallback.", exc)

        return self._compute_fallback_cosine_similarity(text_a, text_b)

    def _compute_fallback_vector(self, text: str, dimensions: int = 384) -> list[float]:
        """Deterministic hash-based dense embedding fallback vector."""
        words = re.findall(r"\w+", text.lower())
        if np is not None:
            vec = np.zeros(dimensions, dtype=np.float32)
            for i, word in enumerate(words):
                h = hash(word) % dimensions
                vec[h] += 1.0 / (1.0 + math.log(i + 1))

            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            return vec.tolist()

        raw_vec = [0.0] * dimensions
        for i, word in enumerate(words):
            h = hash(word) % dimensions
            raw_vec[h] += 1.0 / (1.0 + math.log(i + 1))

        norm = math.sqrt(sum(x * x for x in raw_vec))
        if norm > 0:
            raw_vec = [x / norm for x in raw_vec]
        return raw_vec

    @staticmethod
    def _compute_fallback_cosine_similarity(text_a: str, text_b: str) -> float:
        """
        Token-frequency cosine similarity algorithm.
        Robust, zero-dependency mathematical fallback.
        """
        tokens_a = re.findall(r"\w+", text_a.lower())
        tokens_b = re.findall(r"\w+", text_b.lower())

        if not tokens_a or not tokens_b:
            return 0.0

        vec_a = Counter(tokens_a)
        vec_b = Counter(tokens_b)

        intersection = set(vec_a.keys()) & set(vec_b.keys())
        numerator = sum(vec_a[x] * vec_b[x] for x in intersection)

        sum1 = sum(vec_a[x] ** 2 for x in vec_a.keys())
        sum2 = sum(vec_b[x] ** 2 for x in vec_b.keys())
        denominator = math.sqrt(sum1) * math.sqrt(sum2)

        if not denominator:
            return 0.0

        return round(float(numerator) / denominator, 4)


# Singleton embedding service
embedding_service = EmbeddingService()
