import type { Task } from '../../types';
import { Clock, DollarSign, CheckCircle, XCircle, Loader, AlertCircle } from 'lucide-react';
import './TaskItem.css';

interface TaskItemProps {
  task: Task;
  onSelect: () => void;
  onCancel: () => void;
}

export default function TaskItem({ task, onSelect, onCancel }: TaskItemProps) {
  const getStatusIcon = () => {
    switch (task.status) {
      case 'completed':
        return <CheckCircle className="status-icon success" />;
      case 'failed':
        return <XCircle className="status-icon error" />;
      case 'running':
        return <Loader className="status-icon running" />;
      case 'cancelled':
        return <AlertCircle className="status-icon warning" />;
      default:
        return <Clock className="status-icon pending" />;
    }
  };

  const getStatusClass = () => {
    return `task-item status-${task.status}`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatDuration = () => {
    if (!task.completed_at) return null;
    const start = new Date(task.created_at).getTime();
    const end = new Date(task.completed_at).getTime();
    const duration = (end - start) / 1000;
    return `${duration.toFixed(2)}s`;
  };

  return (
    <div className={getStatusClass()} onClick={onSelect}>
      <div className="task-item-header">
        <div className="task-status">
          {getStatusIcon()}
          <span className="status-text">{task.status}</span>
        </div>
        <div className="task-actions">
          {task.status === 'running' && (
            <button
              className="cancel-button"
              onClick={(e) => {
                e.stopPropagation();
                onCancel();
              }}
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      <div className="task-item-body">
        <p className="task-command">{task.command}</p>
        <div className="task-metadata">
          <span className="task-id">ID: {task.id.slice(0, 8)}</span>
          <span className="task-created">
            <Clock size={14} />
            {formatDate(task.created_at)}
          </span>
          {task.cost !== undefined && (
            <span className="task-cost">
              <DollarSign size={14} />
              ${task.cost.toFixed(4)}
            </span>
          )}
          {task.latency_ms !== undefined && (
            <span className="task-latency">
              <Clock size={14} />
              {task.latency_ms}ms
            </span>
          )}
          {formatDuration() && (
            <span className="task-duration">
              Duration: {formatDuration()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
