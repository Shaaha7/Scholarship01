#!/usr/bin/env python3
"""
scripts/ingest_scholarships.py
================================
Standalone script to parse Tamil Nadu scholarship PDFs and seed the database.
Includes real Tamil Nadu scholarship data for development/demo.

Usage:
  python scripts/ingest_scholarships.py --pdf path/to/scholarship.pdf
  python scripts/ingest_scholarships.py --seed-demo   # Load demo data
"""
import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.db.session import AsyncSessionLocal, create_tables
from app.models.models import EligibilityMatrix, Scholarship
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService

# ── Real Tamil Nadu Scholarship Data ─────────────────────────────────────────
DEMO_SCHOLARSHIPS = [
    {
        "title": "Dr. Ambedkar Law Entrance Scholarship",
        "description": "Scholarship for SC/ST students pursuing LLB courses in Tamil Nadu. Covers tuition fees and maintenance allowance for full duration of the course.",
        "provider": "TN Adi Dravidar and Tribal Welfare Department",
        "scheme_code": "ADTWD-LAW-001",
        "category": "SC",
        "amount": 25000.0,
        "academic_year": "2024-25",
        "application_url": "https://adwelfare.tn.gov.in",
        "is_renewable": True,
        "eligibility": {
            "max_annual_income": 250000.0,
            "community_list": ["SC", "ST"],
            "gender_req": "any",
            "course_type": ["Law", "LLB"],
            "study_level": ["UG", "PG"],
            "min_percentage": 50.0,
            "state_resident_required": True,
        }
    },
    {
        "title": "Chief Minister's Special Scholarship for BC Students",
        "description": "Merit-cum-means scholarship for Backward Class students pursuing professional courses (Engineering, Medicine, Architecture) in Tamil Nadu government and aided colleges.",
        "provider": "TN BC, MBC and Minorities Welfare Department",
        "scheme_code": "BCMBC-CM-2024",
        "category": "BC",
        "amount": 50000.0,
        "deadline": datetime(2024, 11, 30, tzinfo=timezone.utc),
        "academic_year": "2024-25",
        "application_url": "https://bcmbcmw.tn.gov.in",
        "is_renewable": True,
        "eligibility": {
            "max_annual_income": 200000.0,
            "community_list": ["BC", "BCM"],
            "gender_req": "any",
            "course_type": ["Engineering", "Medicine", "Architecture", "Agriculture"],
            "study_level": ["UG"],
            "min_percentage": 60.0,
            "state_resident_required": True,
        }
    },
    {
        "title": "Moovalur Ramamirtham Ammaiyar Higher Education Scheme",
        "description": "Scholarship for first-generation female learners from BC/MBC families. Provides ₹1,000/month maintenance allowance plus tuition fee waiver for government college students.",
        "provider": "TN BC, MBC and Minorities Welfare Department",
        "scheme_code": "BCMBC-MRAA-2024",
        "category": "MBC",
        "amount": 12000.0,
        "deadline": datetime(2024, 12, 31, tzinfo=timezone.utc),
        "academic_year": "2024-25",
        "application_url": "https://bcmbcmw.tn.gov.in/mraa",
        "is_renewable": True,
        "eligibility": {
            "max_annual_income": 250000.0,
            "community_list": ["BC", "MBC", "DNT"],
            "gender_req": "female",
            "course_type": ["Arts", "Science", "Commerce", "Engineering", "Medicine"],
            "study_level": ["UG", "PG"],
            "min_percentage": 0.0,
            "first_gen_learner": True,
            "state_resident_required": True,
        }
    },
    {
        "title": "Post-Matric Scholarship for SC/ST Students",
        "description": "Central government funded scholarship for SC/ST students pursuing post-matriculation studies. Covers tuition fees, maintenance allowance, and study tour charges.",
        "provider": "Government of India / TN Adi Dravidar Welfare",
        "scheme_code": "GOI-POSTMATRIC-SC-2024",
        "category": "SC",
        "amount": 83000.0,
        "deadline": datetime(2024, 10, 31, tzinfo=timezone.utc),
        "academic_year": "2024-25",
        "application_url": "https://scholarships.gov.in",
        "is_renewable": True,
        "eligibility": {
            "max_annual_income": 250000.0,
            "community_list": ["SC", "ST"],
            "gender_req": "any",
            "course_type": ["Engineering", "Medicine", "Arts", "Science", "Commerce", "Law", "Management"],
            "study_level": ["UG", "PG", "PhD", "Diploma"],
            "min_percentage": 0.0,
            "state_resident_required": True,
        }
    },
    {
        "title": "Tamil Nadu State Scholarship for Minorities",
        "description": "Scholarship for students belonging to minority communities (Muslim, Christian, Sikh, Buddhist, Parsi) for pursuing higher education in Tamil Nadu.",
        "provider": "TN BC, MBC and Minorities Welfare Department",
        "scheme_code": "TNMINORITY-2024",
        "category": "Minority",
        "amount": 30000.0,
        "deadline": datetime(2024, 11, 15, tzinfo=timezone.utc),
        "academic_year": "2024-25",
        "application_url": "https://bcmbcmw.tn.gov.in/minority",
        "is_renewable": False,
        "eligibility": {
            "max_annual_income": 200000.0,
            "community_list": ["Muslim", "Christian", "Sikh", "Buddhist", "Parsi"],
            "gender_req": "any",
            "course_type": ["Arts", "Science", "Engineering", "Medicine", "Commerce"],
            "study_level": ["UG", "PG"],
            "min_percentage": 50.0,
            "state_resident_required": True,
        }
    },
    {
        "title": "Anaithu Grama Anna Marumalarchi Thittam Girl Scholarship",
        "description": "Special scholarship for rural girl students from MBC/DNT communities who secure marks above 85% in Class 12 and wish to pursue higher education.",
        "provider": "TN MBC Welfare Department",
        "scheme_code": "TNMBC-GIRL-2024",
        "category": "MBC",
        "amount": 15000.0,
        "deadline": datetime(2024, 9, 30, tzinfo=timezone.utc),
        "academic_year": "2024-25",
        "application_url": "https://mbcwelfare.tn.gov.in",
        "is_renewable": False,
        "eligibility": {
            "max_annual_income": 300000.0,
            "community_list": ["MBC", "DNT"],
            "gender_req": "female",
            "course_type": ["Engineering", "Medicine", "Arts", "Science"],
            "study_level": ["UG"],
            "min_percentage": 85.0,
            "state_resident_required": True,
            "min_tn_residence_years": 5,
        }
    },
    {
        "title": "Free Education Scheme for Scheduled Tribe Students",
        "description": "Complete fee waiver including tuition, hostel, transport, and study materials for Scheduled Tribe students in all Tamil Nadu government colleges.",
        "provider": "TN Adi Dravidar and Tribal Welfare Department",
        "scheme_code": "ADTWD-FREE-ST-2024",
        "category": "ST",
        "amount": 100000.0,
        "academic_year": "2024-25",
        "application_url": "https://adwelfare.tn.gov.in/free-education",
        "is_renewable": True,
        "eligibility": {
            "max_annual_income": 500000.0,
            "community_list": ["ST"],
            "gender_req": "any",
            "course_type": ["Engineering", "Medicine", "Arts", "Science", "Commerce", "Agriculture", "Law"],
            "study_level": ["UG", "PG"],
            "min_percentage": 0.0,
            "state_resident_required": True,
        }
    },
    {
        "title": "National Scholarship Portal - Central Sector Scheme",
        "description": "Merit-based scholarship for students who have passed Class 12 with more than 80% marks and whose parental income is below ₹8 lakh per annum. General and OBC categories.",
        "provider": "Ministry of Education, Government of India",
        "scheme_code": "NSP-CSS-2024",
        "category": "General",
        "amount": 20000.0,
        "deadline": datetime(2024, 11, 30, tzinfo=timezone.utc),
        "academic_year": "2024-25",
        "application_url": "https://scholarships.gov.in",
        "is_renewable": True,
        "eligibility": {
            "max_annual_income": 800000.0,
            "community_list": ["General", "OBC", "EWS"],
            "gender_req": "any",
            "course_type": ["Engineering", "Medicine", "Arts", "Science", "Commerce"],
            "study_level": ["UG"],
            "min_percentage": 80.0,
            "state_resident_required": False,
        }
    },
    {
        "title": "EWS Scholarship for Higher Education",
        "description": "Scholarship for students from Economically Weaker Sections (EWS) in Tamil Nadu pursuing undergraduate courses in government or aided colleges.",
        "provider": "TN Social Welfare and Women Empowerment Department",
        "scheme_code": "TNEWS-2024",
        "category": "EWS",
        "amount": 25000.0,
        "deadline": datetime(2024, 12, 15, tzinfo=timezone.utc),
        "academic_year": "2024-25",
        "application_url": "https://socialwelfare.tn.gov.in",
        "is_renewable": True,
        "eligibility": {
            "min_annual_income": 0,
            "max_annual_income": 800000.0,
            "community_list": ["EWS", "General"],
            "gender_req": "any",
            "course_type": ["Engineering", "Medicine", "Arts", "Science", "Commerce"],
            "study_level": ["UG"],
            "min_percentage": 60.0,
            "state_resident_required": True,
        }
    },
    {
        "title": "OBC Pre-Matric Scholarship for Class 9-10",
        "description": "Pre-matric scholarship for OBC students in Class 9 and 10, providing financial assistance for books, stationery, and uniform. Day scholars and hostellers both eligible.",
        "provider": "Ministry of Social Justice & Empowerment / TN BC Welfare",
        "scheme_code": "OBC-PREMATRIC-2024",
        "category": "OBC",
        "amount": 5000.0,
        "deadline": datetime(2024, 10, 15, tzinfo=timezone.utc),
        "academic_year": "2024-25",
        "application_url": "https://scholarships.gov.in",
        "is_renewable": True,
        "eligibility": {
            "max_annual_income": 100000.0,
            "community_list": ["OBC"],
            "gender_req": "any",
            "course_type": ["School"],
            "study_level": ["School"],
            "min_percentage": 0.0,
            "state_resident_required": True,
        }
    },
]

