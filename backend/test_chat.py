#!/usr/bin/env python3
"""Test the chat endpoint."""
import asyncio
import json
from app.db.session import AsyncSessionLocal
from app.models.models import User
from app.services.auth_service import AuthService
from app.agents.agent import run_scholarship_agent
from sqlalchemy import select

async def test():
    # Create a test user
    session = AsyncSessionLocal()
    auth_svc = AuthService(session)
    
    # Create or get a test user
    stmt = select(User).where(User.email == "test@test.com")
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        print("Creating test user...")
        user_dict = await auth_svc.register_user(
            email="test@test.com",
            password="testpass123",
            full_name="Test User"
        )
        print(f"User created: {user_dict}")
        
        # Fetch the created user
        stmt = select(User).where(User.email == "test@test.com")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
    
    if user:
        print(f"\nTesting agent with user: {user.email}")
        response = await run_scholarship_agent(
            user_message="I am looking for scholarships for SC category students",
            session_id="test-session",
            user_profile={"community": "SC"},
            db=session,
        )
        print(f"\n✅ Agent Response:")
        print(f"Response: {response.get('response', 'No response')[:200]}...")
        print(f"Scholarships found: {len(response.get('scholarships', []))}")
        print(f"Extra Metadata: {response.get('extra_metadata', {})}")
    else:
        print("Failed to create or find user")
    
    await session.close()

asyncio.run(test())
