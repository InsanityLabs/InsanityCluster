# Authentication and Authorization Guide

## Overview

The Insanity Cluster API uses two authentication methods:
- **API Keys**: For server-to-server communication and long-lived access
- **JWT Tokens**: For user sessions and short-lived access

## API Key Authentication

### Generating an API Key

API keys can be generated through the web dashboard or CLI:

**Via Dashboard:**
1. Navigate to Settings → API Keys
2. Click "Generate New API Key"
3. Provide a name and select permissions
4. Copy the key (it will only be shown once)

**Via CLI:**
```bash
insanity-cluster auth create-key --name "My Application" --role user
```

### Using API Keys

Include the API key in the `X-API-Key` header:

```bash
curl -X POST https://api.insanitycluster.com/v1/tasks \
  -H "X-API-Key: ic_live_1234567890abcdef" \
  -H "Content-Type: application/json" \
  -d '{"command": "Write a Python function"}'
```

**Python Example:**
```python
import requests

headers = {
    "X-API-Key": "ic_live_1234567890abcdef",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://api.insanitycluster.com/v1/tasks",
    headers=headers,
    json={"command": "Write a Python function"}
)
```

**JavaScript Example:**
```javascript
const response = await fetch('https://api.insanitycluster.com/v1/tasks', {
  method: 'POST',
  headers: {
    'X-API-Key': 'ic_live_1234567890abcdef',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    command: 'Write a Python function'
  })
});
```

### API Key Format

API keys follow this format:
```
ic_{environment}_{random_string}
```

- `ic_test_...`: Test environment keys
- `ic_live_...`: Production environment keys

### API Key Security

**Best Practices:**
- Never commit API keys to version control
- Use environment variables to store keys
- Rotate keys every 90 days
- Use separate keys for different applications
- Revoke keys immediately if compromised

**Environment Variables:**
```bash
# .env file
INSANITY_CLUSTER_API_KEY=ic_live_1234567890abcdef
```

```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('INSANITY_CLUSTER_API_KEY')
```

## JWT Token Authentication

### Generating a JWT Token

Exchange your API key for a JWT token:

```bash
curl -X POST https://api.insanitycluster.com/v1/auth/token \
  -H "X-API-Key: ic_live_1234567890abcdef"
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-11-16T18:30:00Z"
}
```

### Using JWT Tokens

Include the token in the `Authorization` header:

```bash
curl -X GET https://api.insanitycluster.com/v1/tasks/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Python Example:**
```python
import requests

headers = {
    "Authorization": f"Bearer {jwt_token}",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://api.insanitycluster.com/v1/tasks/550e8400-e29b-41d4-a716-446655440000",
    headers=headers
)
```

### Token Expiration

JWT tokens expire after 24 hours. Implement token refresh logic:

```python
import requests
from datetime import datetime, timezone

class InsanityClusterClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.token = None
        self.token_expires_at = None
    
    def get_token(self):
        """Get a valid JWT token, refreshing if necessary"""
        if self.token and self.token_expires_at:
            # Check if token expires in next 5 minutes
            if datetime.now(timezone.utc) < self.token_expires_at - timedelta(minutes=5):
                return self.token
        
        # Request new token
        response = requests.post(
            "https://api.insanitycluster.com/v1/auth/token",
            headers={"X-API-Key": self.api_key}
        )
        data = response.json()
        
        self.token = data['token']
        self.token_expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        
        return self.token
    
    def make_request(self, method, endpoint, **kwargs):
        """Make an authenticated request"""
        token = self.get_token()
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {token}'
        kwargs['headers'] = headers
        
        return requests.request(method, f"https://api.insanitycluster.com/v1{endpoint}", **kwargs)

# Usage
client = InsanityClusterClient('ic_live_1234567890abcdef')
response = client.make_request('POST', '/tasks', json={'command': 'Write a function'})
```

## Role-Based Access Control (RBAC)

### Roles

The system supports three roles:

#### 1. Admin
- Full access to all resources
- Can manage users and API keys
- Can modify system configuration
- Can view all tasks and metrics

#### 2. User (Default)
- Can create and manage own tasks
- Can view own metrics and costs
- Can configure own operating mode
- Cannot access other users' data

#### 3. Readonly
- Can view own tasks and metrics
- Cannot create or modify tasks
- Cannot change configuration
- Useful for monitoring and reporting

### Checking Permissions

The API returns `403 Forbidden` if you lack permissions:

```json
{
  "error": "Insufficient permissions",
  "code": "FORBIDDEN",
  "details": {
    "required_role": "admin",
    "current_role": "user"
  }
}
```

### Role Assignment

Roles are assigned when creating API keys:

```bash
# Create admin key
insanity-cluster auth create-key --name "Admin Key" --role admin