async def seed_demo_data():
    """Seed the database with real Tamil Nadu scholarship data."""
    print("\n🌱 Seeding Tamil Nadu Scholarship Demo Data...")
    await create_tables()

    embedding_svc = EmbeddingService()
    pinecone_svc = PineconeService()

    async with AsyncSessionLocal() as session:
        created = 0
        for data in DEMO_SCHOLARSHIPS:
            elig_data = data.pop("eligibility", {})
            scholarship = Scholarship(**data)
            session.add(scholarship)
            await session.flush()

            eligibility = EligibilityMatrix(scholarship_id=scholarship.id, **elig_data)
            session.add(eligibility)
            await session.flush()

            # Generate embedding for the scholarship text
            text_for_embedding = f"{scholarship.title} {scholarship.description} Category: {scholarship.category}"
            try:
                embedding = await embedding_svc.embed_query(text_for_embedding)
                chunk_id = f"{scholarship.id}-main"

                await pinecone_svc.upsert_chunks([{
                    "id": chunk_id,
                    "embedding": embedding,
                    "metadata": {
                        "scholarship_id": str(scholarship.id),
                        "title": scholarship.title,
                        "provider": scholarship.provider,
                        "category": scholarship.category,
                        "text_preview": scholarship.description[:200],
                    }
                }])
                scholarship.pinecone_chunk_ids = [chunk_id]
                print(f"  ✅ {scholarship.title[:60]}...")
            except Exception as e:
                print(f"  ⚠️  Embedding skipped for {scholarship.title[:40]}: {e}")

            created += 1

        await session.commit()
        print(f"\n✅ Seeded {created} scholarships successfully!")
        print("   Categories: BC, MBC, SC, ST, General, OBC, EWS, Minority")

