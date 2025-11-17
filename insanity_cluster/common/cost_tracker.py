"""
Cost tracking and limit enforcement system.

This module provides:
- Per-task cost tracking
- Daily and monthly cost aggregation
- Cost limit enforcement with warnings
- Cost estimation based on model pricing
- Cost reporting and analytics
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from insanity_cluster.table.models import Task, User
from insanity_cluster.table.redis_manager import RedisManager
from insanity_cluster.common.configuration import CostLimits


class CostTracker:
    """
    Cost tracking and limit enforcement.
    """
    
    # Model pricing (per million tokens)
    MODEL_PRICING = {
        # OpenAI GPT-5 series
        "gpt-5.1": {"input": 1.25, "output": 5.0},
        "gpt-5": {"input": 1.0, "output": 4.0},
        "gpt-5-mini": {"input": 0.15, "output": 0.6},
        "gpt-5-nano": {"input": 0.05, "output": 0.2},
        "gpt-5-codex": {"input": 1.5, "output": 6.0},
        
        # Anthropic Claude 4 series
        "claude-opus-4.1": {"input": 15.0, "output": 75.0},
        "claude-sonnet-4.5": {"input": 3.0, "output": 15.0},
        "claude-haiku-4.5": {"input": 1.0, "output": 5.0},
        
        # Local models (free)
        "llama3:70b": {"input": 0.0, "output": 0.0},
        "mistral": {"input": 0.0, "output": 0.0},
        "phi3": {"input": 0.0, "output": 0.0},
        "codellama": {"input": 0.0, "output": 0.0},
        "mixtral:8x7b": {"input": 0.0, "output": 0.0},
    }
    
    def __init__(self, db_session: Session, redis_manager: Optional[RedisManager] = None):
        """
        Initialize cost tracker.
        
        Args:
            db_session: SQLAlchemy database session
            redis_manager: Optional Redis manager for caching
        """
        self.db = db_session
        self.redis = redis_manager
    
    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Estimate cost for a model inference.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in dollars
        """
        # Normalize model name
        model_key = self._normalize_model_name(model)
        
        pricing = self.MODEL_PRICING.get(model_key)
        
        if not pricing:
            # Unknown model, assume moderate pricing
            pricing = {"input": 1.0, "output": 4.0}
        
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    def record_task_cost(
        self,
        task_id: uuid.UUID,
        cost: float,
        model_used: str,
        input_tokens: int,
        output_tokens: int,
    ):
        """
        Record cost for a task.
        
        Args:
            task_id: Task UUID
            cost: Actual cost incurred
            model_used: Model that was used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        # Update task cost in database
        task = self.db.query(Task).filter(Task.id == task_id).first()
        
        if task:
            task.cost = Decimal(str(cost))
            self.db.commit()
        
        # Update cached daily cost
        if self.redis:
            today = datetime.utcnow().date().isoformat()
            cache_key = f"cost:daily:{task.user_id}:{today}"
            
            # Increment daily cost
            self.redis.client.incrbyfloat(cache_key, cost)
            
            # Set expiration (keep for 7 days)
            self.redis.client.expire(cache_key, 7 * 24 * 60 * 60)
    
    def get_daily_cost(
        self,
        user_id: uuid.UUID,
        date: Optional[datetime] = None,
    ) -> float:
        """
        Get total cost for a user on a specific day.
        
        Args:
            user_id: User UUID
            date: Date to check (defaults to today)
            
        Returns:
            Total cost in dollars
        """
        if date is None:
            date = datetime.utcnow()
        
        date_str = date.date().isoformat()
        
        # Try cache first
        if self.redis:
            cache_key = f"cost:daily:{user_id}:{date_str}"
            cached_cost = self.redis.client.get(cache_key)
            
            if cached_cost is not None:
                return float(cached_cost)
        
        # Query database
        start_of_day = datetime.combine(date.date(), datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)
        
        result = self.db.query(func.sum(Task.cost)).filter(
            and_(
                Task.user_id == user_id,
                Task.created_at >= start_of_day,
                Task.created_at < end_of_day,
            )
        ).scalar()
        
        total_cost = float(result) if result else 0.0
        
        # Cache the result
        if self.redis:
            cache_key = f"cost:daily:{user_id}:{date_str}"
            self.redis.client.setex(cache_key, 24 * 60 * 60, total_cost)
        
        return total_cost
    
    def get_monthly_cost(
        self,
        user_id: uuid.UUID,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> float:
        """
        Get total cost for a user in a specific month.
        
        Args:
            user_id: User UUID
            year: Year (defaults to current year)
            month: Month (defaults to current month)
            
        Returns:
            Total cost in dollars
        """
        now = datetime.utcnow()
        year = year or now.year
        month = month or now.month
        
        # Calculate month boundaries
        start_of_month = datetime(year, month, 1)
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1)
        else:
            end_of_month = datetime(year, month + 1, 1)
        
        result = self.db.query(func.sum(Task.cost)).filter(
            and_(
                Task.user_id == user_id,
                Task.created_at >= start_of_month,
                Task.created_at < end_of_month,
            )
        ).scalar()
        
        return float(result) if result else 0.0
    
    def check_cost_limits(
        self,
        user_id: uuid.UUID,
        estimated_cost: float,
        cost_limits: CostLimits,
    ) -> Dict[str, Any]:
        """
        Check if a task would exceed cost limits.
        
        Args:
            user_id: User UUID
            estimated_cost: Estimated cost for the task
            cost_limits: Cost limits configuration
            
        Returns:
            Dictionary with:
                - allowed: bool - whether task is allowed
                - reason: str - reason if not allowed
                - warning: bool - whether to show warning
                - current_daily_cost: float
                - current_monthly_cost: float
        """
        result = {
            "allowed": True,
            "reason": None,
            "warning": False,
            "current_daily_cost": 0.0,
            "current_monthly_cost": 0.0,
        }
        
        # Check per-task limit
        if cost_limits.max_cost_per_task is not None:
            if estimated_cost > cost_limits.max_cost_per_task:
                if cost_limits.block_on_limit:
                    result["allowed"] = False
                    result["reason"] = f"Task cost (${estimated_cost:.4f}) exceeds per-task limit (${cost_limits.max_cost_per_task:.4f})"
                    return result
                else:
                    result["warning"] = True
        
        # Check daily limit
        if cost_limits.max_cost_per_day is not None:
            daily_cost = self.get_daily_cost(user_id)
            result["current_daily_cost"] = daily_cost
            
            projected_daily = daily_cost + estimated_cost
            
            if projected_daily > cost_limits.max_cost_per_day:
                if cost_limits.block_on_limit:
                    result["allowed"] = False
                    result["reason"] = f"Task would exceed daily limit (${cost_limits.max_cost_per_day:.2f}). Current: ${daily_cost:.2f}, Estimated: ${estimated_cost:.4f}"
                    return result
                else:
                    result["warning"] = True
            elif projected_daily > cost_limits.max_cost_per_day * (cost_limits.warning_threshold_percent / 100):
                result["warning"] = True
        
        # Check monthly limit
        if cost_limits.max_cost_per_month is not None:
            monthly_cost = self.get_monthly_cost(user_id)
            result["current_monthly_cost"] = monthly_cost
            
            projected_monthly = monthly_cost + estimated_cost
            
            if projected_monthly > cost_limits.max_cost_per_month:
                if cost_limits.block_on_limit:
                    result["allowed"] = False
                    result["reason"] = f"Task would exceed monthly limit (${cost_limits.max_cost_per_month:.2f}). Current: ${monthly_cost:.2f}, Estimated: ${estimated_cost:.4f}"
                    return result
                else:
                    result["warning"] = True
            elif projected_monthly > cost_limits.max_cost_per_month * (cost_limits.warning_threshold_percent / 100):
                result["warning"] = True
        
        return result
    
    def get_cost_report(
        self,
        user_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Generate cost report for a user.
        
        Args:
            user_id: User UUID
            start_date: Start date (defaults to 30 days ago)
            end_date: End date (defaults to now)
            
        Returns:
            Cost report dictionary
        """
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        # Get tasks in date range
        tasks = self.db.query(Task).filter(
            and_(
                Task.user_id == user_id,
                Task.created_at >= start_date,
                Task.created_at < end_date,
            )
        ).all()
        
        # Calculate statistics
        total_cost = sum(float(task.cost) for task in tasks)
        task_count = len(tasks)
        avg_cost_per_task = total_cost / task_count if task_count > 0 else 0.0
        
        # Group by model
        cost_by_model = {}
        for task in tasks:
            if task.result and isinstance(task.result, dict):
                model = task.result.get("model_used", "unknown")
                cost_by_model[model] = cost_by_model.get(model, 0.0) + float(task.cost)
        
        # Group by day
        cost_by_day = {}
        for task in tasks:
            day = task.created_at.date().isoformat()
            cost_by_day[day] = cost_by_day.get(day, 0.0) + float(task.cost)
        
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_cost": total_cost,
            "task_count": task_count,
            "avg_cost_per_task": avg_cost_per_task,
            "cost_by_model": cost_by_model,
            "cost_by_day": cost_by_day,
        }
    
    def get_cost_analytics(
        self,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Get cost analytics for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            Analytics dictionary with trends and insights
        """
        now = datetime.utcnow()
        
        # Get costs for different periods
        today_cost = self.get_daily_cost(user_id, now)
        yesterday_cost = self.get_daily_cost(user_id, now - timedelta(days=1))
        this_month_cost = self.get_monthly_cost(user_id)
        last_month_cost = self.get_monthly_cost(
            user_id,
            year=now.year if now.month > 1 else now.year - 1,
            month=now.month - 1 if now.month > 1 else 12,
        )
        
        # Calculate trends
        daily_trend = ((today_cost - yesterday_cost) / yesterday_cost * 100) if yesterday_cost > 0 else 0.0
        monthly_trend = ((this_month_cost - last_month_cost) / last_month_cost * 100) if last_month_cost > 0 else 0.0
        
        # Get top expensive tasks
        expensive_tasks = self.db.query(Task).filter(
            Task.user_id == user_id
        ).order_by(Task.cost.desc()).limit(5).all()
        
        return {
            "today_cost": today_cost,
            "yesterday_cost": yesterday_cost,
            "this_month_cost": this_month_cost,
            "last_month_cost": last_month_cost,
            "daily_trend_percent": daily_trend,
            "monthly_trend_percent": monthly_trend,
            "top_expensive_tasks": [
                {
                    "id": str(task.id),
                    "command": task.command[:100],
                    "cost": float(task.cost),
                    "created_at": task.created_at.isoformat(),
                }
                for task in expensive_tasks
            ],
        }
    
    def _normalize_model_name(self, model: str) -> str:
        """Normalize model name for pricing lookup."""
        # Remove provider prefixes
        model = model.lower()
        for prefix in ["openai/", "anthropic/", "openrouter/", "local:"]:
            if model.startswith(prefix):
                model = model[len(prefix):]
        
        return model


class CostLimitEnforcer:
    """
    Enforces cost limits before task execution.
    """
    
    def __init__(self, cost_tracker: CostTracker):
        """
        Initialize cost limit enforcer.
        
        Args:
            cost_tracker: CostTracker instance
        """
        self.cost_tracker = cost_tracker
    
    def check_and_enforce(
        self,
        user_id: uuid.UUID,
        estimated_cost: float,
        cost_limits: CostLimits,
    ) -> Dict[str, Any]:
        """
        Check cost limits and enforce if necessary.
        
        Args:
            user_id: User UUID
            estimated_cost: Estimated cost for the task
            cost_limits: Cost limits configuration
            
        Returns:
            Result dictionary with allowed status and messages
        """
        result = self.cost_tracker.check_cost_limits(
            user_id=user_id,
            estimated_cost=estimated_cost,
            cost_limits=cost_limits,
        )
        
        # Add warning messages
        if result["warning"]:
            warnings = []
            
            if cost_limits.max_cost_per_day:
                daily_percent = (result["current_daily_cost"] / cost_limits.max_cost_per_day) * 100
                if daily_percent >= cost_limits.warning_threshold_percent:
                    warnings.append(
                        f"Daily cost is at {daily_percent:.1f}% of limit "
                        f"(${result['current_daily_cost']:.2f} / ${cost_limits.max_cost_per_day:.2f})"
                    )
            
            if cost_limits.max_cost_per_month:
                monthly_percent = (result["current_monthly_cost"] / cost_limits.max_cost_per_month) * 100
                if monthly_percent >= cost_limits.warning_threshold_percent:
                    warnings.append(
                        f"Monthly cost is at {monthly_percent:.1f}% of limit "
                        f"(${result['current_monthly_cost']:.2f} / ${cost_limits.max_cost_per_month:.2f})"
                    )
            
            result["warnings"] = warnings
        
        return result
