#!/usr/bin/env python3
"""Test the agent directly."""
import asyncio
from app.agents.agent import run_scholarship_agent

async def test():
    print("\n🧪 Testing Scholarship Agent...")
    print("=" * 50)
    
    response = await run_scholarship_agent(
        user_message="I need a scholarship for SC category engineering students",
        session_id="test-session-123" ,
        user_profile={"community": "SC", "stream": "Engineering"},
    )
    
    print(f"\n✅ Agent Response Received!")
    print(f"Response Text: {response.get('response', 'No response')[:300]}...")
    print(f"Scholarships Found: {len(response.get('scholarships', []))}")
    if response.get('scholarships'):
        for i, s in enumerate(response['scholarships'][:3], 1):
            print(f"  {i}. {s.get('title', 'Unknown')}")
    
    print(f"Extra Metadata Keys: {list(response.get('extra_metadata', {}).keys())}")
    print(f"Language: {response.get('language')}")
    print(f"Intent: {response.get('intent')}")
    
    if response.get('error'):
        print(f"⚠️  Error: {response.get('error')}")
    else:
        print("✅ No errors!")

asyncio.run(test())
