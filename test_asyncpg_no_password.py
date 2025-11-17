#!/usr/bin/env python3
"""Test asyncpg connection without password"""

import asyncio
import asyncpg

async def test_connection():
    try:
        print("Attempting to connect without password...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='insanity',
            database='insanity_cluster'
            # No password
        )
        print("✅ Connection successful without password!")
        
        result = await conn.fetchval('SELECT 1')
        print(f"✅ Query successful: {result}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
