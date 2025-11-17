#!/usr/bin/env python3
"""
Example Custom Agent Implementation

This example demonstrates how to create a custom agent for Insanity Cluster.
This agent specializes in data analysis tasks.

Usage:
    1. Copy this file to insanity_cluster/crust/data_analysis_agent.py
    2. Register the agent in insanity_cluster/crust/__init__.py
    3. Configure the agent in config.yaml
    4. Use the agent by creating tasks with data analysis requirements
"""

from insanity_cluster.crust.base_agent import BaseAgent
from insanity_cluster.common.models import (
    Subtask, Context, AgentResult, ModelStrategy,
    ResultStatus, ValidationResult
)
from typing import Any, Dict, List
import logging
import json
import re

logger = logging.getLogger(__name__)


class DataAnalysisAgent(BaseAgent):
    """
    Custom agent for data analysis tasks.
    
    Capabilities:
    - Statistical analysis
    - Data visualization recommendations
    - Trend identification
    - Anomaly detection
    - Report generation
    
    Model Preferences:
    - Primary: claude-sonnet-4.5 (excellent for analysis)
    - Fallback: gpt-5-mini (cost-effective)
    - Local: local:llama3:70b (for simple analysis)
    """
    
    def __init__(self, model_router, config):
        super().__init__(model_router, config)
        self.capabilities = [
            "statistical_analysis",
            "data_visualization",
            "trend_identification",
            "anomaly_detection",
            "report_generation"
        ]
    
    async def execute(self, subtask: Subtask, context: Context) -> AgentResult:
        """
        Execute a data analysis subtask.
        
        Args:
            subtask: The subtask to execute
            context: Conversation and task context
        
        Returns:
            AgentResult with analysis results
        """
        logger.info(f"DataAnalysisAgent executing subtask: {subtask.id}")
        
        try:
            # 1. Determine analysis type
            analysis_type = self._determine_analysis_type(subtask)
            logger.info(f"Analysis type: {analysis_type}")
            
            # 2. Select model strategy
            strategy = self.select_model_strategy(subtask)
            
            # 3. Prepare specialized prompt
            prompt = self._prepare_analysis_prompt(subtask, context, analysis_type)
            
            # 4. Call model via router
            response = await self.model_router.route_and_generate(
                prompt=prompt,
                strategy=strategy
            )
            
            # 5. Process and structure response
            output = self._process_analysis_response(response.content, analysis_type)
            
            # 6. Validate output
            validation = self.validate_output(output)
            
            if not validation.is_valid:
                logger.warning(f"Output validation failed: {validation.errors}")
                # Try to fix output
                output = self._fix_output(output, validation.errors)
                validation = self.validate_output(output)
            
            # 7. Return result
            return AgentResult(
                subtask_id=subtask.id,
                status=ResultStatus.SUCCESS if validation.is_valid else ResultStatus.FAILURE,
                output=output,
                cost=response.cost,
                latency_ms=response.latency_ms,
                model_used=response.model,
                validation_score=validation.score,
                error=None if validation.is_valid else f"Validation failed: {validation.errors}"
            )
        
        except Exception as e:
            logger.error(f"DataAnalysisAgent execution failed: {e}", exc_info=True)
            return AgentResult(
                subtask_id=subtask.id,
                status=ResultStatus.FAILURE,
                output=None,
                cost=0.0,
                latency_ms=0,
                model_used="",
                validation_score=0.0,
                error=str(e)
            )
    
    def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
        """
        Select optimal model strategy for data analysis.
        
        Args:
            subtask: The subtask to analyze
        
        Returns:
            ModelStrategy with routing preferences
        """
        # Estimate complexity based on task description
        complexity = self._estimate_complexity(subtask)
        
        # Data analysis typically requires good reasoning
        if complexity < 0.4:
            # Simple analysis - use fast model
            return ModelStrategy(
                routing_mode="SPEED_FIRST",
                max_cost=0.20,
                max_latency_ms=3000,
                required_capabilities=[],
                privacy_level="EXTERNAL_OK"
            )
        elif complexity < 0.7:
            # Moderate analysis - balance cost and quality
            return ModelStrategy(
                routing_mode="COST_OPTIMIZED",
                max_cost=0.50,
                max_latency_ms=5000,
                required_capabilities=[],
                privacy_level="EXTERNAL_OK"
            )
        else:
            # Complex analysis - prioritize quality
            return ModelStrategy(
                routing_mode="QUALITY_FIRST",
                max_cost=1.50,
                max_latency_ms=10000,
                required_capabilities=["long_context"],
                privacy_level="EXTERNAL_OK"
            )
    
    def validate_output(self, output: Any) -> ValidationResult:
        """
        Validate analysis output.
        
        Args:
            output: The output to validate
        
        Returns:
            ValidationResult with score and errors
        """
        errors = []
        score = 1.0
        
        # Check output is a dictionary
        if not isinstance(output, dict):
            errors.append("Output must be a dictionary")
            return ValidationResult(is_valid=False, score=0.0, errors=errors)
        
        # Check required fields
        required_fields = ["analysis_type", "findings", "summary"]
        for field in required_fields:
            if field not in output:
                errors.append(f"Missing required field: {field}")
                score *= 0.7
        
        # Check findings is a list
        if "findings" in output and not isinstance(output["findings"], list):
            errors.append("Findings must be a list")
            score *= 0.8
        
        # Check summary is not empty
        if "summary" in output and not output["summary"]:
            errors.append("Summary cannot be empty")
            score *= 0.9
        
        # Check for data quality indicators
        if "confidence" in output:
            confidence = output.get("confidence", 0)
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                errors.append("Confidence must be a number between 0 and 1")
                score *= 0.9
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            score=score,
            errors=errors
        )
    
    def _determine_analysis_type(self, subtask: Subtask) -> str:
        """Determine the type of analysis required"""
        description = subtask.description.lower()
        
        if any(word in description for word in ["trend", "pattern", "over time"]):
            return "trend_analysis"
        elif any(word in description for word in ["anomaly", "outlier", "unusual"]):
            return "anomaly_detection"
        elif any(word in description for word in ["statistic", "mean", "median", "correlation"]):
            return "statistical_analysis"
        elif any(word in description for word in ["visualize", "chart", "graph", "plot"]):
            return "visualization_recommendation"
        else:
            return "general_analysis"
    
    def _prepare_analysis_prompt(
        self,
        subtask: Subtask,
        context: Context,
        analysis_type: str
    ) -> str:
        """Prepare specialized prompt for data analysis"""
        
        base_prompt = f"""You are a data analysis expert. Perform the following analysis:

Task: {subtask.description}

Analysis Type: {analysis_type}

Context:
{context.get_relevant_context()}

Please provide a comprehensive analysis following this structure:

1. Analysis Type: Specify the type of analysis performed
2. Findings: List key findings as bullet points
3. Summary: Provide a concise summary of the analysis
4. Recommendations: Suggest actionable next steps
5. Confidence: Rate your confidence in the analysis (0.0 to 1.0)

Format your response as JSON with the following structure:
{{
    "analysis_type": "{analysis_type}",
    "findings": [
        "Finding 1",
        "Finding 2",
        ...
    ],
    "summary": "Brief summary of the analysis",
    "recommendations": [
        "Recommendation 1",
        "Recommendation 2",
        ...
    ],
    "confidence": 0.85,
    "metadata": {{
        "methods_used": ["method1", "method2"],
        "data_quality": "high/medium/low",
        "limitations": "Any limitations or caveats"
    }}
}}

Response:"""
        
        return base_prompt
    
    def _process_analysis_response(self, content: str, analysis_type: str) -> dict:
        """Process model response into structured analysis output"""
        try:
            # Try to parse as JSON
            output = json.loads(content)
            
            # Ensure analysis_type is set
            if "analysis_type" not in output:
                output["analysis_type"] = analysis_type
            
            return output
        
        except json.JSONDecodeError:
            # Fallback: extract structured data from text
            logger.warning("Failed to parse JSON, extracting structured data")
            
            output = {
                "analysis_type": analysis_type,
                "findings": self._extract_findings(content),
                "summary": self._extract_summary(content),
                "recommendations": self._extract_recommendations(content),
                "confidence": 0.7,  # Lower confidence for extracted data
                "metadata": {
                    "methods_used": [],
                    "data_quality": "unknown",
                    "limitations": "Response was not in expected JSON format"
                }
            }
            
            return output
    
    def _extract_findings(self, content: str) -> List[str]:
        """Extract findings from text"""
        findings = []
        
        # Look for bullet points or numbered lists
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('- ', '* ', '• ')) or re.match(r'^\d+\.', line):
                finding = re.sub(r'^[-*•\d.]\s*', '', line)
                if finding:
                    findings.append(finding)
        
        return findings if findings else ["Analysis completed"]
    
    def _extract_summary(self, content: str) -> str:
        """Extract summary from text"""
        # Look for summary section
        summary_match = re.search(r'summary:?\s*(.+?)(?:\n\n|\Z)', content, re.IGNORECASE | re.DOTALL)
        if summary_match:
            return summary_match.group(1).strip()
        
        # Fallback: use first paragraph
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        return paragraphs[0] if paragraphs else "Analysis completed"
    
    def _extract_recommendations(self, content: str) -> List[str]:
        """Extract recommendations from text"""
        recommendations = []
        
        # Look for recommendations section
        rec_match = re.search(r'recommendations?:?\s*(.+?)(?:\n\n|\Z)', content, re.IGNORECASE | re.DOTALL)
        if rec_match:
            rec_text = rec_match.group(1)
            lines = rec_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith(('- ', '* ', '• ')) or re.match(r'^\d+\.', line):
                    rec = re.sub(r'^[-*•\d.]\s*', '', line)
                    if rec:
                        recommendations.append(rec)
        
        return recommendations if recommendations else ["Review findings and take appropriate action"]
    
    def _fix_output(self, output: dict, errors: List[str]) -> dict:
        """Attempt to fix output based on validation errors"""
        fixed_output = output.copy()
        
        # Add missing required fields with defaults
        if "analysis_type" not in fixed_output:
            fixed_output["analysis_type"] = "general_analysis"
        
        if "findings" not in fixed_output:
            fixed_output["findings"] = ["Analysis completed"]
        elif not isinstance(fixed_output["findings"], list):
            fixed_output["findings"] = [str(fixed_output["findings"])]
        
        if "summary" not in fixed_output or not fixed_output["summary"]:
            fixed_output["summary"] = "Analysis completed successfully"
        
        if "recommendations" not in fixed_output:
            fixed_output["recommendations"] = []
        
        if "confidence" not in fixed_output:
            fixed_output["confidence"] = 0.7
        
        return fixed_output
    
    def _estimate_complexity(self, subtask: Subtask) -> float:
        """Estimate task complexity (0.0 - 1.0)"""
        complexity = 0.5  # Default for data analysis
        
        description = subtask.description.lower()
        
        # Increase complexity for certain keywords
        complex_keywords = [
            "correlation", "regression", "multivariate", "time series",
            "machine learning", "predictive", "forecast", "model"
        ]
        
        for keyword in complex_keywords:
            if keyword in description:
                complexity += 0.1
        
        # Adjust based on description length
        if len(subtask.description) > 500:
            complexity += 0.1
        
        # Adjust based on dependencies
        if len(subtask.dependencies) > 2:
            complexity += 0.1
        
        return min(complexity, 1.0)


# Example usage
if __name__ == "__main__":
    print("DataAnalysisAgent Example")
    print("=" * 50)
    print()
    print("This is an example custom agent implementation.")
    print("To use this agent:")
    print()
    print("1. Copy to: insanity_cluster/crust/data_analysis_agent.py")
    print("2. Register in: insanity_cluster/crust/__init__.py")
    print("   Add: 'data_analysis': DataAnalysisAgent")
    print()
    print("3. Configure in config.yaml:")
    print("""
agents:
  data_analysis:
    primary_model: claude-sonnet-4.5
    fallback_models:
      - gpt-5-mini
      - local:llama3:70b
    max_cost: 1.00
    fallback_to_paid: true
    """)
    print()
    print("4. Use the agent:")
    print('   insanity-cluster task create "Analyze sales trends for Q3 2025"')
