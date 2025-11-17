# Webhook Integration Guide

## Overview

Webhooks allow you to receive real-time notifications when tasks complete, fail, or are cancelled. Instead of polling the API for task status, the Insanity Cluster will send HTTP POST requests to your specified endpoint.

## Quick Start

### 1. Register a Webhook

```bash
curl -X POST https://api.insanitycluster.com/v1/webhooks \
  -H "X-API-Key: ic_live_1234567890abcdef" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://yourapp.com/webhooks/insanity-cluster",
    "events": ["task.completed", "task.failed"],
    "secret": "your_webhook_secret_key"
  }'
```

**Response:**
```json
{
  "webhook_id": "wh_550e8400e29b41d4a716446655440000",
  "url": "https://yourapp.com/webhooks/insanity-cluster",
  "events": ["task.completed", "task.failed"],
  "created_at": "2025-11-16T10:30:00Z"
}
```

### 2. Handle Webhook Events

Create an endpoint to receive webhook events:

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)
WEBHOOK_SECRET = "your_webhook_secret_key"

@app.route('/webhooks/insanity-cluster', methods=['POST'])
def handle_webhook():
    # Verify signature
    signature = request.headers.get('X-Insanity-Signature')
    if not verify_signature(request.data, signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Parse event
    event = request.json
    event_type = event['type']
    
    if event_type == 'task.completed':
        handle_task_completed(event)
    elif event_type == 'task.failed':
        handle_task_failed(event)
    
    return jsonify({'status': 'received'}), 200

def verify_signature(payload, signature):
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

def handle_task_completed(event):
    task_id = event['data']['task_id']
    result = event['data']['result']
    print(f"Task {task_id} completed: {result}")

def handle_task_failed(event):
    task_id = event['data']['task_id']
    error = event['data']['error']
    print(f"Task {task_id} failed: {error}")
```

## Event Types

### task.completed

Sent when a task completes successfully.

**Payload:**
```json
{
  "type": "task.completed",
  "id": "evt_123456",
  "created_at": "2025-11-16T10:35:00Z",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "completed",
    "command": "Write a Python function to calculate fibonacci numbers",
    "result": {
      "output": "Function generated successfully",
      "artifacts": [
        {
          "type": "file",
          "name": "fibonacci.py",
          "url": "https://storage.insanitycluster.com/artifacts/fibonacci.py",
          "size": 1024
        }
      ]
    },
    "metrics": {
      "total_cost": 0.15,
      "total_latency_ms": 3200,
      "models_used": ["claude-sonnet-4.5"],
      "agents_used": ["DeveloperAgent"]
    },
    "completed_at": "2025-11-16T10:35:00Z"
  }
}
```

### task.failed

Sent when a task fails.

**Payload:**
```json
{
  "type": "task.failed",
  "id": "evt_123457",
  "created_at": "2025-11-16T10:32:00Z",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "failed",
    "command": "Write a Python function",
    "error": {
      "message": "Agent execution failed",
      "code": "AGENT_ERROR",
      "details": {
        "agent": "DeveloperAgent",
        "subtask_id": "subtask-003",
        "reason": "Model API timeout after 3 retries"
      }
    },
    "metrics": {
      "total_cost": 0.05,
      "total_latency_ms": 15000,
      "retry_count": 3
    },
    "failed_at": "2025-11-16T10:32:00Z"
  }
}
```

### task.cancelled

Sent when a task is cancelled by the user.

**Payload:**
```json
{
  "type": "task.cancelled",
  "id": "evt_123458",
  "created_at": "2025-11-16T10:33:00Z",
  "data": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "cancelled",
    "command": "Write a Python function",
    "cancelled_by": "user_123",
    "reason": "User requested cancellation",
    "metrics": {
      "total_cost": 0.02,
      "total_latency_ms": 1500,
      "completed_subtasks": 2,
      "total_subtasks": 5
    },
    "cancelled_at": "2025-11-16T10:33:00Z"
  }
}
```

## Security

### Signature Verification

All webhook requests include an `X-Insanity-Signature` header containing an HMAC SHA-256 signature of the request body.

**Verification Process:**

1. Extract the signature from the `X-Insanity-Signature` header
2. Compute HMAC SHA-256 of the raw request body using your webhook secret
3. Compare the computed signature with the received signature using constant-time comparison

**Python Example:**
```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    """
    Verify webhook signature
    
    Args:
        payload: Raw request body (bytes)
        signature: Signature from X-Insanity-Signature header (str)
        secret: Your webhook secret (str)
    
    Returns:
        bool: True if signature is valid
    """
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

