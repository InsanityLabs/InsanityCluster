#!/usr/bin/env python3
"""
Initialize database schema using Alembic migrations
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    from insanity_cluster.table.database import db_manager
except ImportError:
    print("❌ Error: Required packages not installed")
    print("   Run: pip install -r requirements.txt")
    sys.exit(1)


async def init_database():
    """Initialize database schema"""
    # Load environment variables
    load_dotenv()
    
    print("🔌 Initializing database connection...")
    
    try:
        # Initialize database manager
        await db_manager.initialize()
        print("✅ Connected to database")
        
        # Check database health
        is_healthy = await db_manager.health_check()
        if not is_healthy:
            print("❌ Database health check failed")
            sys.exit(1)
        
        print("✅ Database health check passed")
        
        # Verify tables
        tables = await db_manager.execute_raw("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        if tables:
            print("\n📊 Existing tables:")
            for table in tables:
                print(f"   - {table['table_name']}")
        else:
            print("\n⚠️  No tables found. Run 'alembic upgrade head' to create schema.")
        
        await db_manager.close()
        print("\n✨ Database initialization complete!")
        print("\n💡 Next steps:")
        print("   1. Run: alembic upgrade head")
        print("   2. Start the application")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_database())
