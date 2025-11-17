#!/usr/bin/env python3
"""
Test script to verify TABLE layer components
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    from insanity_cluster.table import (
        init_table_layer,
        close_table_layer,
        db_manager,
        redis_manager,
        vector_store,
        metrics_collector,
    )
except ImportError as e:
    print(f"❌ Error: Required packages not installed - {e}")
    print("   Run: pip install -r requirements.txt")
    sys.exit(1)


async def test_database():
    """Test PostgreSQL database connection"""
    print("\n🔍 Testing PostgreSQL database...")
    try:
        is_healthy = await db_manager.health_check()
        if is_healthy:
            print("✅ PostgreSQL connection successful")
            
            # Test query
            result = await db_manager.execute_raw_one("SELECT COUNT(*) as count FROM users")
            if result:
                print(f"✅ Database query successful - {result['count']} users found")
            return True
        else:
            print("❌ PostgreSQL health check failed")
            return False
    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")
        return False


async def test_redis():
    """Test Redis connection"""
    print("\n🔍 Testing Redis...")
    try:
        is_healthy = await redis_manager.health_check()
        if is_healthy:
            print("✅ Redis connection successful")
            
            # Test cache operations
            await redis_manager.cache_set("test_key", {"test": "value"}, ttl=60)
            value = await redis_manager.cache_get("test_key")
            if value and value.get("test") == "value":
                print("✅ Redis cache operations successful")
            await redis_manager.cache_delete("test_key")
            
            return True
        else:
            print("❌ Redis health check failed")
            return False
    except Exception as e:
        print(f"❌ Redis error: {e}")
        return False


async def test_vector_store():
    """Test Qdrant vector database"""
    print("\n🔍 Testing Qdrant vector database...")
    try:
        is_healthy = await vector_store.health_check()
        if is_healthy:
            print("✅ Qdrant connection successful")
            
            # Check collections
            for collection_name in [
                vector_store.TASK_PATTERNS,
                vector_store.CONTEXT_EMBEDDINGS,
                vector_store.AGENT_KNOWLEDGE,
            ]:
                info = await vector_store.get_collection_info(collection_name)
                if info:
                    print(f"✅ Collection '{collection_name}' exists - {info['points_count']} points")
                else:
                    print(f"⚠️  Collection '{collection_name}' not found")
            
            return True
        else:
            print("❌ Qdrant health check failed")
            return False
    except Exception as e:
        print(f"❌ Qdrant error: {e}")
        return False


async def test_metrics():
    """Test Prometheus metrics"""
    print("\n🔍 Testing Prometheus metrics...")
    try:
        # Record some test metrics
        metrics_collector.record_request("SURFACE", "/test", "success", 0.1)
        metrics_collector.record_task("success", 1.5)
        metrics_collector.set_active_tasks(5)
        
        # Export metrics
        metrics_data = metrics_collector.export_metrics()
        if metrics_data:
            print("✅ Metrics collection successful")
            print(f"✅ Exported {len(metrics_data)} bytes of metrics data")
            return True
        else:
            print("❌ Failed to export metrics")
            return False
    except Exception as e:
        print(f"❌ Metrics error: {e}")
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("TABLE Layer Component Tests")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Initialize TABLE layer
    print("\n🚀 Initializing TABLE layer...")
    try:
        await init_table_layer()
        print("✅ TABLE layer initialized")
    except Exception as e:
        print(f"❌ Failed to initialize TABLE layer: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Run tests
    results = {
        "PostgreSQL": await test_database(),
        "Redis": await test_redis(),
        "Qdrant": await test_vector_store(),
        "Metrics": await test_metrics(),
    }
    
    # Close connections
    print("\n🔌 Closing connections...")
    await close_table_layer()
    print("✅ Connections closed")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for component, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {component}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✨ All tests passed!")
        print("\n💡 Next steps:")
        print("   1. Start Docker services: docker-compose up -d")
        print("   2. Run migrations: alembic upgrade head")
        print("   3. Access Grafana: http://localhost:3000 (admin/admin)")
        print("   4. Access Prometheus: http://localhost:9090")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\n💡 Troubleshooting:")
        print("   1. Ensure Docker services are running: docker-compose up -d")
        print("   2. Check service logs: docker-compose logs")
        print("   3. Verify .env file configuration")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