async def ingest_pdf(pdf_path: str):
    """Ingest a single PDF file."""
    from app.services.ingestion_service import IngestionService

    print(f"\n📄 Ingesting PDF: {pdf_path}")
    await create_tables()

    async with AsyncSessionLocal() as session:
        svc = IngestionService(session)
        result = await svc.ingest_pdf(
            pdf_path=pdf_path,
            scholarship_title=input("Scholarship title: "),
            provider=input("Provider name: "),
            category=input("Category (BC/MBC/SC/ST/General/OBC/EWS/Minority): "),
            source_filename=os.path.basename(pdf_path),
        )
        print(f"\n✅ Ingestion complete!")
        print(f"   Scholarship ID: {result['scholarship_id']}")
        print(f"   Text chunks: {result['chunks_created']}")
        print(f"   Pinecone vectors: {result['pinecone_upserted']}")

def main():
    parser = argparse.ArgumentParser(description="TamilScholar Pro – Data Ingestion Tool")
    parser.add_argument("--pdf", help="Path to scholarship PDF to ingest")
    parser.add_argument("--seed-demo", action="store_true", help="Seed database with real TN scholarship data")
    parser.add_argument("--list", action="store_true", help="List demo scholarships")
    args = parser.parse_args()

    if args.list:
        print("\nDemo Scholarships:")
        for s in DEMO_SCHOLARSHIPS:
            print(f"  [{s['category']}] {s['title']} – ₹{s.get('amount',0):,.0f}/yr")
        return

    if args.seed_demo:
        asyncio.run(seed_demo_data())
    elif args.pdf:
        if not os.path.exists(args.pdf):
            print(f"Error: File not found: {args.pdf}")
            sys.exit(1)
        asyncio.run(ingest_pdf(args.pdf))
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python scripts/ingest_scholarships.py --seed-demo")
        print("  python scripts/ingest_scholarships.py --pdf /path/to/scholarship.pdf")
        print("  python scripts/ingest_scholarships.py --list")

if __name__ == "__main__":
    main()
