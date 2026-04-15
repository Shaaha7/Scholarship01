"""
PDF Ingestion Service
======================
Parses scholarship PDFs → chunks → embeds → upserts to Pinecone + PostgreSQL.
"""
import logging
import re
import uuid
from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import DocumentChunk, Scholarship, EligibilityMatrix
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService

logger = logging.getLogger(__name__)

# ── Text Splitter ─────────────────────────────────────────────────────────────
def split_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    """Split text into overlapping chunks by sentence boundaries."""
    sentences = re.split(r"(?<=[.!?।\n])\s+", text.strip())
    chunks = []
    current = []
    current_len = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        words = sentence.split()
        if current_len + len(words) > chunk_size:
            if current:
                chunks.append(" ".join(current))
            # Start new chunk with overlap
            current = words[-overlap:] if len(words) > overlap else words
            current_len = len(current)
        else:
            current.extend(words)
            current_len += len(words)

    if current:
        chunks.append(" ".join(current))

    return [c for c in chunks if len(c.strip()) > 30]  # Filter very short chunks


class IngestionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_svc = EmbeddingService()
        self.pinecone_svc = PineconeService()

    async def ingest_pdf(
        self,
        pdf_path: str,
        scholarship_title: str,
        provider: str,
        category: str,
        source_filename: str = "",
    ) -> Dict[str, Any]:
        """
        Full ingestion pipeline:
        1. Extract text from PDF
        2. Chunk text
        3. Embed chunks with BGE-M3
        4. Upsert to Pinecone
        5. Save DocumentChunks to PostgreSQL
        6. Create/update Scholarship record
        """
        # Step 1: Extract text
        raw_text = self._extract_pdf_text(pdf_path)
        if not raw_text.strip():
            raise ValueError("PDF contains no extractable text. May be a scanned image.")

        # Step 2: Parse metadata from text
        metadata = self._parse_scholarship_metadata(raw_text, scholarship_title, provider, category)

        # Step 3: Create Scholarship record
        scholarship = await self._create_or_update_scholarship(metadata, source_filename)

        # Step 4: Chunk text
        chunks = split_text(raw_text, chunk_size=400, overlap=50)
        logger.info(f"Split PDF into {len(chunks)} chunks for '{scholarship_title}'")

        # Step 5: Embed chunks
        embeddings = await self.embedding_svc.embed_documents(chunks)

        # Step 6: Prepare Pinecone vectors
        pinecone_chunks = []
        db_chunks = []
        chunk_ids = []

        for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{str(scholarship.id)}-chunk-{i}"
            chunk_ids.append(chunk_id)

            pinecone_chunks.append({
                "id": chunk_id,
                "embedding": embedding,
                "metadata": {
                    "scholarship_id": str(scholarship.id),
                    "title": scholarship_title,
                    "provider": provider,
                    "category": category,
                    "chunk_index": i,
                    "text_preview": chunk_text[:200],
                    "source_file": source_filename,
                },
            })

            db_chunks.append(DocumentChunk(
                scholarship_id=scholarship.id,
                pinecone_id=chunk_id,
                chunk_index=i,
                content=chunk_text,
                source_file=source_filename,
                extra_metadata={"title": scholarship_title, "chunk_index": i},
            ))

        # Step 7: Upsert to Pinecone
        upserted = await self.pinecone_svc.upsert_chunks(pinecone_chunks)

        # Step 8: Save chunks to DB
        for db_chunk in db_chunks:
            self.db.add(db_chunk)

        # Update scholarship with chunk IDs
        scholarship.pinecone_chunk_ids = chunk_ids
        await self.db.commit()

        logger.info(f"Ingestion complete: {len(chunks)} chunks, {upserted} vectors upserted.")
        return {
            "scholarship_id": scholarship.id,
            "chunks_created": len(chunks),
            "pinecone_upserted": upserted,
        }

    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text using PyMuPDF (fitz) with pdfplumber fallback."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(pdf_path)
            text = "\n".join(page.get_text("text") for page in doc)
            doc.close()
            if text.strip():
                return text
        except Exception as e:
            logger.warning(f"PyMuPDF failed: {e}")

        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                return "\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
        except Exception as e:
            logger.error(f"pdfplumber failed: {e}")
            raise RuntimeError(f"Could not extract text from PDF: {e}")

    def _parse_scholarship_metadata(
        self,
        text: str,
        title: str,
        provider: str,
        category: str,
    ) -> Dict[str, Any]:
        """Extract structured metadata from raw PDF text."""
        metadata = {
            "title": title,
            "provider": provider,
            "category": category,
            "description": text[:1000],
            "amount": None,
            "deadline": None,
            "application_url": None,
            "eligibility": {
                "min_annual_income": None,
                "max_annual_income": None,
                "gender_req": "any",
                "community_list": [category] if category else [],
                "course_type": [],
                "study_level": [],
            }
        }

        # Extract amount (INR patterns)
        amount_patterns = [
            r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d{2})?)",
            r"([\d,]+)\s*(?:per annum|per year|annually|p\.a\.)",
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    metadata["amount"] = float(amount_str)
                    break
                except ValueError:
                    pass

        # Extract income limit
        income_match = re.search(
            r"(?:family income|annual income|income limit)[^\d]*([\d,]+)",
            text, re.IGNORECASE
        )
        if income_match:
            try:
                metadata["eligibility"]["max_annual_income"] = float(income_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # Extract gender requirement
        if re.search(r"\b(girl|female|woman|women)\b", text, re.IGNORECASE):
            metadata["eligibility"]["gender_req"] = "female"

        # Extract study levels
        level_keywords = {
            "UG": ["undergraduate", "ug", "bachelor", "b.e", "b.tech", "b.sc", "b.a"],
            "PG": ["postgraduate", "pg", "master", "m.tech", "m.sc", "mba"],
            "PhD": ["phd", "doctorate", "research scholar"],
            "Diploma": ["diploma", "polytechnic"],
            "School": ["school", "hsc", "sslc", "class 10", "class 12"],
        }
        for level, keywords in level_keywords.items():
            if any(re.search(r"\b" + kw + r"\b", text, re.IGNORECASE) for kw in keywords):
                metadata["eligibility"]["study_level"].append(level)

        # Extract URLs
        url_match = re.search(r"https?://\S+", text)
        if url_match:
            metadata["application_url"] = url_match.group(0).rstrip(".,)")

        return metadata

    async def _create_or_update_scholarship(
        self,
        metadata: Dict[str, Any],
        source_filename: str,
    ) -> Scholarship:
        """Create or update scholarship and eligibility records."""
        scholarship = Scholarship(
            title=metadata["title"],
            description=metadata["description"],
            provider=metadata["provider"],
            category=metadata["category"],
            amount=metadata.get("amount"),
            application_url=metadata.get("application_url"),
            source_pdf_url=source_filename,
        )
        self.db.add(scholarship)
        await self.db.flush()

        # Create eligibility matrix
        elig_data = metadata.get("eligibility", {})
        eligibility = EligibilityMatrix(
            scholarship_id=scholarship.id,
            max_annual_income=elig_data.get("max_annual_income"),
            gender_req=elig_data.get("gender_req", "any"),
            community_list=elig_data.get("community_list", []),
            course_type=elig_data.get("course_type", []),
            study_level=elig_data.get("study_level", []),
        )
        self.db.add(eligibility)
        await self.db.flush()

        return scholarship
