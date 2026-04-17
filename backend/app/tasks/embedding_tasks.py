"""
Embedding Tasks – Async embedding generation
=============================================
Background tasks for generating and caching embeddings.
"""
from app.tasks.celery_app import celery_app
from app.services.embedding_service import embedding_service
from app.services.redis_service import redis_service
import hashlib


@celery_app.task(bind=True, max_retries=3)
def generate_embedding_task(self, text: str):
    """Generate embedding for text and cache it."""
    try:
        # Generate hash for caching
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Check cache first
        cached = redis_service.get_cached_embedding(text_hash)
        if cached:
            return cached
        
        # Generate embedding
        embedding = embedding_service.generate_embedding(text)
        
        # Cache the result
        redis_service.cache_embedding(text_hash, embedding)
        
        return embedding
    except Exception as e:
        self.retry(exc=e, countdown=60)


@celery_app.task
def batch_generate_embeddings(texts: list[str]):
    """Generate embeddings for multiple texts in batch."""
    embeddings = []
    for text in texts:
        try:
            embedding = generate_embedding_task.delay(text)
            embeddings.append(embedding.id)
        except Exception as e:
            print(f"Error generating embedding: {e}")
    return embeddings
