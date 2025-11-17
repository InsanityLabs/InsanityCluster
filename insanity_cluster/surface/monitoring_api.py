"""
Monitoring API endpoints for retry handlers and circuit breakers.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from insanity_cluster.common.retry_handler import circuit_breaker_manager
from insanity_cluster.surface.auth import get_current_user


router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


class CircuitBreakerStateResponse(BaseModel):
    """Response with circuit breaker state."""
    name: str
    state: str
    failure_count: int
    success_count: int
    last_failure_time: str | None


class CircuitBreakerResetRequest(BaseModel):
    """Request to reset circuit breaker."""
    name: str


@router.get("/circuit-breakers", response_model=Dict[str, CircuitBreakerStateResponse])
async def get_circuit_breaker_states(
    current_user: Dict = Depends(get_current_user),
):
    """
    Get states of all circuit breakers.
    """
    states = circuit_breaker_manager.get_all_states()
    
    return {
        name: CircuitBreakerStateResponse(**state)
        for name, state in states.items()
    }


@router.get("/circuit-breakers/{name}", response_model=CircuitBreakerStateResponse)
async def get_circuit_breaker_state(
    name: str,
    current_user: Dict = Depends(get_current_user),
):
    """
    Get state of a specific circuit breaker.
    """
    breaker = circuit_breaker_manager.get(name)
    
    if not breaker:
        raise HTTPException(
            status_code=404,
            detail=f"Circuit breaker '{name}' not found",
        )
    
    state = breaker.get_state()
    return CircuitBreakerStateResponse(**state)


@router.post("/circuit-breakers/reset")
async def reset_circuit_breaker(
    request: CircuitBreakerResetRequest,
    current_user: Dict = Depends(get_current_user),
):
    """
    Reset a circuit breaker to closed state.
    """
    success = circuit_breaker_manager.reset(request.name)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Circuit breaker '{request.name}' not found",
        )
    
    return {"message": f"Circuit breaker '{request.name}' reset successfully"}


@router.post("/circuit-breakers/reset-all")
async def reset_all_circuit_breakers(
    current_user: Dict = Depends(get_current_user),
):
    """
    Reset all circuit breakers to closed state.
    """
    circuit_breaker_manager.reset_all()
    
    return {"message": "All circuit breakers reset successfully"}


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    states = circuit_breaker_manager.get_all_states()
    
    # Check if any circuit breakers are open
    open_breakers = [
        name for name, state in states.items()
        if state["state"] == "open"
    ]
    
    healthy = len(open_breakers) == 0
    
    return {
        "healthy": healthy,
        "open_circuit_breakers": open_breakers,
        "total_circuit_breakers": len(states),
    }
