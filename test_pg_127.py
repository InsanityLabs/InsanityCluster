import asyncio
import asyncpg

async def test_connection():
    print("Testing connection to 127.0.0.1...")
    
    try:
        conn = await asyncpg.connect(
            host='127.0.0.1',
            port=5432,
            database='insanity_cluster',
            user='insanity',
            password='insanity_dev_password'
        )
        print("✅ Connection successful!")
        
        result = await conn.fetchval("SELECT 1")
        print(f"✅ Query result: {result}")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
