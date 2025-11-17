# Insanity Cluster Scripts

Utility scripts for managing the Insanity Cluster system.

## API Key Management

### Generate Admin API Key

Generate a new API key for the admin user:

```bash
python scripts/generate_admin_api_key.py
```

This will:
- Find the admin user in the database
- Generate a new secure API key
- Update the user's API key hash
- Display the API key (save it securely!)

### Default Development API Key

For initial development setup, a default API key is created during migrations:

```
API Key: ic_dev_admin_key_change_me_in_production
Email: admin@insanity-cluster.local
```

**⚠️ WARNING:** This default key should ONLY be used for local development. Always generate a new key for production environments!

## Usage Examples

### Test API with curl

```bash
# Health check
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/api/health

# List tasks
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/api/tasks

# Create a task
curl -X POST -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command": "analyze this data", "priority": 1}' \
  http://localhost:8000/api/tasks
```

### Test with Python

```python
import requests

API_KEY = "YOUR_API_KEY"
BASE_URL = "http://localhost:8000/api"

headers = {"X-API-Key": API_KEY}

# Health check
response = requests.get(f"{BASE_URL}/health", headers=headers)
print(response.json())

# Create task
task_data = {
    "command": "analyze this data",
    "priority": 1
}
response = requests.post(f"{BASE_URL}/tasks", json=task_data, headers=headers)
print(response.json())
```

## Other Scripts

- `init_database.py` - Initialize database schema
- `test_dashboard.py` - Test dashboard connectivity
- `generate_dashboard_token.py` - Generate JWT token for dashboard
