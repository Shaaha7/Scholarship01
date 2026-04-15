"""
Embedding Service – BGE-M3 Multilingual Embeddings
=====================================================
Uses BAAI/bge-m3 which supports Tamil, English, and cross-lingual retrieval.
Dimension: 1024
"""
import asyncio
import logging
import threading
import time
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)


_model_lock = threading.Lock()
_cached_model = None
_cached_error = None
_cached_error_at = 0.0
_load_in_progress = False
_load_event = threading.Event()

# After a load failure, wait before trying again. This prevents every request from
# triggering a slow HuggingFace download attempt when the environment has no access.
_error_cooldown_sec = 120
_in_progress_wait_sec = 1.5  # If another thread is loading, fail fast.


def _get_model():
    """Load BGE-M3 model once and cache it; cache failures briefly (thread-safe)."""
    global _cached_model, _cached_error, _cached_error_at

    global _cached_model, _cached_error, _cached_error_at, _load_in_progress

    # First, decide whether this thread is allowed to start loading.
    with _model_lock:
        if _cached_model is not None:
            return _cached_model

        if _cached_error is not None and (time.time() - _cached_error_at) < _error_cooldown_sec:
            raise _cached_error

        if _load_in_progress:
            # Another thread is already loading; do not start a second download.
            # Fail fast so callers can fall back to SQL-only.
            should_wait = True
        else:
            _load_in_progress = True
            _load_event.clear()
            should_wait = False

    if should_wait:
        # Wait briefly for the in-progress loader to finish.
        finished = _load_event.wait(timeout=_in_progress_wait_sec)
        with _model_lock:
            if _cached_model is not None:
                return _cached_model
            if _cached_error is not None and (time.time() - _cached_error_at) < _error_cooldown_sec:
                raise _cached_error
        raise RuntimeError("Embedding model loading is in progress")

    # This thread performs the actual model load.
    try:
        from FlagEmbedding import BGEM3FlagModel

        logger.info(f"Loading BGE-M3 model on {settings.EMBEDDING_DEVICE}...")
        model = BGEM3FlagModel(
            settings.EMBEDDING_MODEL,
            use_fp16=(settings.EMBEDDING_DEVICE == "cuda"),
            device=settings.EMBEDDING_DEVICE,
        )
        logger.info("BGE-M3 model loaded successfully.")

        with _model_lock:
            _cached_model = model
            _cached_error = None
        return model
    except ImportError:
        logger.warning("FlagEmbedding not installed. Using sentence-transformers fallback.")
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(settings.EMBEDDING_MODEL, device=settings.EMBEDDING_DEVICE)
        with _model_lock:
            _cached_model = model
            _cached_error = None
        return model
    except Exception as e:
        logger.error(f"BGE-M3 model load failed: {e}")
        with _model_lock:
            _cached_error = e
            _cached_error_at = time.time()
        raise
    finally:
        with _model_lock:
            _load_in_progress = False
            _load_event.set()


class EmbeddingService:
    """Async wrapper around BGE-M3 for query and document embedding."""

    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._embed_sync, text
        )

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of documents."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self._embed_batch_sync, texts
        )

    def _embed_sync(self, text: str) -> List[float]:
        model = _get_model()
        try:
            # BGE-M3 FlagEmbedding API
            result = model.encode(
                [text],
                batch_size=1,
                max_length=512,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
            return result["dense_vecs"][0].tolist()
        except AttributeError:
            # sentence-transformers fallback
            embedding = model.encode(text, normalize_embeddings=True)
            return embedding.tolist()

    def _embed_batch_sync(self, texts: List[str]) -> List[List[float]]:
        model = _get_model()
        try:
            result = model.encode(
                texts,
                batch_size=16,
                max_length=512,
                return_dense=True,
                return_sparse=False,
                return_colbert_vecs=False,
            )
            return [vec.tolist() for vec in result["dense_vecs"]]
        except AttributeError:
            embeddings = model.encode(texts, normalize_embeddings=True, batch_size=16)
            return [e.tolist() for e in embeddings]


# Lightweight embedding for testing (no model required)
class MockEmbeddingService(EmbeddingService):
    """Mock embedding service for testing without GPU/model."""
    import random

    async def embed_query(self, text: str) -> List[float]:
        import random
        return [random.random() for _ in range(1024)]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        import random
        return [[random.random() for _ in range(1024)] for _ in texts]
