#!/usr/bin/env python3
"""
Generate API key for admin user.

This script creates or updates the API key for the default admin user.
Run this after initial setup to get your admin API key.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from insanity_cluster.common.config import settings
from insanity_cluster.table.database import DatabaseManager
from insanity_cluster.table.redis_manager import RedisManager
from insanity_cluster.surface.auth import AuthManager
from insanity_cluster.table.models import User
from sqlalchemy import select


async def main():
    """Generate API key for admin user"""
    print("Generating API key for admin user...")
    
    # Initialize managers
    db_manager = DatabaseManager()
    await db_manager.initialize()
    redis_manager = RedisManager()
    auth_manager = AuthManager(db_manager, redis_manager)
    
    try:
        # Find admin user
        async with db_manager.session() as session:
            result = await session.execute(
                select(User).filter(User.email == 'admin@insanity-cluster.local')
            )
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                print("ERROR: Admin user not found!")
                print("Please run database migrations first: alembic upgrade head")
                return 1
            
            # Generate new API key
            api_key, api_key_hash = auth_manager.generate_api_key()
            
            # Update user
            admin_user.api_key_hash = api_key_hash
            await session.commit()
            
            print("\n" + "="*60)
            print("SUCCESS! Admin API key generated:")
            print("="*60)
            print(f"\nEmail: {admin_user.email}")
            print(f"Role: {admin_user.role}")
            print(f"API Key: {api_key}")
            print("\n" + "="*60)
            print("\nSave this API key securely - it won't be shown again!")
            print("\nUsage:")
            print(f'  curl -H "X-API-Key: {api_key}" http://localhost:8000/api/health')
            print("="*60 + "\n")
            
            return 0
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await db_manager.close()
        redis_manager.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
