"""
Configuration management using Pydantic settings
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # System Configuration
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # Database Configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "insanity_cluster"
    postgres_user: str = "insanity"
    postgres_password: str = "insanity_dev_password"
    
    @property
    def database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # Qdrant Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    qdrant_api_key: Optional[str] = None
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_secret_key: str = "your-secret-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # AI Model Providers
    openai_api_key: Optional[str] = None
    openai_org_id: Optional[str] = None
    openai_default_model: str = "gpt-5-mini"
    
    anthropic_api_key: Optional[str] = None
    anthropic_default_model: str = "claude-sonnet-4.5"
    
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    ollama_base_url: str = "http://localhost:11434"
    lmstudio_base_url: str = "http://localhost:1234"
    
    # Model Routing Configuration
    operating_mode: str = "mixed"
    default_routing_strategy: str = "cost_optimized"
    max_cost_per_task: float = 1.0
    max_cost_per_day: float = 50.0
    local_complexity_threshold: float = 0.5
    
    # Communication Integrations
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    
    sendgrid_api_key: Optional[str] = None
    sendgrid_from_email: Optional[str] = None
    
    # Monitoring
    prometheus_port: int = 9090
    grafana_port: int = 3000
    grafana_user: str = "admin"
    grafana_password: str = "admin"
    
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "insanity-cluster"
    
    # Security
    enable_tls: bool = False
    tls_cert_path: Optional[str] = None
    tls_key_path: Optional[str] = None
    
    # Data Retention
    context_retention_days: int = 30
    metrics_retention_days: int = 90
    log_retention_days: int = 30
    
    # Performance Tuning
    max_concurrent_tasks: int = 100
    task_timeout_seconds: int = 300
    model_timeout_seconds: int = 60
    max_retry_attempts: int = 3
    retry_backoff_factor: int = 2
    
    ws_heartbeat_interval: int = 30
    ws_max_connections: int = 1000
    
    cache_ttl_seconds: int = 3600
    command_cache_ttl_days: int = 7
    
    # Development Settings
    enable_cors: bool = True
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    enable_api_docs: bool = True
    enable_metrics_endpoint: bool = True


# Global settings instance
settings = Settings()
