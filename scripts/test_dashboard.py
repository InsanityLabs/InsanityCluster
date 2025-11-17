#!/usr/bin/env python3
"""
Simple test script to verify dashboard and API are working correctly.
"""

import requests
import time
import sys

API_URL = "http://localhost:8000"
DASHBOARD_URL = "http://localhost:5173"

def test_api_health():
    """Test if API is responding"""
    print("🔍 Testing API health...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is healthy")
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ API is not responding: {e}")
        return False

def test_dashboard():
    """Test if dashboard is responding"""
    print("🔍 Testing dashboard...")
    try:
        response = requests.get(DASHBOARD_URL, timeout=5)
        if response.status_code == 200:
            print("✅ Dashboard is accessible")
            return True
        else:
            print(f"❌ Dashboard returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Dashboard is not responding: {e}")
        return False

def test_create_task():
    """Test creating a task via API"""
    print("🔍 Testing task creation...")
    try:
        response = requests.post(
            f"{API_URL}/tasks",
            json={"command": "Test task from test script"},
            timeout=5
        )
        if response.status_code in [200, 201]:
            task_data = response.json()
            task_id = task_data.get("id")
            print(f"✅ Task created successfully: {task_id}")
            return task_id
        else:
            print(f"❌ Failed to create task: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to create task: {e}")
        return None

def test_get_tasks():
    """Test retrieving tasks"""
    print("🔍 Testing task retrieval...")
    try:
        response = requests.get(f"{API_URL}/tasks", timeout=5)
        if response.status_code == 200:
            tasks = response.json()
            print(f"✅ Retrieved {len(tasks)} tasks")
            return True
        else:
            print(f"❌ Failed to retrieve tasks: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to retrieve tasks: {e}")
        return False

def test_metrics():
    """Test metrics endpoints"""
    print("🔍 Testing metrics endpoints...")
    endpoints = [
        "/metrics/cost",
        "/metrics/latency",
        "/metrics/system"
    ]
    
    all_ok = True
    for endpoint in endpoints:
        try:
            response = requests.get(f"{API_URL}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"  ✅ {endpoint}")
            else:
                print(f"  ❌ {endpoint} returned {response.status_code}")
                all_ok = False
        except requests.exceptions.RequestException as e:
            print(f"  ❌ {endpoint} failed: {e}")
            all_ok = False
    
    if all_ok:
        print("✅ All metrics endpoints working")
    return all_ok

def test_configuration():
    """Test configuration endpoint"""
    print("🔍 Testing configuration endpoint...")
    try:
        response = requests.get(f"{API_URL}/config", timeout=5)
        if response.status_code == 200:
            print("✅ Configuration endpoint working")
            return True
        else:
            print(f"❌ Configuration endpoint returned {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Configuration endpoint failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Insanity Cluster Dashboard Test Suite")
    print("=" * 60)
    print()
    
    results = []
    
    # Test API
    results.append(("API Health", test_api_health()))
    print()
    
    # Test Dashboard
    results.append(("Dashboard", test_dashboard()))
    print()
    
    # Test Task Creation
    task_id = test_create_task()
    results.append(("Task Creation", task_id is not None))
    print()
    
    # Test Task Retrieval
    results.append(("Task Retrieval", test_get_tasks()))
    print()
    
    # Test Metrics
    results.append(("Metrics", test_metrics()))
    print()
    
    # Test Configuration
    results.append(("Configuration", test_configuration()))
    print()
    
    # Summary
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print("🎉 All tests passed! Your dashboard is ready to use.")
        print()
        print("Next steps:")
        print("  1. Open http://localhost:5173 in your browser")
        print("  2. Explore the Tasks, Metrics, and Configuration tabs")
        print("  3. Create more tasks and watch them in real-time!")
        return 0
    else:
        print()
        print("⚠️  Some tests failed. Please check the errors above.")
        print()
        print("Common issues:")
        print("  - Make sure backend is running: python -m insanity_cluster.surface.main")
        print("  - Make sure dashboard is running: cd dashboard && npm run dev")
        print("  - Check if ports 8000 and 5173 are available")
        return 1

if __name__ == "__main__":
    sys.exit(main())
