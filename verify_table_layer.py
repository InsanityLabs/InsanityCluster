"""
Comprehensive TABLE layer verification
This script verifies all components are properly set up
"""
import subprocess
import sys

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")
        success = result.returncode == 0
        print(f"Status: {'✅ PASS' if success else '❌ FAIL'}")
        return success
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("TABLE LAYER VERIFICATION")
    print("="*60)
    
    tests = [
        ("docker ps --filter name=insanity_postgres --format '{{.Status}}'", 
         "PostgreSQL Container Running"),
        
        ("docker ps --filter name=insanity_redis --format '{{.Status}}'", 
         "Redis Container Running"),
        
        ("docker ps --filter name=insanity_qdrant --format '{{.Status}}'", 
         "Qdrant Container Running"),
        
        ("docker ps --filter name=insanity_prometheus --format '{{.Status}}'", 
         "Prometheus Container Running"),
        
        ("docker ps --filter name=insanity_grafana --format '{{.Status}}'", 
         "Grafana Container Running"),
        
        ('docker exec insanity_postgres psql -U insanity -d insanity_cluster -c "\\l" | findstr insanity_cluster', 
         "Database 'insanity_cluster' Exists"),
        
        ('docker exec insanity_postgres psql -U insanity -d insanity_cluster -c "\\du" | findstr insanity', 
         "User 'insanity' Exists"),
        
        ('docker exec insanity_postgres psql -U insanity -d insanity_cluster -c "\\dt" | findstr users', 
         "Table 'users' Exists"),
        
        ('docker exec insanity_postgres psql -U insanity -d insanity_cluster -c "\\dt" | findstr tasks', 
         "Table 'tasks' Exists"),
        
        ('docker exec insanity_postgres psql -U insanity -d insanity_cluster -c "\\dt" | findstr context', 
         "Table 'context' Exists"),
        
        ('docker exec insanity_postgres psql -U insanity -d insanity_cluster -c "\\dt" | findstr metrics', 
         "Table 'metrics' Exists"),
        
        ('docker exec insanity_postgres bash -c "PGPASSWORD=insanity_dev_password psql -h localhost -U insanity -d insanity_cluster -c \'SELECT 1;\'"', 
         "Password Authentication Works (inside container)"),
        
        ("docker exec insanity_redis redis-cli PING", 
         "Redis Responding"),
        
        ("curl -s http://localhost:6333/collections", 
         "Qdrant API Responding"),
        
        ("curl -s http://localhost:9090/-/healthy", 
         "Prometheus Healthy"),
        
        ("curl -s http://localhost:3000/api/health", 
         "Grafana Healthy"),
    ]
    
    results = []
    for cmd, desc in tests:
        results.append(run_command(cmd, desc))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! TABLE layer is fully operational!")
        print("\n📊 Access your services:")
        print("   - Grafana: http://localhost:3000 (admin/admin)")
        print("   - Prometheus: http://localhost:9090")
        print("   - Qdrant: http://localhost:6333/dashboard")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
