"""
Research Agent for CRUST layer.

Handles research tasks including web search, data gathering, synthesis,
report generation, trend analysis, and competitive analysis.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

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


class ResearchAgent(BaseAgent):
    """
    Specialized agent for research and analysis tasks.
    
    Capabilities:
    - Web search and data gathering
    - Multi-source data synthesis
    - Structured report generation with citations
    - Trend analysis and insights
    - Competitive analysis
    - Source credibility checking
    
    Optimized for comprehensive, accurate research.
    """
    
    def __init__(
        self,
        model_router: ModelRouter,
        search_api_client: Optional[Any] = None
    ):
        """
        Initialize Research Agent.
        
        Args:
            model_router: Model router for inference
            search_api_client: Web search API client (optional)
        """
        # Default to task-specific for research
        default_strategy = ModelStrategy(
            routing_mode=RoutingMode.TASK_SPECIFIC,
            max_cost=0.5,
            required_capabilities=["long_context"],
            privacy_level=PrivacyLevel.EXTERNAL_OK
        )
        
        super().__init__(
            agent_type=AgentType.RESEARCH,
            model_router=model_router,
            default_model_strategy=default_strategy
        )
        
        # External service clients
        self.search_api_client = search_api_client
        
        # Research quality thresholds
        self.min_sources = 3
        self.credibility_threshold = 0.7
    
    async def execute(self, subtask: Subtask, context: Dict[str, Any]) -> AgentResult:
        """
        Execute research subtask.
        
        Args:
            subtask: Subtask to execute
            context: Execution context
            
        Returns:
            AgentResult with research output
        """
        logger.info(f"Research agent executing: {subtask.description}")
        
        try:
            # Determine task type
            task_type = self._identify_task_type(subtask.description)
            
            # Select model strategy
            model_strategy = self.select_model_strategy(subtask)
            
            # Execute based on task type
            if task_type == "web_search":
                output = await self._perform_web_search(subtask, context, model_strategy)
            elif task_type == "data_synthesis":
                output = await self._synthesize_data(subtask, context, model_strategy)
            elif task_type == "report_generation":
                output = await self._generate_report(subtask, context, model_strategy)
            elif task_type == "trend_analysis":
                output = await self._analyze_trends(subtask, context, model_strategy)
            elif task_type == "competitive_analysis":
                output = await self._competitive_analysis(subtask, context, model_strategy)
            else:
                output = await self._execute_generic_research(subtask, context, model_strategy)
            
            # Validate output
            validation_score = self.validate_output(output, subtask)
            
            # Get metrics
            cost = context.get("last_response_cost", subtask.estimated_cost)
            latency_ms = context.get("last_response_latency_ms", 1500)
            model_used = context.get("last_model_used", "claude-sonnet-4.5")
            
            return self._create_success_result(
                subtask=subtask,
                output=output,
                cost=cost,
                latency_ms=latency_ms,
                model_used=model_used,
                validation_score=validation_score
            )
            
        except Exception as e:
            logger.error(f"Research agent execution failed: {e}")
            return self._report_error(subtask, e, context)
    
    def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
        """
        Select model strategy for research tasks.
        
        Args:
            subtask: Subtask to analyze
            
        Returns:
            ModelStrategy optimized for research
        """
        description_lower = subtask.description.lower()
        
        # Complex analysis requires quality
        if any(keyword in description_lower for keyword in ["analyze", "synthesis", "comprehensive"]):
            return ModelStrategy(
                routing_mode=RoutingMode.QUALITY_FIRST,
                max_cost=1.0,
                required_capabilities=["long_context"],
                privacy_level=PrivacyLevel.EXTERNAL_OK
            )
        
        # Simple searches can be cost-optimized
        if any(keyword in description_lower for keyword in ["search", "find", "lookup"]):
            return ModelStrategy(
                routing_mode=RoutingMode.COST_OPTIMIZED,
                max_cost=0.3,
                required_capabilities=[],
                privacy_level=PrivacyLevel.EXTERNAL_OK
            )
        
        return self.default_model_strategy
    
    def validate_output(self, output: Any, subtask: Subtask) -> float:
        """
        Validate research output.
        
        Checks:
        - Source citations
        - Data completeness
        - Credibility indicators
        - Structured format
        
        Args:
            output: Generated research
            subtask: Original subtask
            
        Returns:
            Validation score (0.0 to 1.0)
        """
        if not isinstance(output, (str, dict)):
            return 0.0
        
        # Convert dict to string for validation
        if isinstance(output, dict):
            output_str = str(output)
        else:
            output_str = output
        
        score = 0.0
        checks_passed = 0
        total_checks = 6
        
        # Check 1: Not empty
        if output_str.strip():
            checks_passed += 1
        
        # Check 2: Substantial content
        if len(output_str) > 200:
            checks_passed += 1
        
        # Check 3: Contains citations or sources
        citation_indicators = ["source:", "reference:", "http", "www", "according to"]
        if any(indicator in output_str.lower() for indicator in citation_indicators):
            checks_passed += 1
        
        # Check 4: Structured format
        if any(marker in output_str for marker in ["1.", "2.", "•", "-", "##", "###"]):
            checks_passed += 1
        
        # Check 5: Contains data or statistics
        data_indicators = ["%", "percent", "number", "data", "study", "research"]
        if any(indicator in output_str.lower() for indicator in data_indicators):
            checks_passed += 1
        
        # Check 6: No obvious errors
        error_indicators = ["error", "failed", "no results", "cannot find"]
        if not any(indicator in output_str.lower() for indicator in error_indicators):
            checks_passed += 1
        
        score = checks_passed / total_checks
        
        logger.debug(f"Validation score: {score:.2f} ({checks_passed}/{total_checks} checks passed)")
        
        return score
    
    def _identify_task_type(self, description: str) -> str:
        """
        Identify research task type.
        
        Args:
            description: Task description
            
        Returns:
            Task type identifier
        """
        description_lower = description.lower()
        
        if any(keyword in description_lower for keyword in ["search", "find", "lookup", "gather"]):
            return "web_search"
        elif any(keyword in description_lower for keyword in ["synthesize", "combine", "merge"]):
            return "data_synthesis"
        elif any(keyword in description_lower for keyword in ["report", "document", "summary"]):
            return "report_generation"
        elif any(keyword in description_lower for keyword in ["trend", "pattern", "forecast"]):
            return "trend_analysis"
        elif any(keyword in description_lower for keyword in ["competitive", "competitor", "compare"]):
            return "competitive_analysis"
        else:
            return "generic"
    
    async def _perform_web_search(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """
        Perform web search and gather data.
        
        Args:
            subtask: Web search subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Search results and gathered data
        """
        query = context.get("query", subtask.description)
        max_results = context.get("max_results", 10)
        
        # Perform search if API is configured
        search_results = []
        if self.search_api_client:
            logger.info(f"Performing web search: {query}")
            # Placeholder for actual search API integration
            search_results = [
                {"title": "Result 1", "url": "https://example.com/1", "snippet": "..."},
                {"title": "Result 2", "url": "https://example.com/2", "snippet": "..."},
            ]
        else:
            # Simulate search results
            search_results = [
                {"title": f"Simulated result for: {query}", "url": "https://example.com", "snippet": "No search API configured"}
            ]
        
        # Analyze and summarize results
        prompt = f"""Analyze the following search results for: {query}

