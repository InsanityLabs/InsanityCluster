# Insanity Cluster - Quick Start Guide

## 🚀 Start Everything (Recommended)

### Windows
```cmd
scripts\start_dev.bat
```

### Linux/Mac
```bash
chmod +x scripts/start_dev.sh
./scripts/start_dev.sh
```

This starts:
- ✅ PostgreSQL, Redis, Qdrant
- ✅ Backend API → `http://localhost:8000`
- ✅ Dashboard → `http://localhost:5173`
- ✅ Grafana → `http://localhost:3000`

## 🎨 Start Dashboard Only

If backend is already running:

### Windows
```cmd
scripts\start_dashboard.bat
```

### Linux/Mac
```bash
chmod +x scripts/start_dashboard.sh
./scripts/start_dashboard.sh
```

## 📝 Create Your First Task

### Via API
```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"command": "Analyze market trends"}'
```

### Via Python
```python
import requests

response = requests.post(
    "http://localhost:8000/tasks",
    json={"command": "Analyze market trends"}
)
print(response.json())
```

### Via Dashboard
1. Open `http://localhost:5173`
2. Go to Tasks tab
3. Watch your tasks appear in real-time!

## 🔍 Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Dashboard | http://localhost:5173 | - |
| API Docs | http://localhost:8000/docs | - |
| Grafana | http://localhost:3000 | admin/admin |
| Prometheus | http://localhost:9090 | - |

## 🛠️ Manual Setup

If you prefer manual control:

```bash
# 1. Start infrastructure
docker-compose up -d postgres redis qdrant

# 2. Activate Python environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate.bat  # Windows

# 3. Run migrations
alembic upgrade head

# 4. Start backend
python -m insanity_cluster.surface.main

# 5. Start dashboard (new terminal)
cd dashboard
npm run dev
```

## 📚 Full Documentation

- **Testing Guide**: See `TESTING_GUIDE.md` for comprehensive testing instructions
- **Dashboard Docs**: See `dashboard/IMPLEMENTATION.md` for dashboard details
- **API Docs**: Visit `http://localhost:8000/docs` when running

## 🐛 Troubleshooting

### Dashboard shows "Disconnected"
- Ensure backend is running on port 8000
- Check `dashboard/.env` file

### No tasks appearing
- Create a task via API first
- Check browser console (F12) for errors

### Port already in use
- Stop other services using ports 8000, 5173, 5432, 6379
- Or change ports in configuration files

## 🎯 Next Steps

1. ✅ Start the services
2. ✅ Open dashboard at `http://localhost:5173`
3. ✅ Create a test task
4. ✅ Explore the three main tabs:
   - **Tasks**: Monitor task execution
   - **Metrics**: View cost and performance
   - **Configuration**: Manage system settings

Happy coding! 🎉
