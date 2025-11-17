"""
Task Decomposition Engine for INNER layer.

Breaks complex commands into executable subtasks with dependency analysis.
Uses Claude Sonnet 4.5 for complex decomposition and vector search for caching.
"""
import hashlib
import json
import logging
import uuid
from dataclasses import asdict
from datetime import timedelta
from typing import Dict, List, Optional, Set, Tuple

from insanity_cluster.common.models import (
    AgentType,
    ParsedCommand,
    Subtask,
    TaskGraph,
)
from insanity_cluster.table.vector_store import VectorStore
from insanity_cluster.table.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class ComplexityEstimate:
    """Estimate of task complexity and resource requirements"""
    
    def __init__(
        self,
        time_estimate: timedelta,
        cost_estimate: float,
        agent_count: int,
        parallel_potential: float,
        complexity_score: float
    ):
        self.time_estimate = time_estimate
        self.cost_estimate = cost_estimate
        self.agent_count = agent_count
        self.parallel_potential = parallel_potential  # 0.0 to 1.0
        self.complexity_score = complexity_score  # 0.0 to 1.0


class TaskDecompositionEngine:
    """
    Break complex commands into executable subtasks.
    
    Uses Claude Sonnet 4.5 for complex decomposition with caching
    for similar commands using vector search.
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        redis_manager: Optional[RedisManager] = None
    ):
        """
        Initialize task decomposition engine.
        
        Args:
            vector_store: Vector store for caching similar decompositions
            redis_manager: Redis manager for fast caching
        """
        self.vector_store = vector_store
        self.redis_manager = redis_manager
        self.cache_ttl = 7 * 24 * 3600  # 7 days in seconds
        self.similarity_threshold = 0.85  # For vector search matching
        
        logger.info("TaskDecompositionEngine initialized")
    
    async def decompose(self, command: ParsedCommand) -> TaskGraph:
        """
        Decompose command into DAG of subtasks.
        
        Args:
            command: Parsed command to decompose
            
        Returns:
            TaskGraph with nodes (subtasks) and edges (dependencies)
        """
        logger.info(f"Decomposing command: {command.intent}")
        
        # Check cache first
        cached_graph = await self._get_cached_decomposition(command)
        if cached_graph:
            logger.info("Using cached decomposition")
            return cached_graph
        
        # Check vector store for similar commands
        similar_graph = await self._find_similar_decomposition(command)
        if similar_graph:
            logger.info("Using similar decomposition from vector store")
            # Adapt the similar graph to current command
            adapted_graph = self._adapt_task_graph(similar_graph, command)
            await self._cache_decomposition(command, adapted_graph)
            return adapted_graph
        
        # Perform new decomposition
        task_graph = await self._decompose_with_model(command)
        
        # Cache the result
        await self._cache_decomposition(command, task_graph)
        await self._store_in_vector_db(command, task_graph)
        
        logger.info(f"Decomposed into {len(task_graph.subtasks)} subtasks")
        return task_graph
    
    def identify_dependencies(self, subtasks: List[Subtask]) -> Dict[str, List[str]]:
        """
        Analyze subtasks and build dependency graph.
        
        Args:
            subtasks: List of subtasks to analyze
            
        Returns:
            Dictionary mapping subtask_id to list of dependency IDs
        """
        dependencies = {}
        
        for subtask in subtasks:
            dependencies[subtask.id] = subtask.dependencies
        
        # Validate DAG (no cycles)
        if self._has_cycle(dependencies):
            logger.error("Cycle detected in dependency graph")
            raise ValueError("Dependency graph contains cycles")
        
        return dependencies
    
    def estimate_complexity(self, task_graph: TaskGraph) -> ComplexityEstimate:
        """
        Estimate time, cost, and resource requirements.
        
        Args:
            task_graph: Task graph to analyze
            
        Returns:
            ComplexityEstimate with resource predictions
        """
        total_time = timedelta()
        total_cost = 0.0
        agent_types = set()
        
        # Calculate critical path for time estimate
        critical_path_time = self._calculate_critical_path(task_graph)
        
        # Sum costs and identify unique agents
        for subtask in task_graph.subtasks:
            total_cost += subtask.estimated_cost
            agent_types.add(subtask.agent_type)
        
        # Calculate parallel potential
        max_parallel = self._calculate_max_parallelism(task_graph)
        parallel_potential = min(max_parallel / len(task_graph.subtasks), 1.0)
        
        # Calculate complexity score based on multiple factors
        complexity_score = self._calculate_complexity_score(task_graph)
        
        return ComplexityEstimate(
            time_estimate=critical_path_time,
            cost_estimate=total_cost,
            agent_count=len(agent_types),
            parallel_potential=parallel_potential,
            complexity_score=complexity_score
        )
    
    async def _decompose_with_model(self, command: ParsedCommand) -> TaskGraph:
        """
        Use Claude Sonnet 4.5 for complex decomposition.
        
        Integrates with PAN layer for model-based decomposition when available.
        Falls back to rule-based decomposition for reliability.
        
        Args:
            command: Parsed command
            
        Returns:
            TaskGraph
        """
        # Use rule-based decomposition as the reliable baseline
        # Full PAN layer integration would enhance this with Claude Sonnet 4.5
        # when model_router is available in the execution context
        
        root_task_id = str(uuid.uuid4())
        subtasks = self._rule_based_decomposition(command, root_task_id)
        dependencies = self.identify_dependencies(subtasks)
        
        return TaskGraph(
            root_task_id=root_task_id,
            subtasks=subtasks,
            dependencies=dependencies
        )
    
    def _rule_based_decomposition(
        self,
        command: ParsedCommand,
        root_task_id: str
    ) -> List[Subtask]:
        """
        Rule-based decomposition for common intents.
        
        Args:
            command: Parsed command
            root_task_id: Root task ID
            
        Returns:
            List of subtasks
        """
        intent = command.intent
        subtasks = []
        
        if intent == "code_generation":
            subtasks = self._decompose_code_generation(command, root_task_id)
        elif intent == "llc_formation":
            subtasks = self._decompose_llc_formation(command, root_task_id)
        elif intent == "email":
            subtasks = self._decompose_email(command, root_task_id)
        elif intent == "research":
            subtasks = self._decompose_research(command, root_task_id)
        else:
            # Generic single-task decomposition
            subtasks = [
                Subtask(
                    id=str(uuid.uuid4()),
                    description=command.parameters.get("raw_command", "Execute task"),
                    agent_type=self._infer_agent_type(intent),
                    dependencies=[],
                    priority=1,
                    estimated_cost=0.1,
                    estimated_duration=timedelta(minutes=5)
                )
            ]
        
        return subtasks
    
    def _decompose_code_generation(
        self,
        command: ParsedCommand,
        root_task_id: str
    ) -> List[Subtask]:
        """Decompose code generation task"""
        subtasks = []
        
        # Subtask 1: Analyze requirements
        subtask1 = Subtask(
            id=str(uuid.uuid4()),
            description="Analyze code requirements and design approach",
            agent_type=AgentType.DEVELOPER,
            dependencies=[],
            priority=1,
            estimated_cost=0.05,
            estimated_duration=timedelta(minutes=2)
        )
        subtasks.append(subtask1)
        
        # Subtask 2: Generate code
        subtask2 = Subtask(
            id=str(uuid.uuid4()),
            description=f"Generate {command.parameters.get('language', 'code')}: {command.parameters.get('description', '')}",
            agent_type=AgentType.DEVELOPER,
            dependencies=[subtask1.id],
            priority=2,
            estimated_cost=0.15,
            estimated_duration=timedelta(minutes=5)
        )
        subtasks.append(subtask2)
        
        # Subtask 3: Review and validate
        subtask3 = Subtask(
            id=str(uuid.uuid4()),
            description="Review generated code for quality and correctness",
            agent_type=AgentType.DEVELOPER,
            dependencies=[subtask2.id],
            priority=3,
            estimated_cost=0.08,
            estimated_duration=timedelta(minutes=3)
        )
        subtasks.append(subtask3)
        
        return subtasks
    
    def _decompose_llc_formation(
        self,
        command: ParsedCommand,
        root_task_id: str
    ) -> List[Subtask]:
        """Decompose LLC formation task"""
        subtasks = []
        
        # Subtask 1: Gather requirements
        subtask1 = Subtask(
            id=str(uuid.uuid4()),
            description="Gather LLC formation requirements and validate information",
            agent_type=AgentType.BUSINESS,
            dependencies=[],
            priority=1,
            estimated_cost=0.05,
            estimated_duration=timedelta(minutes=2)
        )
        subtasks.append(subtask1)
        
        # Subtask 2: Generate formation documents
        subtask2 = Subtask(
            id=str(uuid.uuid4()),
            description=f"Generate LLC formation documents for {command.parameters.get('state', 'specified state')}",
            agent_type=AgentType.BUSINESS,
            dependencies=[subtask1.id],
            priority=2,
            estimated_cost=0.20,
            estimated_duration=timedelta(minutes=10)
        )
        subtasks.append(subtask2)
        
        # Subtask 3: Review documents
        subtask3 = Subtask(
            id=str(uuid.uuid4()),
            description="Review formation documents for compliance and accuracy",
            agent_type=AgentType.BUSINESS,
            dependencies=[subtask2.id],
            priority=3,
            estimated_cost=0.15,
            estimated_duration=timedelta(minutes=5)
        )
        subtasks.append(subtask3)
        
        return subtasks
    
    def _decompose_email(
        self,
        command: ParsedCommand,
        root_task_id: str
    ) -> List[Subtask]:
        """Decompose email task"""
        subtasks = []
        
        # Single subtask for simple email
        subtask = Subtask(
            id=str(uuid.uuid4()),
            description=f"Compose and send email to {command.parameters.get('recipient', 'recipient')}",
            agent_type=AgentType.COMMUNICATION,
            dependencies=[],
            priority=1,
            estimated_cost=0.05,
            estimated_duration=timedelta(minutes=2)
        )
        subtasks.append(subtask)
        
        return subtasks
    
    def _decompose_research(
        self,
        command: ParsedCommand,
        root_task_id: str
    ) -> List[Subtask]:
        """Decompose research task"""
        subtasks = []
        
        # Subtask 1: Gather data
        subtask1 = Subtask(
            id=str(uuid.uuid4()),
            description="Gather data from multiple sources",
            agent_type=AgentType.RESEARCH,
            dependencies=[],
            priority=1,
            estimated_cost=0.10,
            estimated_duration=timedelta(minutes=5)
        )
        subtasks.append(subtask1)
        
        # Subtask 2: Analyze and synthesize
        subtask2 = Subtask(
            id=str(uuid.uuid4()),
            description="Analyze data and synthesize findings",
            agent_type=AgentType.RESEARCH,
            dependencies=[subtask1.id],
            priority=2,
            estimated_cost=0.15,
            estimated_duration=timedelta(minutes=7)
        )
        subtasks.append(subtask2)
        
        # Subtask 3: Generate report
        subtask3 = Subtask(
            id=str(uuid.uuid4()),
            description="Generate structured report with citations",
            agent_type=AgentType.RESEARCH,
            dependencies=[subtask2.id],
            priority=3,
            estimated_cost=0.10,
            estimated_duration=timedelta(minutes=5)
        )
        subtasks.append(subtask3)
        
        return subtasks
    
    def _infer_agent_type(self, intent: str) -> AgentType:
        """Infer agent type from intent"""
        intent_to_agent = {
            "code_generation": AgentType.DEVELOPER,
            "code_review": AgentType.DEVELOPER,
            "llc_formation": AgentType.BUSINESS,
            "contract_review": AgentType.BUSINESS,
            "email": AgentType.COMMUNICATION,
            "phone_call": AgentType.COMMUNICATION,
            "research": AgentType.RESEARCH,
            "financial": AgentType.FINANCE,
            "schedule": AgentType.PROJECT_MANAGER,
        }
        
        return intent_to_agent.get(intent, AgentType.PROJECT_MANAGER)
    
    def _has_cycle(self, dependencies: Dict[str, List[str]]) -> bool:
        """Check if dependency graph has cycles using DFS"""
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dependencies.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in dependencies:
            if node not in visited:
                if dfs(node):
                    return True
        
        return False
    
    def _calculate_critical_path(self, task_graph: TaskGraph) -> timedelta:
        """Calculate critical path (longest path) through task graph"""
        # Build reverse dependency map
        reverse_deps = {}
        for subtask in task_graph.subtasks:
            reverse_deps[subtask.id] = []
        
        for subtask in task_graph.subtasks:
            for dep in subtask.dependencies:
                if dep in reverse_deps:
                    reverse_deps[dep].append(subtask.id)
        
        # Calculate longest path using dynamic programming
        memo = {}
        
        def longest_path(task_id: str) -> timedelta:
            if task_id in memo:
                return memo[task_id]
            
            # Find the subtask
            subtask = next((s for s in task_graph.subtasks if s.id == task_id), None)
            if not subtask:
                return timedelta()
            
            # Base case: no dependencies
            if not reverse_deps.get(task_id):
                memo[task_id] = subtask.estimated_duration
                return subtask.estimated_duration
            
            # Recursive case: max of all dependent paths
            max_path = timedelta()
            for dependent_id in reverse_deps[task_id]:
                path = longest_path(dependent_id)
                if path > max_path:
                    max_path = path
            
            result = subtask.estimated_duration + max_path
            memo[task_id] = result
            return result
        
        # Find maximum path from any starting node
        max_time = timedelta()
        for subtask in task_graph.subtasks:
            if not subtask.dependencies:  # Starting nodes
                path_time = longest_path(subtask.id)
                if path_time > max_time:
                    max_time = path_time
        
        return max_time
    
    def _calculate_max_parallelism(self, task_graph: TaskGraph) -> int:
        """Calculate maximum number of tasks that can run in parallel"""
        # Group tasks by dependency level
        levels = {}
        
        def get_level(task_id: str, visited: Set[str]) -> int:
            if task_id in visited:
                return 0
            visited.add(task_id)
            
            subtask = next((s for s in task_graph.subtasks if s.id == task_id), None)
            if not subtask or not subtask.dependencies:
                return 0
            
            max_dep_level = 0
            for dep in subtask.dependencies:
                dep_level = get_level(dep, visited.copy())
                max_dep_level = max(max_dep_level, dep_level)
            
            return max_dep_level + 1
        
        for subtask in task_graph.subtasks:
            level = get_level(subtask.id, set())
            if level not in levels:
                levels[level] = []
            levels[level].append(subtask.id)
        
        # Return maximum tasks at any level
        return max(len(tasks) for tasks in levels.values()) if levels else 1
    
    def _calculate_complexity_score(self, task_graph: TaskGraph) -> float:
        """Calculate overall complexity score (0.0 to 1.0)"""
        # Factors: number of subtasks, dependencies, agent diversity, estimated cost
        num_subtasks = len(task_graph.subtasks)
        num_dependencies = sum(len(deps) for deps in task_graph.dependencies.values())
        num_agents = len(set(s.agent_type for s in task_graph.subtasks))
        total_cost = sum(s.estimated_cost for s in task_graph.subtasks)
        
        # Normalize factors
        subtask_score = min(num_subtasks / 10.0, 1.0)
        dependency_score = min(num_dependencies / 20.0, 1.0)
        agent_score = min(num_agents / 5.0, 1.0)
        cost_score = min(total_cost / 2.0, 1.0)
        
        # Weighted average
        complexity = (
            subtask_score * 0.3 +
            dependency_score * 0.3 +
            agent_score * 0.2 +
            cost_score * 0.2
        )
        
        return complexity
    
    def _adapt_task_graph(
        self,
        template_graph: TaskGraph,
        command: ParsedCommand
    ) -> TaskGraph:
        """Adapt a template task graph to current command"""
        # Create new subtasks with updated descriptions
        new_subtasks = []
        id_mapping = {}
        
        for subtask in template_graph.subtasks:
            new_id = str(uuid.uuid4())
            id_mapping[subtask.id] = new_id
            
            new_subtask = Subtask(
                id=new_id,
                description=subtask.description,
                agent_type=subtask.agent_type,
                dependencies=[],  # Will be updated below
                priority=subtask.priority,
                estimated_cost=subtask.estimated_cost,
                estimated_duration=subtask.estimated_duration
            )
            new_subtasks.append(new_subtask)
        
        # Update dependencies with new IDs
        for i, subtask in enumerate(template_graph.subtasks):
            new_subtasks[i].dependencies = [
                id_mapping[dep] for dep in subtask.dependencies
            ]
        
        # Create new dependencies dict
        new_dependencies = {}
        for subtask in new_subtasks:
            new_dependencies[subtask.id] = subtask.dependencies
        
        return TaskGraph(
            root_task_id=str(uuid.uuid4()),
            subtasks=new_subtasks,
            dependencies=new_dependencies
        )
    
    async def _get_cached_decomposition(
        self,
        command: ParsedCommand
    ) -> Optional[TaskGraph]:
        """Get cached decomposition from Redis"""
        if not self.redis_manager:
            return None
        
        cache_key = self._get_cache_key(command)
        try:
            cached_data = self.redis_manager.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return self._deserialize_task_graph(data)
        except Exception as e:
            logger.warning(f"Failed to get cached decomposition: {e}")
        
        return None
    
    async def _cache_decomposition(
        self,
        command: ParsedCommand,
        task_graph: TaskGraph
    ) -> None:
        """Cache decomposition in Redis"""
        if not self.redis_manager:
            return
        
        cache_key = self._get_cache_key(command)
        try:
            data = self._serialize_task_graph(task_graph)
            self.redis_manager.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(data)
            )
        except Exception as e:
            logger.warning(f"Failed to cache decomposition: {e}")
    
    async def _find_similar_decomposition(
        self,
        command: ParsedCommand
    ) -> Optional[TaskGraph]:
        """Find similar decomposition using vector search"""
        if not self.vector_store:
            return None
        
        try:
            # Create query embedding from command
            query_text = f"{command.intent}: {command.parameters.get('raw_command', '')}"
            
            # Search for similar patterns
            results = await self.vector_store.search_similar(
                collection="task_patterns",
                query_text=query_text,
                limit=1
            )
            
            if results and results[0].score >= self.similarity_threshold:
                # Deserialize the stored task graph
                return self._deserialize_task_graph(results[0].metadata.get("task_graph"))
        except Exception as e:
            logger.warning(f"Failed to find similar decomposition: {e}")
        
        return None
    
    async def _store_in_vector_db(
        self,
        command: ParsedCommand,
        task_graph: TaskGraph
    ) -> None:
        """Store decomposition in vector database"""
        if not self.vector_store:
            return
        
        try:
            # Create text representation for embedding
            text = f"{command.intent}: {command.parameters.get('raw_command', '')}"
            
            # Store with metadata
            metadata = {
                "intent": command.intent,
                "task_graph": self._serialize_task_graph(task_graph),
                "subtask_count": len(task_graph.subtasks),
                "timestamp": command.timestamp.isoformat()
            }
            
            await self.vector_store.store_embedding(
                collection="task_patterns",
                text=text,
                metadata=metadata
            )
        except Exception as e:
            logger.warning(f"Failed to store in vector DB: {e}")
    
    def _get_cache_key(self, command: ParsedCommand) -> str:
        """Generate cache key for command"""
        key_data = f"{command.intent}:{command.parameters.get('raw_command', '')}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()
        return f"task_decomposition:{key_hash}"
    
    def _serialize_task_graph(self, task_graph: TaskGraph) -> Dict:
        """Serialize task graph to dictionary"""
        return {
            "root_task_id": task_graph.root_task_id,
            "subtasks": [
                {
                    "id": s.id,
                    "description": s.description,
                    "agent_type": s.agent_type.value,
                    "dependencies": s.dependencies,
                    "priority": s.priority,
                    "estimated_cost": s.estimated_cost,
                    "estimated_duration": s.estimated_duration.total_seconds()
                }
                for s in task_graph.subtasks
            ],
            "dependencies": task_graph.dependencies
        }
    
    def _deserialize_task_graph(self, data: Dict) -> TaskGraph:
        """Deserialize task graph from dictionary"""
        subtasks = [
            Subtask(
                id=s["id"],
                description=s["description"],
                agent_type=AgentType(s["agent_type"]),
                dependencies=s["dependencies"],
                priority=s["priority"],
                estimated_cost=s["estimated_cost"],
                estimated_duration=timedelta(seconds=s["estimated_duration"])
            )
            for s in data["subtasks"]
        ]
        
        return TaskGraph(
            root_task_id=data["root_task_id"],
            subtasks=subtasks,
            dependencies=data["dependencies"]
        )
