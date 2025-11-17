# WebSocket API Documentation

## Overview

The Insanity Cluster WebSocket API provides real-time bidirectional communication for task updates, system notifications, and streaming responses.

## Connection

### Endpoint

```
ws://localhost:8000/ws
wss://api.insanitycluster.com/ws
```

### Authentication

Include authentication in the connection URL or initial message:

**Option 1: Query Parameter**
```
ws://localhost:8000/ws?token=<jwt_token>
```

**Option 2: Initial Message**
```json
{
  "type": "auth",
  "token": "<jwt_token>"
}
```

### Connection Example

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=YOUR_JWT_TOKEN');

ws.onopen = () => {
  console.log('Connected to Insanity Cluster');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  handleMessage(message);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from Insanity Cluster');
  // Implement reconnection logic
};
```

## Message Types

### Client → Server Messages

#### 1. Subscribe to Task Updates

Subscribe to real-time updates for a specific task.

```json
{
  "type": "subscribe",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "type": "subscribed",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success"
}
```

#### 2. Unsubscribe from Task Updates

Stop receiving updates for a task.

```json
{
  "type": "unsubscribe",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### 3. Ping

Keep the connection alive.

```json
{
  "type": "ping"
}
```

**Response:**
```json
{
  "type": "pong",
  "timestamp": "2025-11-16T10:30:00Z"
}
```

### Server → Client Messages

#### 1. Task Status Update

Sent when task status changes.

```json
{
  "type": "task_update",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "executing",
  "progress": {
    "current_step": 3,
    "total_steps": 10,
    "percentage": 30.0
  },
  "message": "Developer Agent is generating code...",
  "timestamp": "2025-11-16T10:30:00Z"
}
```

#### 2. Subtask Update

Sent when a subtask starts or completes.

```json
{
  "type": "subtask_update",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "subtask_id": "subtask-001",
  "status": "completed",
  "agent": "DeveloperAgent",
  "description": "Generate Python function for data processing",
  "result": {
    "output": "Function generated successfully",
    "cost": 0.05,
    "latency_ms": 1200
  },
  "timestamp": "2025-11-16T10:30:15Z"
}
```

#### 3. Streaming Response

Real-time token-by-token output from AI models.

```json
{
  "type": "stream",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "subtask_id": "subtask-001",
  "chunk": "def process_data(input_list):\n",
  "is_final": false,
  "timestamp": "2025-11-16T10:30:16Z"
}
```

When streaming is complete:
```json
{
  "type": "stream",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "subtask_id": "subtask-001",
  "chunk": "",
  "is_final": true,
  "timestamp": "2025-11-16T10:30:20Z"
}
```

#### 4. Task Completed

Sent when task execution finishes.

```json
{
  "type": "task_completed",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "output": "Task completed successfully",
    "artifacts": [
      {
        "type": "file",
        "name": "data_processor.py",
        "url": "https://storage.insanitycluster.com/artifacts/..."
      }
    ]
  },
  "metrics": {
    "total_cost": 0.25,
    "total_latency_ms": 5400,
    "models_used": ["claude-sonnet-4.5", "gpt-5-mini"]
  },
  "timestamp": "2025-11-16T10:35:00Z"
}
```

#### 5. Task Failed

Sent when task execution fails.

```json
{
  "type": "task_failed",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error": {
    "message": "Agent execution failed",
    "code": "AGENT_ERROR",
    "details": {
      "agent": "DeveloperAgent",
      "subtask_id": "subtask-003",
      "reason": "Model API timeout"
    }
  },
  "timestamp": "2025-11-16T10:32:00Z"
}
```

#### 6. System Notification

General system notifications.

```json
{
  "type": "notification",
  "level": "warning",
  "message": "Approaching daily cost limit (80% used)",
  "details": {
    "current_cost": 40.00,
    "daily_limit": 50.00
  },
  "timestamp": "2025-11-16T10:30:00Z"
}
```

Notification levels: `info`, `warning`, `error`

#### 7. Agent Activity

Real-time agent status updates.

```json
{
  "type": "agent_activity",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent": "DeveloperAgent",
  "activity": "Reviewing generated code",
  "model_used": "claude-sonnet-4.5",
  "timestamp": "2025-11-16T10:30:10Z"
}
```

## Connection Management

### Heartbeat

The server sends ping messages every 30 seconds. Clients should respond with pong to maintain the connection.

**Server Ping:**
```json
{
  "type": "ping",
  "timestamp": "2025-11-16T10:30:00Z"
}
```

**Client Pong:**
```json
{
  "type": "pong"
}
```

### Reconnection

If the connection is lost, implement exponential backoff for reconnection:

```javascript
let reconnectDelay = 1000; // Start with 1 second
const maxReconnectDelay = 30000; // Max 30 seconds

function connect() {
  const ws = new WebSocket('ws://localhost:8000/ws?token=YOUR_TOKEN');
  
  ws.onopen = () => {
    console.log('Connected');
    reconnectDelay = 1000; // Reset delay on successful connection
  };
  
  ws.onclose = () => {
    console.log(`Reconnecting in ${reconnectDelay}ms...`);
    setTimeout(connect, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, maxReconnectDelay);
  };
  
  return ws;
}

const ws = connect();
```

## Error Handling

### Error Message Format

```json
{
  "type": "error",
  "code": "INVALID_MESSAGE",
  "message": "Invalid message format",
  "details": {
    "expected": "JSON object with 'type' field",
    "received": "invalid json"
  },
  "timestamp": "2025-11-16T10:30:00Z"
}
```

### Common Error Codes

- `AUTH_REQUIRED`: Authentication required
- `AUTH_FAILED`: Authentication failed
- `INVALID_MESSAGE`: Invalid message format
- `TASK_NOT_FOUND`: Task ID not found
- `SUBSCRIPTION_FAILED`: Failed to subscribe to task
- `RATE_LIMIT_EXCEEDED`: Too many messages sent

## Complete Example

```javascript
class InsanityClusterClient {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
    this.subscriptions = new Set();
  }

  connect() {
    this.ws = new WebSocket(`ws://localhost:8000/ws?token=${this.token}`);
    
    this.ws.onopen = () => {
      console.log('Connected to Insanity Cluster');
      this.reconnectDelay = 1000;
      
      // Re-subscribe to tasks after reconnection
      this.subscriptions.forEach(taskId => {
        this.subscribeToTask(taskId);
      });
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    this.ws.onclose = () => {
      console.log(`Connection closed. Reconnecting in ${this.reconnectDelay}ms...`);
      setTimeout(() => this.connect(), this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
    };
  }

  subscribeToTask(taskId) {
    this.subscriptions.add(taskId);
    this.send({
      type: 'subscribe',
      task_id: taskId
    });
  }

  unsubscribeFromTask(taskId) {
    this.subscriptions.delete(taskId);
    this.send({
      type: 'unsubscribe',
      task_id: taskId
    });
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('WebSocket not connected');
    }
  }

  handleMessage(message) {
    switch (message.type) {
      case 'task_update':
        console.log(`Task ${message.task_id}: ${message.status} (${message.progress.percentage}%)`);
        break;
      
      case 'stream':
        process.stdout.write(message.chunk);
        if (message.is_final) {
          console.log('\n[Stream complete]');
        }
        break;
      
      case 'task_completed':
        console.log(`Task ${message.task_id} completed!`);
        console.log(`Cost: $${message.metrics.total_cost}`);
        console.log(`Latency: ${message.metrics.total_latency_ms}ms`);
        break;
      
      case 'task_failed':
        console.error(`Task ${message.task_id} failed: ${message.error.message}`);
        break;
      
      case 'notification':
        console.log(`[${message.level.toUpperCase()}] ${message.message}`);
        break;
      
      case 'ping':
        this.send({ type: 'pong' });
        break;
      
      case 'error':
        console.error(`Error: ${message.message} (${message.code})`);
        break;
      
      default:
        console.log('Unknown message type:', message.type);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage
const client = new InsanityClusterClient('your-jwt-token');
client.connect();

// Subscribe to a task
client.subscribeToTask('550e8400-e29b-41d4-a716-446655440000');

// Later, unsubscribe
// client.unsubscribeFromTask('550e8400-e29b-41d4-a716-446655440000');

// Disconnect when done
// client.disconnect();
```

## Best Practices

1. **Always implement reconnection logic** - Network issues are common
2. **Handle all message types** - Don't assume you'll only receive expected messages
3. **Respond to pings** - Keep the connection alive
4. **Validate messages** - Check for required fields before processing
5. **Limit subscriptions** - Don't subscribe to too many tasks simultaneously
6. **Clean up subscriptions** - Unsubscribe when you no longer need updates
7. **Use exponential backoff** - Avoid overwhelming the server during reconnection
8. **Log errors** - Track connection issues for debugging

## Rate Limits

- Maximum 100 subscriptions per connection
- Maximum 10 messages per second per connection
- Ping/pong messages don't count toward rate limits

## Security

- Always use WSS (WebSocket Secure) in production
- Never expose JWT tokens in client-side code
- Implement token refresh before expiration
- Validate all incoming messages
- Use HMAC signatures for webhook verification
