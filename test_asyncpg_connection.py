#!/usr/bin/env python3
"""Test asyncpg connection to PostgreSQL"""

import asyncio
import asyncpg

async def test_connection():
    try:
        print("Attempting to connect with asyncpg...")
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='insanity',
            password='insanity_dev_password',
            database='insanity_cluster'
        )
        print("✅ Connection successful!")
        
        # Test a simple query
        result = await conn.fetchval('SELECT 1')
        print(f"✅ Query successful: {result}")
        
        await conn.close()
        print("✅ Connection closed")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