# Usage in Flask
@app.route('/webhooks/insanity-cluster', methods=['POST'])
def webhook():
    signature = request.headers.get('X-Insanity-Signature')
    if not verify_webhook_signature(request.data, signature, WEBHOOK_SECRET):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Process webhook...
```

**Node.js Example:**
```javascript
const crypto = require('crypto');

function verifyWebhookSignature(payload, signature, secret) {
  const expectedSignature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}

// Usage in Express
app.post('/webhooks/insanity-cluster', express.raw({type: 'application/json'}), (req, res) => {
  const signature = req.headers['x-insanity-signature'];
  
  if (!verifyWebhookSignature(req.body, signature, WEBHOOK_SECRET)) {
    return res.status(401).json({error: 'Invalid signature'});
  }
  
  // Process webhook...
  res.json({status: 'received'});
});
```

### Best Practices

1. **Always verify signatures** - Never process webhooks without verification
2. **Use HTTPS** - Only accept webhooks over HTTPS
3. **Keep secrets secure** - Store webhook secrets in environment variables
4. **Implement idempotency** - Handle duplicate webhook deliveries
5. **Return quickly** - Respond within 5 seconds to avoid timeouts
6. **Process asynchronously** - Queue webhook processing for long-running tasks

## Webhook Management

### List Webhooks

```bash
curl -X GET https://api.insanitycluster.com/v1/webhooks \
  -H "X-API-Key: ic_live_1234567890abcdef"
```

**Response:**
```json
{
  "webhooks": [
    {
      "webhook_id": "wh_550e8400e29b41d4a716446655440000",
      "url": "https://yourapp.com/webhooks/insanity-cluster",
      "events": ["task.completed", "task.failed"],
      "created_at": "2025-11-16T10:30:00Z",
      "last_delivery": "2025-11-16T11:00:00Z",
      "status": "active"
    }
  ]
}
```

### Update Webhook

```bash
curl -X PUT https://api.insanitycluster.com/v1/webhooks/wh_550e8400e29b41d4a716446655440000 \
  -H "X-API-Key: ic_live_1234567890abcdef" \
  -H "Content-Type: application/json" \
  -d '{
    "events": ["task.completed", "task.failed", "task.cancelled"]
  }'
```

### Delete Webhook

```bash
curl -X DELETE https://api.insanitycluster.com/v1/webhooks/wh_550e8400e29b41d4a716446655440000 \
  -H "X-API-Key: ic_live_1234567890abcdef"
```

## Delivery Behavior

### Retry Logic

If your endpoint fails to respond or returns an error status code (5xx or 4xx), the Insanity Cluster will retry delivery:

- **Retry Schedule**: 1 minute, 5 minutes, 15 minutes, 1 hour, 6 hours
- **Max Retries**: 5 attempts
- **Timeout**: 5 seconds per attempt

### Delivery Headers

All webhook requests include these headers:

```
Content-Type: application/json
X-Insanity-Signature: <hmac_signature>
X-Insanity-Event-Type: task.completed
X-Insanity-Event-Id: evt_123456
X-Insanity-Delivery-Id: del_789012
X-Insanity-Delivery-Attempt: 1
User-Agent: InsanityCluster-Webhook/1.0
```

### Expected Response

Your endpoint should respond with:
- **Status Code**: 200-299 (success) or 410 (disable webhook)
- **Response Time**: < 5 seconds
- **Body**: Optional JSON acknowledgment

```json
{
  "status": "received",
  "message": "Webhook processed successfully"
}
```

### Disabling Webhooks

If your endpoint returns `410 Gone`, the webhook will be automatically disabled:

```python
@app.route('/webhooks/insanity-cluster', methods=['POST'])
def webhook():
    # Disable this webhook
    return jsonify({'message': 'Webhook disabled'}), 410
