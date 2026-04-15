"""
Pinecone Serverless Service
============================
Handles upsert and semantic search against Pinecone serverless index.
Namespace: "scholarships"
"""
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class PineconeService:
    """Async-compatible Pinecone operations wrapper."""

    def __init__(self):
        self._index = None

    def _get_index(self):
        if self._index:
            return self._index
        try:
            from pinecone import Pinecone, ServerlessSpec
            pc = Pinecone(api_key=settings.PINECONE_API_KEY)

            # Create index if it doesn't exist
            existing = [idx.name for idx in pc.list_indexes()]
            if settings.PINECONE_INDEX_NAME not in existing:
                pc.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=settings.PINECONE_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
                logger.info(f"Created Pinecone index: {settings.PINECONE_INDEX_NAME}")

            self._index = pc.Index(settings.PINECONE_INDEX_NAME)
            return self._index
        except Exception as e:
            logger.warning(f"Pinecone unavailable: {e}. Returning None.")
            return None

    async def upsert_chunks(
        self,
        chunks: List[Dict[str, Any]],
        namespace: str = "scholarships",
    ) -> int:
        """
        Upsert text chunks with embeddings to Pinecone.
        Each chunk: {"id": str, "embedding": List[float], "metadata": dict}
        Returns number of vectors upserted.
        """
        import asyncio
        index = self._get_index()
        if not index:
            logger.warning("Pinecone index not available. Skipping upsert.")
            return 0

        vectors = [
            {
                "id": chunk["id"],
                "values": chunk["embedding"],
                "metadata": chunk.get("metadata", {}),
            }
            for chunk in chunks
        ]

        # Batch upsert in groups of 100
        batch_size = 100
        total_upserted = 0
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i: i + batch_size]
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda b=batch: index.upsert(vectors=b, namespace=namespace)
                )
                total_upserted += len(batch)
            except Exception as e:
                logger.error(f"Pinecone upsert error (batch {i}): {e}")

        logger.info(f"Upserted {total_upserted} vectors to Pinecone.")
        return total_upserted

    async def semantic_search(
        self,
        query_embedding: List[float],
        filter_ids: Optional[List[str]] = None,
        top_k: int = 10,
        namespace: str = "scholarships",
    ) -> List[Dict[str, Any]]:
        """
        Search Pinecone for semantically similar scholarship chunks.
        Returns list of {"scholarship_id": str, "chunk_id": str, "score": float}
        """
        import asyncio
        index = self._get_index()
        if not index:
            return []

        query_filter = None
        if filter_ids:
            query_filter = {"scholarship_id": {"$in": filter_ids[:500]}}

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: index.query(
                    vector=query_embedding,
                    top_k=top_k,
                    filter=query_filter,
                    include_metadata=True,
                    namespace=namespace,
                ),
            )

            return [
                {
                    "chunk_id": match.id,
                    "scholarship_id": match.metadata.get("scholarship_id", match.id),
                    "score": match.score,
                    "title": match.metadata.get("title", ""),
                    "extra_metadata": match.metadata,
                }
                for match in result.matches
            ]
        except Exception as e:
            logger.error(f"Pinecone query error: {e}")
            return []

    async def delete_by_scholarship(self, scholarship_id: str, namespace: str = "scholarships"):
        """Delete all vectors for a scholarship."""
        import asyncio
        index = self._get_index()
        if not index:
            return

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: index.delete(
                    filter={"scholarship_id": {"$eq": scholarship_id}},
                    namespace=namespace,
                ),
            )
        except Exception as e:
            logger.error(f"Pinecone delete error: {e}")
