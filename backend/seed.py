#!/usr/bin/env python3
"""Quick seed script for demo scholarships."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def main():
    from scripts.ingest_scholarships import seed_demo_data
    await seed_demo_data()

if __name__ == "__main__":
    asyncio.run(main())
