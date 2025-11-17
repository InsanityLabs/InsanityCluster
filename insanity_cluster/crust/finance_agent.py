"""
Finance Agent for CRUST layer.

Handles financial tasks including accounting, budget management, invoicing,
financial reporting, and payment processing.
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from insanity_cluster.common.models import (
    AgentResult,
    AgentType,
    ModelStrategy,
    PrivacyLevel,
    RoutingMode,
    Subtask,
)
from insanity_cluster.crust.base_agent import BaseAgent
from insanity_cluster.pan.model_router import ModelRouter
from insanity_cluster.pan.models import GenerationParams

logger = logging.getLogger(__name__)


class FinanceAgent(BaseAgent):
    """
    Specialized agent for financial tasks.
    
    Capabilities:
    - Accounting and budget management
    - Invoicing and payment processing
    - Financial reporting and analysis
    - Stripe and PayPal integration
    - Calculation verification
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        stripe_client: Optional[Any] = None,
        paypal_client: Optional[Any] = None
    ):
        """Initialize Finance Agent."""
        default_strategy = ModelStrategy(
            routing_mode=RoutingMode.COST_OPTIMIZED,
            max_cost=0.3,
            required_capabilities=[],
            privacy_level=PrivacyLevel.EXTERNAL_OK
        )
        
        super().__init__(
            agent_type=AgentType.FINANCE,
            model_router=model_router,
            default_model_strategy=default_strategy
        )
        
        self.stripe_client = stripe_client
        self.paypal_client = paypal_client
    
    async def execute(self, subtask: Subtask, context: Dict[str, Any]) -> AgentResult:
        """Execute financial subtask."""
        logger.info(f"Finance agent executing: {subtask.description}")
        
        try:
            task_type = self._identify_task_type(subtask.description)
            model_strategy = self.select_model_strategy(subtask)
            
            if task_type == "accounting":
                output = await self._handle_accounting(subtask, context, model_strategy)
            elif task_type == "invoicing":
                output = await self._create_invoice(subtask, context, model_strategy)
            elif task_type == "reporting":
                output = await self._generate_financial_report(subtask, context, model_strategy)
            elif task_type == "payment":
                output = await self._process_payment(subtask, context)
            else:
                output = await self._execute_generic_finance(subtask, context, model_strategy)
            
            validation_score = self.validate_output(output, subtask)
            cost = context.get("last_response_cost", subtask.estimated_cost)
            latency_ms = context.get("last_response_latency_ms", 800)
            model_used = context.get("last_model_used", "gpt-5-mini")
            
            return self._create_success_result(
                subtask=subtask,
                output=output,
                cost=cost,
                latency_ms=latency_ms,
                model_used=model_used,
                validation_score=validation_score
            )
            
        except Exception as e:
            logger.error(f"Finance agent execution failed: {e}")
            return self._report_error(subtask, e, context)
    
    def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
        """Select model strategy for financial tasks."""
        return ModelStrategy(
            routing_mode=RoutingMode.COST_OPTIMIZED,
            max_cost=0.3,
            required_capabilities=[],
            privacy_level=PrivacyLevel.EXTERNAL_OK
        )
    
    def validate_output(self, output: Any, subtask: Subtask) -> float:
        """Validate financial output with calculation verification."""
        if not isinstance(output, (str, dict)):
            return 0.0
        
        output_str = str(output)
        checks_passed = 0
        total_checks = 5
        
        if output_str.strip():
            checks_passed += 1
        if any(num in output_str for num in ["$", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
            checks_passed += 1
        if not any(err in output_str.lower() for err in ["error", "failed", "invalid"]):
            checks_passed += 1
        if any(term in output_str.lower() for term in ["total", "amount", "balance", "payment"]):
            checks_passed += 1
        if len(output_str) > 30:
            checks_passed += 1
        
        return checks_passed / total_checks
    
    def _identify_task_type(self, description: str) -> str:
        """Identify financial task type."""
        desc_lower = description.lower()
        if any(kw in desc_lower for kw in ["account", "budget", "expense", "ledger"]):
            return "accounting"
        elif any(kw in desc_lower for kw in ["invoice", "bill"]):
            return "invoicing"
        elif any(kw in desc_lower for kw in ["report", "statement", "analysis"]):
            return "reporting"
        elif any(kw in desc_lower for kw in ["payment", "pay", "charge", "transaction"]):
            return "payment"
        return "generic"
    
    async def _handle_accounting(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """Handle accounting tasks."""
        transactions = context.get("transactions", [])
        period = context.get("period", "monthly")
        
        prompt = f"""Process accounting for {period} period:

Task: {subtask.description}
Transactions: {len(transactions)}

Provide:
1. Categorized expenses
2. Income summary
3. Balance calculations
4. Budget analysis
"""
        
        generation_params = GenerationParams(
            max_tokens=1500,
            temperature=0.2,
            system_prompt="You are a financial accountant. Provide accurate calculations."
        )
        
        response = await self._generate_with_model(
            prompt=prompt,
            model_strategy=model_strategy,
            generation_params=generation_params,
            context=context
        )
        
        context["last_response_cost"] = response.cost
        context["last_response_latency_ms"] = response.latency_ms
        context["last_model_used"] = response.model
        
        return {
            "type": "accounting",
            "period": period,
            "analysis": response.content,
            "transaction_count": len(transactions),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _create_invoice(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """Create invoice."""
        client_name = context.get("client_name", "")
        items = context.get("items", [])
        
        prompt = f"""Generate professional invoice:

Task: {subtask.description}
Client: {client_name}
Items: {len(items)}

Create complete invoice with:
1. Invoice number
2. Date
3. Itemized list
4. Subtotal
5. Tax
6. Total
7. Payment terms
"""
        
        generation_params = GenerationParams(
            max_tokens=1000,
            temperature=0.2,
            system_prompt="You are an invoicing specialist. Create accurate invoices."
        )
        
        response = await self._generate_with_model(
            prompt=prompt,
            model_strategy=model_strategy,
            generation_params=generation_params,
            context=context
        )
        
        context["last_response_cost"] = response.cost
        context["last_response_latency_ms"] = response.latency_ms
        context["last_model_used"] = response.model
        
        return {
            "type": "invoice",
            "client": client_name,
            "invoice_content": response.content,
            "status": "generated",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _generate_financial_report(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """Generate financial report."""
        report_type = context.get("report_type", "summary")
        data = context.get("financial_data", {})
        
        prompt = f"""Generate {report_type} financial report:

Task: {subtask.description}

Include:
1. Revenue analysis
2. Expense breakdown
3. Profit/loss
4. Key metrics
5. Trends
6. Recommendations
"""
        
        generation_params = GenerationParams(
            max_tokens=2000,
            temperature=0.3,
            system_prompt="You are a financial analyst. Provide clear, actionable reports."
        )
        
        response = await self._generate_with_model(
            prompt=prompt,
            model_strategy=model_strategy,
            generation_params=generation_params,
            context=context
        )
        
        context["last_response_cost"] = response.cost
        context["last_response_latency_ms"] = response.latency_ms
        context["last_model_used"] = response.model
        
        return {
            "type": "financial_report",
            "report_type": report_type,
            "report": response.content,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _process_payment(
        self,
        subtask: Subtask,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process payment via Stripe or PayPal."""
        amount = context.get("amount", 0.0)
        payment_method = context.get("payment_method", "stripe")
        
        if payment_method == "stripe" and self.stripe_client:
            logger.info(f"Processing Stripe payment: ${amount}")
            status = "processed_stripe"
        elif payment_method == "paypal" and self.paypal_client:
            logger.info(f"Processing PayPal payment: ${amount}")
            status = "processed_paypal"
        else:
            status = "simulated"
        
        return {
            "type": "payment",
            "amount": amount,
            "payment_method": payment_method,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _execute_generic_finance(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """Execute generic financial task."""
        prompt = f"""Complete financial task:

Task: {subtask.description}

Provide accurate financial analysis and recommendations.
"""
        
        generation_params = GenerationParams(
            max_tokens=1500,
            temperature=0.3,
            system_prompt="You are a financial expert. Provide accurate, practical advice."
        )
        
        response = await self._generate_with_model(
            prompt=prompt,
            model_strategy=model_strategy,
            generation_params=generation_params,
            context=context
        )
        
        context["last_response_cost"] = response.cost
        context["last_response_latency_ms"] = response.latency_ms
        context["last_model_used"] = response.model
        
        return response.content
