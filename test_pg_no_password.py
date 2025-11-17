import asyncio
import asyncpg
from dotenv import load_dotenv
import os

async def test_connection():
    load_dotenv()
    
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = int(os.getenv('POSTGRES_PORT', '5432'))
    database = os.getenv('POSTGRES_DB', 'insanity_cluster')
    user = os.getenv('POSTGRES_USER', 'insanity')
    
    print(f"Connecting to: {user}@{host}:{port}/{database} (no password)")
    
    try:
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=user
        )
        print("✅ Connection successful!")
        
        result = await conn.fetchval("SELECT 1")
        print(f"✅ Query result: {result}")
        
        await conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
