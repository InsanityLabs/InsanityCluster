"""
Demo script for SURFACE layer functionality.

This script demonstrates:
1. Command parsing
2. Authentication
3. Task creation via API
4. WebSocket streaming
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from insanity_cluster.surface.command_parser import CommandParser
from insanity_cluster.surface.auth import AuthManager, UserRole
from insanity_cluster.table.database import DatabaseManager
from insanity_cluster.table.redis_manager import RedisManager
from insanity_cluster.table.models import User


async def demo_command_parser():
    """Demo command parser functionality"""
    print("\n" + "="*60)
    print("DEMO: Command Parser")
    print("="*60)
    
    # Initialize Redis manager
    redis_manager = RedisManager()
    
    # Create command parser
    parser = CommandParser(redis_manager)
    
    # Test commands
    test_commands = [
        "Create a Python web scraper for news articles",
        "Send an email to john@example.com about the meeting",
        "Form an LLC in Delaware called Tech Innovations",
        "Review the contract for legal issues",
        "Write a function to calculate fibonacci numbers"
    ]
    
    for command in test_commands:
        print(f"\nCommand: {command}")
        try:
            parsed = parser.parse(command, user_id="demo_user")
            print(f"  Intent: {parsed.intent}")
            print(f"  Confidence: {parsed.confidence:.2f}")
            print(f"  Parameters: {parsed.parameters}")
        except Exception as e:
            print(f"  Error: {e}")
    
    redis_manager.close()


async def demo_authentication():
    """Demo authentication functionality"""
    print("\n" + "="*60)
    print("DEMO: Authentication & Session Management")
    print("="*60)
    
    # Initialize managers
    db_manager = DatabaseManager()
    redis_manager = RedisManager()
    auth_manager = AuthManager(db_manager, redis_manager)
    
    # Generate API key
    print("\n1. Generating API key...")
    api_key, api_key_hash = auth_manager.generate_api_key()
    print(f"   API Key: {api_key[:20]}...")
    print(f"   Hash: {api_key_hash[:20]}...")
    
    # Create test user
    print("\n2. Creating test user...")
    with db_manager.get_session() as session:
        # Check if user exists
        user = session.query(User).filter(User.email == "demo@example.com").first()
        if not user:
            user = User(
                email="demo@example.com",
                api_key_hash=api_key_hash,
                role=UserRole.USER.value
            )
            session.add(user)
            session.commit()
            print(f"   Created user: {user.email}")
        else:
            user.api_key_hash = api_key_hash
            session.commit()
            print(f"   Updated existing user: {user.email}")
        
        user_id = str(user.id)
    
    # Verify API key
    print("\n3. Verifying API key...")
    verified_user = await auth_manager.verify_api_key(api_key)
    print(f"   Verified user: {verified_user.email}")
    print(f"   Role: {verified_user.role}")
    
    # Create JWT token
    print("\n4. Creating JWT token...")
    jwt_token = auth_manager.create_jwt_token(user_id, UserRole.USER.value)
    print(f"   JWT Token: {jwt_token[:50]}...")
    
    # Verify JWT token
    print("\n5. Verifying JWT token...")
    payload = await auth_manager.verify_jwt_token(jwt_token)
    print(f"   User ID: {payload['sub']}")
    print(f"   Role: {payload['role']}")
    
    # Create session
    print("\n6. Creating session...")
    session_id = await auth_manager.create_session(
        user_id,
        metadata={"ip": "127.0.0.1", "user_agent": "demo"}
    )
    print(f"   Session ID: {session_id}")
    
    # Get session
    print("\n7. Retrieving session...")
    session_data = await auth_manager.get_session(session_id)
    print(f"   Session data: {session_data}")
    
    # Check permissions
    print("\n8. Checking permissions...")
    has_user_perm = auth_manager.check_permission(UserRole.USER.value, UserRole.USER)
    has_admin_perm = auth_manager.check_permission(UserRole.USER.value, UserRole.ADMIN)
    print(f"   User has USER permission: {has_user_perm}")
    print(f"   User has ADMIN permission: {has_admin_perm}")
    
    # Cleanup
    await auth_manager.delete_session(session_id)
    redis_manager.close()
    
    print(f"\n   API Key for testing: {api_key}")


async def demo_api_client():
    """Demo API client usage"""
    print("\n" + "="*60)
    print("DEMO: API Client Usage")
    print("="*60)
    
    print("\nTo test the API, first start the server:")
    print("  python -m insanity_cluster.surface.main")
    print("\nThen use curl or httpx to interact with the API:")
    print("\n1. Create a task:")
    print('  curl -X POST http://localhost:8000/api/tasks \\')
    print('    -H "X-API-Key: <your_api_key>" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"command": "Create a Python web scraper", "priority": 1}\'')
    print("\n2. Get task status:")
    print('  curl http://localhost:8000/api/tasks/<task_id> \\')
    print('    -H "X-API-Key: <your_api_key>"')
    print("\n3. List tasks:")
    print('  curl http://localhost:8000/api/tasks \\')
    print('    -H "X-API-Key: <your_api_key>"')


async def demo_cli():
    """Demo CLI usage"""
    print("\n" + "="*60)
    print("DEMO: CLI Usage")
    print("="*60)
    
    print("\nThe CLI provides a user-friendly interface:")
    print("\n1. Setup configuration:")
    print("  python -m insanity_cluster.surface.cli setup")
    print("\n2. Submit a command:")
    print("  python -m insanity_cluster.surface.cli run Create a Python web scraper")
    print("\n3. Submit with streaming:")
    print("  python -m insanity_cluster.surface.cli run --stream Write a REST API")
    print("\n4. Check task status:")
    print("  python -m insanity_cluster.surface.cli status <task-id>")
    print("\n5. List recent tasks:")
    print("  python -m insanity_cluster.surface.cli list")
    print("\n6. Interactive mode:")
    print("  python -m insanity_cluster.surface.cli interactive")


async def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("INSANITY CLUSTER - SURFACE LAYER DEMO")
    print("="*60)
    
    try:
        # Demo 1: Command Parser
        await demo_command_parser()
        
        # Demo 2: Authentication
        await demo_authentication()
        
        # Demo 3: API Client
        await demo_api_client()
        
        # Demo 4: CLI
        await demo_cli()
        
        print("\n" + "="*60)
        print("DEMO COMPLETE")
        print("="*60)
        print("\nNext steps:")
        print("1. Start the SURFACE layer server:")
        print("   python -m insanity_cluster.surface.main")
        print("2. Use the API key from the authentication demo")
        print("3. Test the API endpoints or CLI commands")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
