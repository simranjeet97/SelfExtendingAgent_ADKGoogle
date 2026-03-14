import asyncio
import sys
import os
import pathlib

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from backend.agent_runner import run_answer_stream

async def test_answer():
    user_msg = "explain me about redis use in node js"
    skill_content = """---
name: redis-node
description: How to use Redis for caching in Node.js applications.
---
# Redis in Node.js
Redis is an in-memory data structure store. In Node.js, you can use the 'redis' or 'ioredis' package.
Example: const client = redis.createClient(); await client.connect();"""

    print("--- Testing run_answer_stream ---")
    async for chunk in run_answer_stream(user_msg, skill_content=skill_content):
        print(f"CHUNK: {chunk}", end="")
    print("\n--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(test_answer())
