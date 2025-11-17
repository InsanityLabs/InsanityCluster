import { DollarSign, TrendingUp, Activity, Hash } from 'lucide-react';
import './CostMetrics.css';

interface CostMetricsProps {
  data: {
    total_spend: number;
    cost_per_task: number;
    daily_spend: number;
    task_count: number;
  };
}

export default function CostMetrics({ data }: CostMetricsProps) {
  return (
    <div className="cost-metrics">
      <h3>Cost Metrics</h3>
      <div className="metrics-cards">
        <div className="metric-card">
          <div className="metric-icon">
            <DollarSign size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-label">Total Spend</div>
            <div className="metric-value">${data.total_spend.toFixed(2)}</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">
            <TrendingUp size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-label">Daily Spend</div>
            <div className="metric-value">${data.daily_spend.toFixed(2)}</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">
            <Activity size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-label">Cost per Task</div>
            <div className="metric-value">${data.cost_per_task.toFixed(4)}</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">
            <Hash size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-label">Total Tasks</div>
            <div className="metric-value">{data.task_count}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