```

## Testing Webhooks

### Test Endpoint

Use webhook.site or similar services for testing:

```bash
# Register test webhook
curl -X POST https://api.insanitycluster.com/v1/webhooks \
  -H "X-API-Key: ic_live_1234567890abcdef" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://webhook.site/your-unique-url",
    "events": ["task.completed"]
  }'
```

### Send Test Event

Trigger a test webhook delivery:

```bash
curl -X POST https://api.insanitycluster.com/v1/webhooks/wh_550e8400e29b41d4a716446655440000/test \
  -H "X-API-Key: ic_live_1234567890abcdef"
```

**Test Payload:**
```json
{
  "type": "test",
  "id": "evt_test_123",
  "created_at": "2025-11-16T10:30:00Z",
  "data": {
    "message": "This is a test webhook event"
  }
}
```

### Local Testing with ngrok

For local development, use ngrok to expose your local server:

```bash
# Start ngrok
ngrok http 5000

# Register webhook with ngrok URL
curl -X POST https://api.insanitycluster.com/v1/webhooks \
  -H "X-API-Key: ic_live_1234567890abcdef" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://abc123.ngrok.io/webhooks/insanity-cluster",
    "events": ["task.completed"]
  }'
```

## Complete Implementation Examples

### Python (Flask)

```python
from flask import Flask, request, jsonify
import hmac
import hashlib
import json
from datetime import datetime

app = Flask(__name__)
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

# Store processed event IDs to handle duplicates
processed_events = set()

@app.route('/webhooks/insanity-cluster', methods=['POST'])
def handle_webhook():
    # Verify signature
    signature = request.headers.get('X-Insanity-Signature')
    if not verify_signature(request.data, signature):
        app.logger.warning('Invalid webhook signature')
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Parse event
    event = request.json
    event_id = event['id']
    
    # Check for duplicate
    if event_id in processed_events:
        app.logger.info(f'Duplicate event {event_id}, skipping')
        return jsonify({'status': 'duplicate'}), 200
    
    # Process event
    try:
        process_event(event)
        processed_events.add(event_id)
        return jsonify({'status': 'received'}), 200
    except Exception as e:
        app.logger.error(f'Error processing webhook: {e}')
        return jsonify({'error': 'Processing failed'}), 500

def verify_signature(payload, signature):
    if not signature:
        return False
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

def process_event(event):
    event_type = event['type']
    data = event['data']
    
    if event_type == 'task.completed':
        task_id = data['task_id']
        result = data['result']
        print(f"Task {task_id} completed")
        # Send notification, update database, etc.
        
    elif event_type == 'task.failed':
        task_id = data['task_id']
        error = data['error']
        print(f"Task {task_id} failed: {error['message']}")
        # Alert team, retry task, etc.
        
    elif event_type == 'task.cancelled':
        task_id = data['task_id']
        print(f"Task {task_id} cancelled")
        # Clean up resources, etc.

if __name__ == '__main__':
    app.run(port=5000)
```

### Node.js (Express)

```javascript
const express = require('express');
const crypto = require('crypto');

const app = express();
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET;

// Store processed event IDs
const processedEvents = new Set();

// Use raw body parser for signature verification
app.post('/webhooks/insanity-cluster', 
  express.raw({type: 'application/json'}),
  async (req, res) => {
    // Verify signature
    const signature = req.headers['x-insanity-signature'];
    if (!verifySignature(req.body, signature)) {
      console.warn('Invalid webhook signature');
      return res.status(401).json({error: 'Invalid signature'});
    }
    
    // Parse event
    const event = JSON.parse(req.body.toString());
    const eventId = event.id;
    
    // Check for duplicate
    if (processedEvents.has(eventId)) {
      console.log(`Duplicate event ${eventId}, skipping`);
      return res.json({status: 'duplicate'});
    }
    
    // Process event asynchronously
    processEvent(event).catch(err => {
      console.error('Error processing webhook:', err);
    });
    
    // Respond immediately
    processedEvents.add(eventId);
    res.json({status: 'received'});
  }
);

