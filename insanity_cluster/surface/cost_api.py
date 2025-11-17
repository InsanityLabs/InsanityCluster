"""
Cost tracking and reporting API endpoints.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from insanity_cluster.common.cost_tracker import CostTracker
from insanity_cluster.table.database import get_db
from insanity_cluster.table.redis_manager import RedisManager
from insanity_cluster.surface.auth import get_current_user


router = APIRouter(prefix="/api/v1/costs", tags=["costs"])


class CostEstimateRequest(BaseModel):
    """Request to estimate cost for a task."""
    model: str
    input_tokens: int
    output_tokens: int


class CostEstimateResponse(BaseModel):
    """Response with cost estimate."""
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float


class DailyCostResponse(BaseModel):
    """Response with daily cost."""
    date: str
    total_cost: float
    user_id: str


class MonthlyCostResponse(BaseModel):
    """Response with monthly cost."""
    year: int
    month: int
    total_cost: float
    user_id: str


class CostReportResponse(BaseModel):
    """Response with cost report."""
    start_date: str
    end_date: str
    total_cost: float
    task_count: int
    avg_cost_per_task: float
    cost_by_model: Dict[str, float]
    cost_by_day: Dict[str, float]


class CostAnalyticsResponse(BaseModel):
    """Response with cost analytics."""
    today_cost: float
    yesterday_cost: float
    this_month_cost: float
    last_month_cost: float
    daily_trend_percent: float
    monthly_trend_percent: float
    top_expensive_tasks: list


@router.post("/estimate", response_model=CostEstimateResponse)
async def estimate_cost(
    request: CostEstimateRequest,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Estimate cost for a model inference.
    """
    cost_tracker = CostTracker(db)
    
    estimated_cost = cost_tracker.estimate_cost(
        model=request.model,
        input_tokens=request.input_tokens,
        output_tokens=request.output_tokens,
    )
    
    return CostEstimateResponse(
        model=request.model,
        input_tokens=request.input_tokens,
        output_tokens=request.output_tokens,
        estimated_cost=estimated_cost,
    )


@router.get("/daily", response_model=DailyCostResponse)
async def get_daily_cost(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Get total cost for a specific day.
    """
    cost_tracker = CostTracker(db)
    user_id = UUID(current_user["user_id"])
    
    if date:
        date_obj = datetime.fromisoformat(date)
    else:
        date_obj = datetime.utcnow()
    
    total_cost = cost_tracker.get_daily_cost(user_id, date_obj)
    
    return DailyCostResponse(
        date=date_obj.date().isoformat(),
        total_cost=total_cost,
        user_id=str(user_id),
    )


@router.get("/monthly", response_model=MonthlyCostResponse)
async def get_monthly_cost(
    year: Optional[int] = Query(None, description="Year"),
    month: Optional[int] = Query(None, description="Month (1-12)"),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Get total cost for a specific month.
    """
    cost_tracker = CostTracker(db)
    user_id = UUID(current_user["user_id"])
    
    now = datetime.utcnow()
    year = year or now.year
    month = month or now.month
    
    total_cost = cost_tracker.get_monthly_cost(user_id, year, month)
    
    return MonthlyCostResponse(
        year=year,
        month=month,
        total_cost=total_cost,
        user_id=str(user_id),
    )


@router.get("/report", response_model=CostReportResponse)
async def get_cost_report(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Generate cost report for a date range.
    """
    cost_tracker = CostTracker(db)
    user_id = UUID(current_user["user_id"])
    
    start_date_obj = datetime.fromisoformat(start_date) if start_date else None
    end_date_obj = datetime.fromisoformat(end_date) if end_date else None
    
    report = cost_tracker.get_cost_report(user_id, start_date_obj, end_date_obj)
    
    return CostReportResponse(**report)


@router.get("/analytics", response_model=CostAnalyticsResponse)
async def get_cost_analytics(
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """
    Get cost analytics with trends and insights.
    """
    cost_tracker = CostTracker(db)
    user_id = UUID(current_user["user_id"])
    
    analytics = cost_tracker.get_cost_analytics(user_id)
    
    return CostAnalyticsResponse(**analytics)
