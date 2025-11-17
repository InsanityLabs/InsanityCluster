#!/bin/bash
# Quick start script for dashboard development

set -e

echo "🎨 Starting Insanity Cluster Dashboard"
echo "======================================"

# Check if node is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js 20+"
    exit 1
fi

# Check if dashboard dependencies are installed
if [ ! -d "dashboard/node_modules" ]; then
    echo "📥 Installing dashboard dependencies..."
    cd dashboard
    npm install
    cd ..
fi

# Start the dashboard
echo "✅ Starting dashboard on http://localhost:5173"
echo ""
echo "Note: Make sure the backend API is running on http://localhost:8000"
echo "      You can start it with: python -m insanity_cluster.surface.main"
echo ""

cd dashboard
npm run dev