# Create user key (default)
insanity-cluster auth create-key --name "User Key" --role user

# Create readonly key
insanity-cluster auth create-key --name "Monitoring Key" --role readonly
```

## OAuth 2.0 Integration

For third-party applications, use OAuth 2.0:

### Authorization Code Flow

**Step 1: Redirect user to authorization URL**
```
https://api.insanitycluster.com/oauth/authorize?
  client_id=YOUR_CLIENT_ID&
  redirect_uri=https://yourapp.com/callback&
  response_type=code&
  scope=tasks:read tasks:write config:read
```

**Step 2: User authorizes your application**

**Step 3: Exchange authorization code for access token**
```bash
curl -X POST https://api.insanitycluster.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=AUTH_CODE" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "redirect_uri=https://yourapp.com/callback"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "refresh_token_here",
  "scope": "tasks:read tasks:write config:read"
}
```

### Scopes

Available OAuth scopes:

- `tasks:read`: Read task status and results
- `tasks:write`: Create and cancel tasks
- `config:read`: Read configuration
- `config:write`: Modify configuration
- `metrics:read`: Read metrics and costs
- `webhooks:write`: Manage webhooks

### Refresh Tokens

Use refresh tokens to get new access tokens:

```bash
curl -X POST https://api.insanitycluster.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=REFRESH_TOKEN" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET"
```

## Security Best Practices

### 1. Secure Storage

**Never hardcode credentials:**
```python
# ❌ Bad
api_key = "ic_live_1234567890abcdef"

# ✅ Good
import os
api_key = os.getenv('INSANITY_CLUSTER_API_KEY')
```

### 2. Use HTTPS

Always use HTTPS in production:
```python
# ❌ Bad
base_url = "http://api.insanitycluster.com"

# ✅ Good
base_url = "https://api.insanitycluster.com"
```

### 3. Rotate Keys Regularly

Set up automatic key rotation:
```bash
# Rotate keys every 90 days
insanity-cluster auth rotate-key --key-id key_123 --schedule 90d
```

### 4. Use Least Privilege

Create keys with minimal required permissions:
```bash
# For monitoring only
insanity-cluster auth create-key --name "Monitor" --role readonly

# For specific application
insanity-cluster auth create-key --name "App" --role user --scopes tasks:write
```

### 5. Monitor API Usage

Track API key usage:
```bash
# View API key usage
insanity-cluster auth usage --key-id key_123

# Set up alerts for unusual activity
insanity-cluster auth alert --key-id key_123 --threshold 1000
```

### 6. Revoke Compromised Keys

Immediately revoke compromised keys:
```bash
insanity-cluster auth revoke-key --key-id key_123
```

## Rate Limiting

### Rate Limit Headers

All API responses include rate limit information:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1700140800
```

### Rate Limit Tiers

- **Free Tier**: 100 requests/hour
- **Paid Tier**: 1000 requests/hour
- **Enterprise**: Custom limits

### Handling Rate Limits

```python
import time
import requests

def make_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            # Rate limit exceeded
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            wait_time = max(reset_time - time.time(), 0) + 1
            
            print(f"Rate limit exceeded. Waiting {wait_time}s...")
            time.sleep(wait_time)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

## Error Responses

### Authentication Errors

**401 Unauthorized - Missing or invalid credentials:**
```json
{
  "error": "Authentication required",
  "code": "UNAUTHORIZED",
  "details": {
    "message": "No API key or token provided"
  }
}
```

**403 Forbidden - Insufficient permissions:**
```json
{
  "error": "Insufficient permissions",
  "code": "FORBIDDEN",
  "details": {
    "required_role": "admin",
    "current_role": "user"
  }
}
```

**429 Too Many Requests - Rate limit exceeded:**
```json
{
  "error": "Rate limit exceeded",
  "code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "limit": 1000,
    "reset_at": "2025-11-16T11:00:00Z"
  }
}
```

## Testing Authentication

### Test API Key

Use test keys for development:

```bash
# Create test key
insanity-cluster auth create-key --name "Test" --environment test

# Test key format: ic_test_...
```

### Verify Authentication

Test your authentication setup:

```bash
curl -X GET https://api.insanitycluster.com/v1/auth/verify \
  -H "X-API-Key: ic_live_1234567890abcdef"
```

**Response:**
```json
{
  "authenticated": true,
  "user_id": "user_123",
  "role": "user",
  "key_id": "key_456",
  "expires_at": null
}
```

## Support

For authentication issues:
- Email: security@insanitycluster.com
- Documentation: https://docs.insanitycluster.com/auth
- Status: https://status.insanitycluster.com
