export interface Task {
  id: string;
  command: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  task_graph?: TaskGraph;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  result?: any;
  cost?: number;
  latency_ms?: number;
  created_at: string;
  completed_at?: string;
}

export interface TaskGraph {
  root_task_id: string;
  subtasks: Subtask[];
  dependencies: Record<string, string[]>;
}

export interface Subtask {
  id: string;
  description: string;
  agent_type: string;
  dependencies: string[];
  priority: number;
  estimated_cost: number;
  estimated_duration: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
}

export interface AgentType {
  name: string;
  description: string;
  capabilities: string[];
}

export interface ModelConfig {
  mode: 'LOCAL' | 'OPENROUTER_FREE' | 'MIXED' | 'WEB' | 'OPENROUTER_PAID';
  default_strategy: 'SPEED_FIRST' | 'QUALITY_FIRST' | 'COST_OPTIMIZED' | 'TASK_SPECIFIC';
  max_cost_per_task?: number;
  max_cost_per_day?: number;
  local_complexity_threshold?: number;
  agent_overrides?: Record<string, AgentModelConfig>;
  task_type_overrides?: Record<string, TaskModelConfig>;
}

export interface AgentModelConfig {
  preferred_models: string[];
  fallback_to_paid: boolean;
  max_cost?: number;
}

export interface TaskModelConfig {
  model_override?: string;
  strategy_override?: string;
  allow_local: boolean;
  allow_paid: boolean;
}

export interface MetricsData {
  cost: {
    total_spend: number;
    cost_per_task: number;
    daily_spend: number;
    task_count: number;
  };
  latency: {
    p50: number;
    p95: number;
    p99: number;
    avg: number;
  };
  system: {
    task_completion_rate: number;
    error_rate: number;
    active_tasks: number;
    queue_depth: number;
  };
}
