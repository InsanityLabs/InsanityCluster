import psycopg2
from dotenv import load_dotenv
import os

def test_connection():
    load_dotenv()
    
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = int(os.getenv('POSTGRES_PORT', '5432'))
    database = os.getenv('POSTGRES_DB', 'insanity_cluster')
    user = os.getenv('POSTGRES_USER', 'insanity')
    password = os.getenv('POSTGRES_PASSWORD', 'insanity_dev_password')
    
    print(f"Connecting to: {user}@{host}:{port}/{database}")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print("✅ Connection successful!")
        
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        print(f"✅ Query result: {result[0]}")
        
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        print(f"✅ Found {count} user(s) in database")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)
