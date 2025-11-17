import psycopg2

try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='insanity_cluster',
        user='testuser',
        password='testpass'
    )
    print("✅ Connection successful with testuser!")
    conn.close()
except Exception as e:
    print(f"❌ Failed: {e}")
