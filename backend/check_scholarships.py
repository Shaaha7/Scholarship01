#!/usr/bin/env python3
"""Check if scholarships were seeded."""
import asyncio
from app.db.session import AsyncSessionLocal
from app.models.models import Scholarship
from sqlalchemy import select

async def check():
    session = AsyncSessionLocal()
    stmt = select(Scholarship)
    result = await session.execute(stmt)
    scholarships = result.scalars().all()
    print(f"\n✅ Found {len(scholarships)} scholarships in database")
    if scholarships:
        for i, s in enumerate(scholarships[:3], 1):
            print(f"  {i}. {s.title} ({s.category})")
    await session.close()

asyncio.run(check())