function verifySignature(payload, signature) {
  if (!signature) return false;
  
  const expectedSignature = crypto
    .createHmac('sha256', WEBHOOK_SECRET)
    .update(payload)
    .digest('hex');
  
  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(expectedSignature)
  );
}

async function processEvent(event) {
  const { type, data } = event;
  
  switch (type) {
    case 'task.completed':
      console.log(`Task ${data.task_id} completed`);
      // Send notification, update database, etc.
      break;
      
    case 'task.failed':
      console.log(`Task ${data.task_id} failed: ${data.error.message}`);
      // Alert team, retry task, etc.
      break;
      
    case 'task.cancelled':
      console.log(`Task ${data.task_id} cancelled`);
      // Clean up resources, etc.
      break;
  }
}

app.listen(5000, () => {
  console.log('Webhook server listening on port 5000');
});
```

## Monitoring Webhooks

### Delivery Logs

View webhook delivery history:

```bash
curl -X GET https://api.insanitycluster.com/v1/webhooks/wh_550e8400e29b41d4a716446655440000/deliveries \
  -H "X-API-Key: ic_live_1234567890abcdef"
```

**Response:**
```json
{
  "deliveries": [
    {
      "delivery_id": "del_789012",
      "event_id": "evt_123456",
      "event_type": "task.completed",
      "status": "success",
      "status_code": 200,
      "attempt": 1,
      "delivered_at": "2025-11-16T11:00:00Z",
      "response_time_ms": 150
    },
    {
      "delivery_id": "del_789013",
      "event_id": "evt_123457",
      "event_type": "task.failed",
      "status": "failed",
      "status_code": 500,
      "attempt": 3,
      "delivered_at": "2025-11-16T11:15:00Z",
      "response_time_ms": 5000,
      "error": "Connection timeout"
    }
  ]
}
```

### Webhook Health

Check webhook health status:

```bash
curl -X GET https://api.insanitycluster.com/v1/webhooks/wh_550e8400e29b41d4a716446655440000/health \
  -H "X-API-Key: ic_live_1234567890abcdef"
```

**Response:**
```json
{
  "webhook_id": "wh_550e8400e29b41d4a716446655440000",
  "status": "healthy",
  "success_rate": 0.98,
  "average_response_time_ms": 200,
  "last_success": "2025-11-16T11:00:00Z",
  "last_failure": "2025-11-15T10:00:00Z",
  "total_deliveries": 1000,
  "failed_deliveries": 20
}
```

## Troubleshooting

### Common Issues

**1. Signature Verification Fails**
- Ensure you're using the raw request body (not parsed JSON)
- Check that your secret matches the one used during registration
- Verify you're using HMAC SHA-256

**2. Timeouts**
- Respond within 5 seconds
- Process webhooks asynchronously
- Use a queue for long-running tasks

**3. Duplicate Events**
- Implement idempotency using event IDs
- Store processed event IDs in a database or cache

**4. Missing Events**
- Check webhook delivery logs
- Verify your endpoint is accessible
- Ensure your server is running

### Debug Mode

Enable debug logging for webhooks:

```bash
curl -X PUT https://api.insanitycluster.com/v1/webhooks/wh_550e8400e29b41d4a716446655440000 \
  -H "X-API-Key: ic_live_1234567890abcdef" \
  -H "Content-Type: application/json" \
  -d '{"debug": true}'
```

## Support

For webhook issues:
- Email: webhooks@insanitycluster.com
- Documentation: https://docs.insanitycluster.com/webhooks
- Status: https://status.insanitycluster.com
