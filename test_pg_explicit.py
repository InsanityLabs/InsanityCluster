import asyncio
import asyncpg

async def test_connection():
    print("Testing explicit connection...")
    
    try:
        # Try with explicit server_settings to disable SSL
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            database='insanity_cluster',
            user='insanity',
            password='insanity_dev_password',
            server_settings={'application_name': 'test_script'},
            ssl=False
        )
        print("✅ Connection successful!")
        
        result = await conn.fetchval("SELECT 1")
        print(f"✅ Query result: {result}")
        
        # Test a real query
        users = await conn.fetch("SELECT * FROM users LIMIT 1")
        print(f"✅ Found {len(users)} user(s)")
        
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
