#!/bin/bash
# Development startup script for Insanity Cluster with Dashboard

set -e

echo "🚀 Starting Insanity Cluster Development Environment"
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}⚠️  docker-compose not found. Please install Docker and Docker Compose.${NC}"
    exit 1
fi

# Check if node is available
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠️  Node.js not found. Please install Node.js 20+.${NC}"
    exit 1
fi

# Start infrastructure services
echo -e "\n${BLUE}📦 Starting infrastructure services (PostgreSQL, Redis, Qdrant)...${NC}"
docker-compose up -d postgres redis qdrant

# Wait for services to be ready
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"
sleep 5

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating one...${NC}"
    python -m venv venv
fi

# Activate virtual environment
echo -e "${BLUE}🐍 Activating Python virtual environment...${NC}"
source venv/bin/activate

# Install Python dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo -e "${BLUE}📥 Installing Python dependencies...${NC}"
    pip install -r requirements.txt
    touch venv/.installed
fi

# Run database migrations
echo -e "${BLUE}🗄️  Running database migrations...${NC}"
alembic upgrade head

# Start the backend API server in background
echo -e "${GREEN}✅ Starting backend API server on http://localhost:8000${NC}"
python -m insanity_cluster.surface.main &
BACKEND_PID=$!

# Wait for backend to start
echo -e "${BLUE}⏳ Waiting for backend to start...${NC}"
sleep 3

# Start the dashboard dev server
echo -e "${GREEN}✅ Starting dashboard dev server on http://localhost:5173${NC}"
cd dashboard
npm run dev &
DASHBOARD_PID=$!
cd ..

echo -e "\n${GREEN}=================================================="
echo -e "🎉 Development environment is ready!"
echo -e "=================================================="
echo -e "Backend API:  ${BLUE}http://localhost:8000${NC}"
echo -e "Dashboard:    ${BLUE}http://localhost:5173${NC}"
echo -e "Grafana:      ${BLUE}http://localhost:3000${NC} (admin/admin)"
echo -e "Prometheus:   ${BLUE}http://localhost:9090${NC}"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Trap Ctrl+C and cleanup
cleanup() {
    echo -e "\n${YELLOW}🛑 Stopping services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $DASHBOARD_PID 2>/dev/null || true
    docker-compose down
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

trap cleanup INT TERM

# Wait for processes
wait
