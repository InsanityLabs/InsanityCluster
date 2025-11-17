# SURFACE Layer Quick Start Guide

Get up and running with the SURFACE layer in 5 minutes!

## Prerequisites

- Python 3.11+
- Docker and Docker Compose (for Redis and PostgreSQL)
- Virtual environment (recommended)

## Step 1: Install Dependencies

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Start Infrastructure Services

```bash
# Start Redis and PostgreSQL
docker-compose up -d redis postgres

# Verify services are running
docker-compose ps
```

## Step 3: Initialize Database

```bash
# Run database migrations
alembic upgrade head

# Or use the init script
python scripts/init_database.py
```

## Step 4: Configure Environment

```bash
# Copy template
cp .env.template .env

# Edit .env file with your settings
# At minimum, set:
# - API_SECRET_KEY (generate a secure random string)
# - POSTGRES_PASSWORD (if changed from default)
```

## Step 5: Create Your First User

```bash
# Run the demo script to create a test user
python examples/surface_layer_demo.py
```

This will:
- Create a test user with email `demo@example.com`
- Generate an API key
- Display the API key (save this!)

## Step 6: Start the SURFACE Layer Server

```bash
# Using make
make dev-surface

# Or directly
python -m insanity_cluster.surface.main
```

The server will start on `http://localhost:8000`

## Step 7: Test the API

### Option A: Using curl

```bash
# Health check
curl http://localhost:8000/api/health

# Create a task (replace YOUR_API_KEY)
curl -X POST http://localhost:8000/api/tasks \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command": "Create a Python web scraper", "priority": 1}'

# Get task status (replace TASK_ID)
curl http://localhost:8000/api/tasks/TASK_ID \
  -H "X-API-Key: YOUR_API_KEY"
```

### Option B: Using the CLI

```bash
# Setup CLI
python -m insanity_cluster.surface.cli setup
# Enter API URL: http://localhost:8000/api
# Enter API Key: YOUR_API_KEY

# Submit a command
python -m insanity_cluster.surface.cli run Create a Python web scraper

# Check status
python -m insanity_cluster.surface.cli status TASK_ID

# Interactive mode
python -m insanity_cluster.surface.cli interactive
```

### Option C: Using the Web Interface

Open your browser and navigate to:
- API Documentation: http://localhost:8000/api/docs
- Alternative Docs: http://localhost:8000/api/redoc

## Step 8: Test WebSocket Streaming

Create a simple HTML file (`test_websocket.html`):

```html
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Test</title>
</head>
<body>
    <h1>WebSocket Test</h1>
    <div id="messages"></div>
    
    <script>
        const token = 'YOUR_API_KEY';  // Replace with your API key
        const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);
        
        ws.onopen = () => {
            console.log('Connected');
            document.getElementById('messages').innerHTML += '<p>Connected!</p>';
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Message:', data);
            document.getElementById('messages').innerHTML += 
                `<p>${data.type}: ${JSON.stringify(data)}</p>`;
            
            // Respond to ping
            if (data.type === 'ping') {
                ws.send(JSON.stringify({type: 'pong'}));
            }
        };
        
        ws.onerror = (error) => {
            console.error('Error:', error);
        };
        
        ws.onclose = () => {
            console.log('Disconnected');
        };
    </script>
</body>
</html>
```

Open the file in your browser to test WebSocket connection.

## Common Commands

### Server Management

```bash
# Start server
make dev-surface

# Start with auto-reload (development)
uvicorn insanity_cluster.surface.main:app --reload

# Start with specific host/port
uvicorn insanity_cluster.surface.main:app --host 0.0.0.0 --port 8080
```

### CLI Commands

```bash
# Submit command
ic run <your command here>

# Submit with streaming
ic run --stream <your command>

# Check status
ic status <task-id>

# Stream status updates
ic status --stream <task-id>

# List tasks
ic list

# List by status
ic list --status-filter completed

# Show config
ic config

# Interactive mode
ic interactive
```

### API Endpoints

- `GET /` - Service information
- `GET /api/health` - Health check
- `POST /api/tasks` - Create task
- `GET /api/tasks/{task_id}` - Get task status
- `GET /api/tasks` - List tasks
- `DELETE /api/tasks/{task_id}` - Cancel task
- `POST /api/webhooks` - Register webhook
- `DELETE /api/webhooks/{webhook_id}` - Delete webhook
- `WS /ws?token=<token>` - WebSocket connection

## Troubleshooting

### Server won't start

**Problem:** Port already in use
```bash
# Find process using port 8000
lsof -i :8000  # On Linux/Mac
netstat -ano | findstr :8000  # On Windows

# Kill the process or use a different port
uvicorn insanity_cluster.surface.main:app --port 8080
```

**Problem:** Database connection failed
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

**Problem:** Redis connection failed
```bash
# Check if Redis is running
docker-compose ps redis

# Check logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis
```

### Authentication issues

**Problem:** Invalid API key
- Verify the API key is correct
- Check if user exists in database
- Generate a new API key using the demo script

**Problem:** JWT token expired
- JWT tokens expire after 24 hours (configurable)
- Generate a new token or use API key authentication

### WebSocket issues

**Problem:** Connection refused
- Verify server is running
- Check WebSocket URL format: `ws://localhost:8000/ws?token=YOUR_KEY`
- Ensure token is provided in query parameter

**Problem:** Connection drops
- Check heartbeat interval (default 30s)
- Verify network stability
- Check server logs for errors

## Next Steps

1. **Explore the API:**
   - Visit http://localhost:8000/api/docs
   - Try different endpoints
   - Test with different commands

2. **Integrate with your application:**
   - Use the REST API for backend integration
   - Use WebSocket for realtime updates
   - Use CLI for command-line tools

3. **Customize configuration:**
   - Adjust JWT expiration
   - Configure CORS origins
   - Set rate limits (when implemented)

4. **Monitor performance:**
   - Check response times
   - Monitor WebSocket connections
   - Review logs for errors

5. **Prepare for INNER layer integration:**
   - The SURFACE layer is ready to integrate with INNER layer
   - Task queue is set up in Redis
   - Progress updates can be streamed via WebSocket

## Resources

- **Documentation:** `insanity_cluster/surface/README.md`
- **Implementation Details:** `insanity_cluster/surface/IMPLEMENTATION.md`
- **Demo Script:** `examples/surface_layer_demo.py`
- **API Docs:** http://localhost:8000/api/docs (when server is running)

## Getting Help

If you encounter issues:

1. Check the logs:
   ```bash
   # Server logs (if running in terminal)
   # Or check Docker logs
   docker-compose logs -f
   ```

2. Verify configuration:
   ```bash
   # Check .env file
   cat .env
   
   # Test database connection
   python scripts/init_database.py
   ```

3. Run the demo script:
   ```bash
   python examples/surface_layer_demo.py
   ```

4. Check service status:
   ```bash
   docker-compose ps
   ```

## Success Checklist

- [ ] Infrastructure services running (Redis, PostgreSQL)
- [ ] Database initialized
- [ ] Environment configured
- [ ] Test user created with API key
- [ ] Server started successfully
- [ ] Health check returns 200 OK
- [ ] Task creation works
- [ ] Task status retrieval works
- [ ] CLI commands work
- [ ] WebSocket connection established

Congratulations! You're now ready to use the SURFACE layer! 🎉
