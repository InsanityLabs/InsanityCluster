# SURFACE Layer

The SURFACE layer is the user interface and interaction layer of the Insanity Cluster. It provides multiple interfaces for users to interact with the system.

## Components

### 1. Command Parser (`command_parser.py`)
Parses natural language commands into structured format using lightweight models.

**Features:**
- Pattern-based quick matching for common intents
- Model-based parsing for complex commands
- Redis caching for common command patterns
- Clarification request generation for ambiguous commands
- Parameter extraction for different intent types

**Usage:**
```python
from insanity_cluster.surface import CommandParser
from insanity_cluster.table.redis_manager import RedisManager

redis_manager = RedisManager()
parser = CommandParser(redis_manager)

parsed = parser.parse("Create a Python web scraper", user_id="user123")
print(f"Intent: {parsed.intent}")
print(f"Confidence: {parsed.confidence}")
```

### 2. Authentication & Session Management (`auth.py`)
Handles authentication, authorization, and session management.

**Features:**
- API key authentication with secure hashing
- JWT token authentication
- Role-based access control (RBAC) with admin, user, readonly roles
- API key generation and rotation
- Redis-based session management
- FastAPI dependency functions for easy integration

**Usage:**
```python
from insanity_cluster.surface import AuthManager, UserRole
from insanity_cluster.table.database import DatabaseManager
from insanity_cluster.table.redis_manager import RedisManager

db_manager = DatabaseManager()
redis_manager = RedisManager()
auth_manager = AuthManager(db_manager, redis_manager)

# Generate API key
api_key, api_key_hash = auth_manager.generate_api_key()

# Verify API key
user = await auth_manager.verify_api_key(api_key)

# Create JWT token
token = auth_manager.create_jwt_token(str(user.id), user.role)

# Create session
session_id = await auth_manager.create_session(str(user.id))
```

### 3. REST API Gateway (`api.py`)
FastAPI application providing REST endpoints for task management and webhooks.

**Endpoints:**
- `POST /tasks` - Create a new task
- `GET /tasks/{task_id}` - Get task status
- `GET /tasks` - List tasks
- `DELETE /tasks/{task_id}` - Cancel a task
- `POST /webhooks` - Register webhook
- `DELETE /webhooks/{webhook_id}` - Delete webhook
- `POST /admin/users` - Create user (admin only)

**Usage:**
```bash
# Create a task
curl -X POST http://localhost:8000/api/tasks \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"command": "Create a Python web scraper", "priority": 1}'

# Get task status
curl http://localhost:8000/api/tasks/{task_id} \
  -H "X-API-Key: your_api_key"
```

### 4. WebSocket Server (`websocket_server.py`)
Realtime bidirectional communication with clients.

**Features:**
- WebSocket connections with authentication
- Heartbeat mechanism (ping/pong every 30s)
- Task progress streaming
- System event broadcasting
- Connection management with automatic cleanup
- Subscription-based updates

**Usage:**
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws?token=your_api_key');

// Subscribe to task updates
ws.send(JSON.stringify({
  type: 'subscribe',
  task_id: 'task-id-here'
}));

// Receive updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

### 5. CLI Interface (`cli.py`)
Command-line interface for interacting with the system.

**Features:**
- Natural language command submission
- Task status checking
- Task listing with filters
- Realtime progress streaming
- Interactive mode
- Configuration management

**Usage:**
```bash
# Setup CLI
ic setup

# Submit a command
ic run Create a Python web scraper

# Submit with streaming
ic run --stream Write a REST API in FastAPI

# Check task status
ic status <task-id>

# Stream task updates
ic status --stream <task-id>

# List recent tasks
ic list

# List by status
ic list --status-filter completed

# Interactive mode
ic interactive

# Show configuration
ic config
```

### 6. Main Server (`main.py`)
Entry point that integrates all SURFACE layer components.

**Usage:**
```bash
# Run the server
python -m insanity_cluster.surface.main

# Or with uvicorn directly
uvicorn insanity_cluster.surface.main:app --host 0.0.0.0 --port 8000
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      SURFACE LAYER                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   CLI        │  │   REST API   │  │  WebSocket   │    │
│  │  Interface   │  │   Gateway    │  │   Server     │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
│  ┌──────────────┐  ┌──────┴───────┐  ┌──────────────┐    │
│  │   Command    │  │     Auth     │  │   Session    │    │
│  │   Parser     │  │   Manager    │  │   Manager    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    INNER LAYER (Task Queue)
```

## Data Flow

1. **Command Ingestion:**
   - User submits command via CLI, API, or WebSocket
   - Command Parser extracts intent and parameters
   - Auth Manager validates user credentials

2. **Task Creation:**
   - Task created in database with "pending" status
   - Task queued in Redis for INNER layer processing
   - Task ID returned to user immediately (< 100ms)

3. **Progress Updates:**
   - INNER layer updates task progress in Redis
   - WebSocket server streams updates to connected clients
   - CLI displays realtime progress

4. **Task Completion:**
   - Task result stored in database
   - Webhooks triggered for registered URLs
   - Final status available via API

## Configuration

Configuration is managed through environment variables (see `.env.template`):

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_SECRET_KEY=your-secret-key-change-this

# JWT Configuration
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# WebSocket Configuration
WS_HEARTBEAT_INTERVAL=30
WS_MAX_CONNECTIONS=1000

# CORS Configuration
ENABLE_CORS=true
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

## Testing

Run tests for SURFACE layer:

```bash
# Run all tests
pytest tests/surface/

# Run specific test file
pytest tests/surface/test_command_parser.py

# Run with coverage
pytest tests/surface/ --cov=insanity_cluster.surface
```

## Performance Targets

- **Command Acknowledgment:** < 100ms
- **Command Parsing:** < 50ms (cached), < 200ms (model-based)
- **WebSocket Latency:** < 50ms for message delivery
- **API Response Time:** < 100ms for status queries
- **Concurrent Connections:** Support 1000+ WebSocket connections

## Security

- **Authentication:** API key or JWT token required for all endpoints
- **Authorization:** Role-based access control (RBAC)
- **API Key Storage:** SHA-256 hashed in database
- **Session Management:** Redis-based with TTL
- **Rate Limiting:** Configurable per endpoint (future)
- **CORS:** Configurable allowed origins

## Dependencies

- **FastAPI:** Web framework and API gateway
- **uvicorn:** ASGI server
- **websockets:** WebSocket client/server
- **click:** CLI framework
- **rich:** Terminal formatting and progress bars
- **httpx:** Async HTTP client
- **PyJWT:** JWT token handling
- **redis:** Session and cache management
- **SQLAlchemy:** Database ORM

## Future Enhancements

- [ ] Rate limiting per user/endpoint
- [ ] API key scopes and permissions
- [ ] OAuth 2.0 integration
- [ ] GraphQL API endpoint
- [ ] Web dashboard (React/Vue)
- [ ] Mobile app support
- [ ] Voice interface integration
- [ ] Multi-language support
- [ ] Advanced analytics dashboard
