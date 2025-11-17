#!/usr/bin/env python3
"""
Generate a JWT token for the dashboard to use
"""
import jwt
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from insanity_cluster.common.config import settings

def generate_dashboard_token():
    """Generate a JWT token for dashboard authentication"""
    load_dotenv()
    
    # Token payload
    payload = {
        "sub": "dashboard_user",  # Subject (user ID)
        "name": "Dashboard",
        "role": "user",
        "iat": datetime.utcnow(),  # Issued at
        "exp": datetime.utcnow() + timedelta(days=365)  # Expires in 1 year
    }
    
    # Generate token
    token = jwt.encode(
        payload,
        settings.api_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    print("=" * 80)
    print("🔑 Dashboard JWT Token Generated")
    print("=" * 80)
    print()
    print("Token:")
    print(token)
    print()
    print("=" * 80)
    print("📋 Configuration Instructions:")
    print("=" * 80)
    print()
    print("1. Update dashboard/.env:")
    print(f"   VITE_API_TOKEN={token}")
    print()
    print("2. Or update dashboard WebSocket connection to use this token")
    print()
    print("Token Details:")
    print(f"  - User: dashboard_user")
    print(f"  - Role: user")
    print(f"  - Expires: {payload['exp'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  - Secret Key: {settings.api_secret_key[:20]}...")
    print()
    print("=" * 80)

if __name__ == "__main__":
    generate_dashboard_token()
