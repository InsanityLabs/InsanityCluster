"""
Common utility functions
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional


def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"ic_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_task_id() -> str:
    """Generate a unique task ID"""
    import uuid
    return str(uuid.uuid4())


def calculate_cost(tokens: int, price_per_million: float) -> float:
    """Calculate cost based on token count and pricing"""
    return (tokens / 1_000_000) * price_per_million


def format_duration(duration: timedelta) -> str:
    """Format a timedelta as a human-readable string"""
    total_seconds = int(duration.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def is_expired(timestamp: datetime, ttl_seconds: int) -> bool:
    """Check if a timestamp has expired based on TTL"""
    expiry = timestamp + timedelta(seconds=ttl_seconds)
    return datetime.now() > expiry


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to a maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