Task: {subtask.description}

Search Results:
{self._format_search_results(search_results)}

Provide:
1. Summary of findings
2. Key insights
3. Relevant data points
4. Source credibility assessment
5. Recommendations for further research
"""
        
        generation_params = GenerationParams(
            max_tokens=2000,
            temperature=0.4,
            system_prompt="You are a research analyst. Provide thorough, objective analysis with citations."
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
            "type": "web_search",
            "query": query,
            "results_count": len(search_results),
            "analysis": response.content,
            "sources": search_results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _synthesize_data(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """
        Synthesize data from multiple sources.
        
        Args:
            subtask: Data synthesis subtask
            context: Execution context with source data
            model_strategy: Model selection strategy
            
        Returns:
            Synthesized analysis
        """
        sources = context.get("sources", [])
        
        if not sources:
            return {"error": "No sources provided for synthesis"}
        
        prompt = f"""Synthesize information from multiple sources:

Task: {subtask.description}

Sources ({len(sources)} total):
{self._format_sources(sources)}

Provide:
1. Integrated summary
2. Common themes and patterns
3. Contradictions or disagreements
4. Confidence level in findings
5. Data quality assessment
6. Synthesized conclusions
"""
        
        generation_params = GenerationParams(
            max_tokens=3000,
            temperature=0.3,
            system_prompt="You are a research synthesizer. Integrate information objectively and identify patterns."
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
            "type": "data_synthesis",
            "sources_count": len(sources),
            "synthesis": response.content,
            "credibility_score": self._assess_credibility(sources),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _generate_report(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """
        Generate structured research report.
        
        Args:
            subtask: Report generation subtask
            context: Execution context with research data
            model_strategy: Model selection strategy
            
        Returns:
            Structured report with citations
        """
        topic = context.get("topic", subtask.description)
        research_data = context.get("research_data", "")
        report_format = context.get("format", "comprehensive")
        
        prompt = f"""Generate a {report_format} research report on: {topic}

Task: {subtask.description}

Research Data:
{research_data}

Structure the report with:
1. Executive Summary
2. Introduction and Background
3. Methodology
4. Findings and Analysis
5. Key Insights
6. Conclusions
7. Recommendations
8. References and Citations

