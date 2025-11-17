import { CheckCircle, XCircle, Activity, Layers } from 'lucide-react';
import './SystemMetrics.css';

interface SystemMetricsProps {
  data: {
    task_completion_rate: number;
    error_rate: number;
    active_tasks: number;
    queue_depth: number;
  };
}

export default function SystemMetrics({ data }: SystemMetricsProps) {
  return (
    <div className="system-metrics">
      <h3>System Metrics</h3>
      <div className="metrics-cards">
        <div className="metric-card">
          <div className="metric-icon success">
            <CheckCircle size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-label">Completion Rate</div>
            <div className="metric-value">{(data.task_completion_rate * 100).toFixed(1)}%</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon error">
            <XCircle size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-label">Error Rate</div>
            <div className="metric-value">{(data.error_rate * 100).toFixed(1)}%</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">
            <Activity size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-label">Active Tasks</div>
            <div className="metric-value">{data.active_tasks}</div>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon">
            <Layers size={24} />
          </div>
          <div className="metric-content">
            <div className="metric-label">Queue Depth</div>
            <div className="metric-value">{data.queue_depth}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
