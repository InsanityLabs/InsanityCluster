"""
Configuration API endpoints for managing system configurations.

This module provides REST API endpoints for:
- Mode selection and configuration management
- Agent-specific model selection
- Task-type model mapping
- Model provider configuration
- Routing strategy configuration
- Configuration validation and conflict detection
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from insanity_cluster.common.configuration import (
    ModeConfiguration,
    OperatingMode,
    RoutingStrategy,
    AgentType,
    AgentModelConfig,
    TaskModelConfig,
    ModelProviderConfig,
    CostLimits,
    RetryPolicy,
    TimeoutConfig,
    CircuitBreakerConfig,
    get_default_config,
)
from insanity_cluster.common.config_manager import ConfigurationManager, config_cache
from insanity_cluster.table.database import get_db
from insanity_cluster.surface.auth import get_current_user


router = APIRouter(prefix="/api/v1/config", tags=["configuration"])


# Pydantic models for API requests/responses
class ModeSelectionRequest(BaseModel):
    """Request to change operating mode."""
    mode: OperatingMode
    use_default_config: bool = True


class ModeSelectionResponse(BaseModel):
    """Response for mode selection."""
    config_id: str
    mode: OperatingMode
    message: str


class AgentModelConfigRequest(BaseModel):
    """Request to configure agent-specific models."""
    agent_type: AgentType
    preferred_models: List[str]
    fallback_to_paid: bool = True
    max_cost: Optional[float] = None


class TaskModelConfigRequest(BaseModel):
    """Request to configure task-type models."""
    task_type: str
    model_override: Optional[str] = None
    strategy_override: Optional[RoutingStrategy] = None
    allow_local: bool = True
    allow_paid: bool = True
    max_cost: Optional[float] = None


class ModelProviderConfigRequest(BaseModel):
    """Request to configure model provider."""
    provider_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = True
    enabled_models: List[str] = Field(default_factory=list)
    rate_limit_rpm: Optional[int] = None


class ConfigurationCreateRequest(BaseModel):
    """Request to create a new configuration."""
    name: str
    description: Optional[str] = None
    mode: OperatingMode
    default_strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMIZED
    max_cost_per_task: Optional[float] = None
    max_cost_per_day: Optional[float] = None
    local_complexity_threshold: float = 0.5
    set_active: bool = False


class ConfigurationUpdateRequest(BaseModel):
    """Request to update configuration."""
    name: Optional[str] = None
    description: Optional[str] = None
    default_strategy: Optional[RoutingStrategy] = None
    max_cost_per_task: Optional[float] = None
    max_cost_per_day: Optional[float] = None
    local_complexity_threshold: Optional[float] = None
    change_description: Optional[str] = None


class ConfigurationResponse(BaseModel):
    """Response containing configuration details."""
    id: str
    name: str
    description: Optional[str]
    mode: str
    version: int
    is_active: bool
    is_default: bool
    created_at: str
    updated_at: str


class ConfigurationDetailResponse(BaseModel):
    """Detailed configuration response."""
    id: str
    name: str
    description: Optional[str]
    config_data: Dict[str, Any]
    version: int
    is_active: bool
    validation_errors: List[str]


class ValidationResponse(BaseModel):
    """Configuration validation response."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


@router.get("/modes", response_model=List[Dict[str, Any]])
async def list_operating_modes():
    """
    List all available operating modes with descriptions.
    """
    return [
        {
            "mode": mode.value,
            "name": get_default_config(mode).name,
            "description": get_default_config(mode).description,
            "cost_level": _get_cost_level(mode),
            "privacy_level": _get_privacy_level(mode),
        }
        for mode in OperatingMode
    ]


