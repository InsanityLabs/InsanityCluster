#!/bin/bash
# Test TABLE layer from inside Docker container

echo "Testing TABLE layer components from inside Docker..."
echo ""

# Test PostgreSQL
echo "1. Testing PostgreSQL..."
docker exec insanity_postgres psql -U insanity -d insanity_cluster -c "SELECT 'PostgreSQL is working!' as status, COUNT(*) as user_count FROM users;" && echo "✅ PostgreSQL: PASS" || echo "❌ PostgreSQL: FAIL"
echo ""

# Test Redis
echo "2. Testing Redis..."
docker exec insanity_redis redis-cli PING && echo "✅ Redis: PASS" || echo "❌ Redis: FAIL"
echo ""

# Test Qdrant
echo "3. Testing Qdrant..."
curl -s http://localhost:6333/collections | grep -q "task_patterns" && echo "✅ Qdrant: PASS" || echo "❌ Qdrant: FAIL"
echo ""

# Test Prometheus
echo "4. Testing Prometheus..."
curl -s http://localhost:9090/-/healthy | grep -q "Prometheus" && echo "✅ Prometheus: PASS" || echo "❌ Prometheus: FAIL"
echo ""

# Test Grafana
echo "5. Testing Grafana..."
curl -s http://localhost:3000/api/health | grep -q "ok" && echo "✅ Grafana: PASS" || echo "❌ Grafana: FAIL"
echo ""

echo "========================================="
echo "TABLE Layer Infrastructure Test Complete"
echo "========================================="