Use professional academic style with proper citations.
"""
        
        generation_params = GenerationParams(
            max_tokens=4000,
            temperature=0.4,
            system_prompt="You are a research report writer. Create comprehensive, well-structured reports with citations."
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
            "type": "research_report",
            "topic": topic,
            "format": report_format,
            "report": response.content,
            "word_count": len(response.content.split()),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _analyze_trends(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """
        Analyze trends and patterns.
        
        Args:
            subtask: Trend analysis subtask
            context: Execution context with data
            model_strategy: Model selection strategy
            
        Returns:
            Trend analysis and insights
        """
        data = context.get("data", [])
        time_period = context.get("time_period", "recent")
        
        prompt = f"""Analyze trends and patterns:

Task: {subtask.description}
Time Period: {time_period}

Data Points: {len(data) if isinstance(data, list) else 'provided'}

Provide:
1. Identified trends
2. Pattern analysis
3. Growth/decline indicators
4. Anomalies or outliers
5. Predictive insights
6. Confidence levels
7. Recommendations
"""
        
        generation_params = GenerationParams(
            max_tokens=2500,
            temperature=0.3,
            system_prompt="You are a trend analyst. Identify patterns and provide data-driven insights."
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
            "type": "trend_analysis",
            "time_period": time_period,
            "analysis": response.content,
            "data_points": len(data) if isinstance(data, list) else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _competitive_analysis(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> Dict[str, Any]:
        """
        Perform competitive analysis.
        
        Args:
            subtask: Competitive analysis subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Competitive analysis report
        """
        competitors = context.get("competitors", [])
        criteria = context.get("criteria", [])
        
        prompt = f"""Perform competitive analysis:

Task: {subtask.description}

Competitors: {', '.join(competitors) if competitors else 'To be identified'}
Analysis Criteria: {', '.join(criteria) if criteria else 'Standard business metrics'}

Provide:
1. Competitor profiles
2. Strengths and weaknesses
3. Market positioning
4. Competitive advantages
5. Threats and opportunities
6. Market share analysis
7. Strategic recommendations
8. Comparison matrix
"""
        
        generation_params = GenerationParams(
            max_tokens=3000,
            temperature=0.3,
            system_prompt="You are a competitive intelligence analyst. Provide objective, strategic analysis."
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
            "type": "competitive_analysis",
            "competitors": competitors,
            "analysis": response.content,
            "criteria": criteria,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _execute_generic_research(
        self,
        subtask: Subtask,
        context: Dict[str, Any],
        model_strategy: ModelStrategy
    ) -> str:
        """
        Execute generic research task.
        
        Args:
            subtask: Generic research subtask
            context: Execution context
            model_strategy: Model selection strategy
            
        Returns:
            Research output
        """
        prompt = f"""Conduct research on:

Task: {subtask.description}

Context: {context.get('additional_context', 'None provided')}

Provide comprehensive research with:
1. Background information
2. Key findings
3. Data and statistics
4. Analysis
5. Sources and citations
"""
        
        generation_params = GenerationParams(
            max_tokens=2500,
            temperature=0.4,
            system_prompt="You are a research specialist. Provide thorough, well-cited research."
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
    
    def _format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Format search results for prompt.
        
        Args:
            results: List of search results
            
        Returns:
            Formatted string
        """
        formatted = []
        for i, result in enumerate(results, 1):
            formatted.append(
                f"{i}. {result.get('title', 'No title')}\n"
                f"   URL: {result.get('url', 'No URL')}\n"
                f"   {result.get('snippet', 'No snippet')}\n"
            )
        return "\n".join(formatted)
    
    def _format_sources(self, sources: List[Any]) -> str:
        """
        Format sources for prompt.
        
        Args:
            sources: List of sources
            
        Returns:
            Formatted string
        """
        formatted = []
        for i, source in enumerate(sources, 1):
            if isinstance(source, dict):
                formatted.append(f"{i}. {source.get('title', 'Source')}:\n   {source.get('content', str(source))}\n")
            else:
                formatted.append(f"{i}. {str(source)}\n")
        return "\n".join(formatted)
    
    def _assess_credibility(self, sources: List[Any]) -> float:
        """
        Assess credibility of sources.
        
        Args:
            sources: List of sources
            
        Returns:
            Credibility score (0.0 to 1.0)
        """
        if not sources:
            return 0.0
        
        # Simplified credibility assessment
        # In production, use more sophisticated analysis
        credible_indicators = [".edu", ".gov", ".org", "research", "study", "journal"]
        
        credible_count = 0
        for source in sources:
            source_str = str(source).lower()
            if any(indicator in source_str for indicator in credible_indicators):
                credible_count += 1
        
        return min(credible_count / len(sources), 1.0)