@router.post("/modes/select", response_model=ModeSelectionResponse)
async def select_operating_mode(
    request: ModeSelectionRequest,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Select an operating mode and optionally use default configuration.
    """
    config_manager = ConfigurationManager(db)
    user_id = UUID(current_user["user_id"])
    
    if request.use_default_config:
        # Get default config for the mode
        default_config = get_default_config(request.mode)
        
        # Create configuration
        config_id = config_manager.create_configuration(
            config=default_config,
            user_id=user_id,
            set_active=True,
        )
        
        # Invalidate cache
        config_cache.invalidate(user_id)
        
        return ModeSelectionResponse(
            config_id=str(config_id),
            mode=request.mode,
            message=f"Switched to {request.mode.value} mode with default configuration",
        )
    else:
        # Just switch mode without changing other settings
        active_config = config_manager.get_active_configuration(user_id)
        
        if active_config:
            active_config.mode = request.mode
            config_manager.update_configuration(
                config_id=UUID(active_config.id) if hasattr(active_config, 'id') else None,
                config=active_config,
                user_id=user_id,
                change_description=f"Changed mode to {request.mode.value}",
            )
        else:
            # No active config, create default
            default_config = get_default_config(request.mode)
            config_id = config_manager.create_configuration(
                config=default_config,
                user_id=user_id,
                set_active=True,
            )
        
        config_cache.invalidate(user_id)
        
        return ModeSelectionResponse(
            config_id=str(config_id) if 'config_id' in locals() else "unknown",
            mode=request.mode,
            message=f"Switched to {request.mode.value} mode",
        )


@router.get("/configurations", response_model=List[ConfigurationResponse])
async def list_configurations(
    include_system: bool = True,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    List all configurations for the current user.
    """
    config_manager = ConfigurationManager(db)
    user_id = UUID(current_user["user_id"])
    
    configs = config_manager.list_configurations(
        user_id=user_id,
        include_system=include_system,
    )
    
    return [ConfigurationResponse(**config) for config in configs]


@router.get("/configurations/active", response_model=ConfigurationDetailResponse)
async def get_active_configuration(
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Get the active configuration for the current user.
    """
    config_manager = ConfigurationManager(db)
    user_id = UUID(current_user["user_id"])
    
    # Try cache first
    config = config_cache.get(user_id)
    
    if not config:
        config = config_manager.get_active_configuration(user_id)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active configuration found",
            )
        
        config_cache.set(config, user_id)
    
    validation_errors = config.validate()
    
    return ConfigurationDetailResponse(
        id=str(config.id) if hasattr(config, 'id') else "unknown",
        name=config.name or "Unnamed Configuration",
        description=config.description,
        config_data=config.to_dict(),
        version=config.version,
        is_active=True,
        validation_errors=validation_errors,
    )


@router.get("/configurations/{config_id}", response_model=ConfigurationDetailResponse)
async def get_configuration(
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Get a specific configuration by ID.
    """
    config_manager = ConfigurationManager(db)
    
    config = config_manager.get_configuration(config_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )
    
    validation_errors = config.validate()
    
    return ConfigurationDetailResponse(
        id=str(config_id),
        name=config.name or "Unnamed Configuration",
        description=config.description,
        config_data=config.to_dict(),
        version=config.version,
        is_active=False,  # Would need to check this from DB
        validation_errors=validation_errors,
    )


@router.post("/configurations", response_model=ConfigurationResponse)
async def create_configuration(
    request: ConfigurationCreateRequest,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Create a new configuration.
    """
    config_manager = ConfigurationManager(db)
    user_id = UUID(current_user["user_id"])
    
    # Create configuration from request
    config = ModeConfiguration(
        mode=request.mode,
        name=request.name,
        description=request.description,
        default_strategy=request.default_strategy,
        cost_limits=CostLimits(
            max_cost_per_task=request.max_cost_per_task,
            max_cost_per_day=request.max_cost_per_day,
        ),
        local_complexity_threshold=request.local_complexity_threshold,
    )
    
    config_id = config_manager.create_configuration(
        config=config,
        user_id=user_id,
        set_active=request.set_active,
    )
    
    if request.set_active:
        config_cache.invalidate(user_id)
    
    # Get the created config to return
    configs = config_manager.list_configurations(user_id=user_id)
    created_config = next((c for c in configs if c["id"] == str(config_id)), None)
    
    if not created_config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve created configuration",
        )
    
    return ConfigurationResponse(**created_config)


@router.put("/configurations/{config_id}/activate")
async def activate_configuration(
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Set a configuration as active.
    """
    config_manager = ConfigurationManager(db)
    user_id = UUID(current_user["user_id"])
    
    success = config_manager.set_active_configuration(config_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )
    
    config_cache.invalidate(user_id)
    
    return {"message": "Configuration activated successfully"}


@router.delete("/configurations/{config_id}")
async def delete_configuration(
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Delete a configuration.
    """
    config_manager = ConfigurationManager(db)
    user_id = UUID(current_user["user_id"])
    
    success = config_manager.delete_configuration(config_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )
    
    config_cache.invalidate(user_id)
    
    return {"message": "Configuration deleted successfully"}


@router.post("/configurations/{config_id}/agents")
async def configure_agent_models(
    config_id: UUID,
    request: AgentModelConfigRequest,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Configure agent-specific model preferences.
    """
    config_manager = ConfigurationManager(db)
    user_id = UUID(current_user["user_id"])
    
    config = config_manager.get_configuration(config_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )
    
    # Update agent configuration
    agent_config = AgentModelConfig(
        preferred_models=request.preferred_models,
        fallback_to_paid=request.fallback_to_paid,
        max_cost=request.max_cost,
    )
    
    config.agent_overrides[request.agent_type] = agent_config
    
    config_manager.update_configuration(
        config_id=config_id,
        config=config,
        user_id=user_id,
        change_description=f"Updated {request.agent_type.value} agent configuration",
    )
    
    config_cache.invalidate(user_id)
    
    return {"message": f"Agent {request.agent_type.value} configuration updated"}


@router.post("/configurations/{config_id}/tasks")
async def configure_task_models(
    config_id: UUID,
    request: TaskModelConfigRequest,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Configure task-type specific model preferences.
    """
    config_manager = ConfigurationManager(db)
    user_id = UUID(current_user["user_id"])
    
    config = config_manager.get_configuration(config_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )
    
    # Update task configuration
    task_config = TaskModelConfig(
        model_override=request.model_override,
        strategy_override=request.strategy_override,
        allow_local=request.allow_local,
        allow_paid=request.allow_paid,
        max_cost=request.max_cost,
    )
    
    config.task_type_overrides[request.task_type] = task_config
    
    config_manager.update_configuration(
        config_id=config_id,
        config=config,
        user_id=user_id,
        change_description=f"Updated task type '{request.task_type}' configuration",
    )
    
    config_cache.invalidate(user_id)
    
    return {"message": f"Task type '{request.task_type}' configuration updated"}


@router.post("/configurations/{config_id}/providers")
async def configure_model_provider(
    config_id: UUID,
    request: ModelProviderConfigRequest,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Configure model provider settings.
    """
    config_manager = ConfigurationManager(db)
    user_id = UUID(current_user["user_id"])
    
    config = config_manager.get_configuration(config_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )
    
    # Update provider configuration
    provider_config = ModelProviderConfig(
        provider_name=request.provider_name,
        api_key=request.api_key,
        base_url=request.base_url,
        enabled=request.enabled,
        enabled_models=request.enabled_models,
        rate_limit_rpm=request.rate_limit_rpm,
    )
    
    config.provider_configs[request.provider_name] = provider_config
    
    config_manager.update_configuration(
        config_id=config_id,
        config=config,
        user_id=user_id,
        change_description=f"Updated provider '{request.provider_name}' configuration",
    )
    
    config_cache.invalidate(user_id)
    
    return {"message": f"Provider '{request.provider_name}' configuration updated"}


@router.post("/configurations/{config_id}/validate", response_model=ValidationResponse)
async def validate_configuration(
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Validate a configuration and return errors/warnings.
    """
    config_manager = ConfigurationManager(db)
    
    config = config_manager.get_configuration(config_id)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )
    
    errors = config.validate()
    warnings = _get_configuration_warnings(config)
    
    return ValidationResponse(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


@router.get("/configurations/{config_id}/export")
async def export_configuration(
    config_id: UUID,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Export configuration as JSON or YAML.
    """
    config_manager = ConfigurationManager(db)
    
    exported = config_manager.export_configuration(config_id, format)
    
    if not exported:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuration not found",
        )
    
    return {"format": format, "data": exported}


@router.post("/configurations/import")
async def import_configuration(
    data: str,
    format: str = "json",
    set_active: bool = False,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Import configuration from JSON or YAML.
    """
    config_manager = ConfigurationManager(db)
    user_id = UUID(current_user["user_id"])
    
    try:
        config_id = config_manager.import_configuration(
            data=data,
            format=format,
            user_id=user_id,
            set_active=set_active,
        )
        
        if set_active:
            config_cache.invalidate(user_id)
        
        return {"config_id": str(config_id), "message": "Configuration imported successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to import configuration: {str(e)}",
        )


@router.post("/configurations/defaults")
async def create_default_configurations(
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Create default configurations for all operating modes.
    """
    config_manager = ConfigurationManager(db)
    user_id = UUID(current_user["user_id"])
    
    config_manager.create_default_configurations(user_id)
    
    return {"message": "Default configurations created successfully"}


# Helper functions
def _get_cost_level(mode: OperatingMode) -> int:
    """Get cost level (1-5) for a mode."""
    cost_levels = {
        OperatingMode.LOCAL: 1,
        OperatingMode.OPENROUTER_FREE: 1,
        OperatingMode.MIXED: 3,
        OperatingMode.OPENROUTER_PAID: 4,
        OperatingMode.WEB: 5,
    }
    return cost_levels.get(mode, 3)


def _get_privacy_level(mode: OperatingMode) -> str:
    """Get privacy level description for a mode."""
    privacy_levels = {
        OperatingMode.LOCAL: "Maximum (Local only)",
        OperatingMode.OPENROUTER_FREE: "Medium (External APIs)",
        OperatingMode.MIXED: "Medium (Hybrid)",
        OperatingMode.OPENROUTER_PAID: "Low (External APIs)",
        OperatingMode.WEB: "Low (External APIs)",
    }
    return privacy_levels.get(mode, "Unknown")


def _get_configuration_warnings(config: ModeConfiguration) -> List[str]:
    """Get configuration warnings (non-critical issues)."""
    warnings = []
    
    # Check for high cost limits
    if config.cost_limits.max_cost_per_day and config.cost_limits.max_cost_per_day > 100:
        warnings.append("Daily cost limit is set very high (>$100)")
    
    # Check for missing agent configurations
    if not config.agent_overrides:
        warnings.append("No agent-specific configurations set, using defaults")
    
    # Check for mixed mode without complexity threshold
    if config.mode == OperatingMode.MIXED and config.local_complexity_threshold == 0:
        warnings.append("Mixed mode with 0 complexity threshold will always use paid models")
    
    return warnings
