import { useState, useEffect } from 'react';
import { apiClient, type TaskStatus } from '../../lib/api';
import { wsClient } from '../../lib/websocket';
import type { Task } from '../../types';
import { CheckCircle, XCircle, Loader, Clock, User } from 'lucide-react';
import './TaskDetail.css';

interface TaskDetailProps {
  taskId: string;
  onClose: () => void;
}

export default function TaskDetail({ taskId, onClose }: TaskDetailProps) {
  const [task, setTask] = useState<Task | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadTaskDetails = async () => {
      try {
        setLoading(true);
        const [taskData, statusData] = await Promise.all([
          apiClient.getTask(taskId),
          apiClient.getTaskStatus(taskId),
        ]);
        setTask(taskData);
        setTaskStatus(statusData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load task details');
      } finally {
        setLoading(false);
      }
    };

    loadTaskDetails();

    // Listen for task updates
    wsClient.onTaskUpdate((update) => {
      if (update.task_id === taskId) {
        setTaskStatus((prev) =>
          prev
            ? {
                ...prev,
                status: update.status,
                progress: update.progress,
              }
            : null
        );
      }
    });
  }, [taskId]);

  if (loading) {
    return (
      <div className="task-detail">
        <div className="task-detail-loading">
          <div className="spinner" />
          <p>Loading task details...</p>
        </div>
      </div>
    );
  }

  if (error || !task || !taskStatus) {
    return (
      <div className="task-detail">
        <div className="task-detail-error">
          <p>Error: {error || 'Task not found'}</p>
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    );
  }

  const getSubtaskIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="subtask-icon success" size={16} />;
      case 'failed':
        return <XCircle className="subtask-icon error" size={16} />;
      case 'running':
        return <Loader className="subtask-icon running" size={16} />;
      default:
        return <Clock className="subtask-icon pending" size={16} />;
    }
  };

  return (
    <div className="task-detail">
      <div className="task-detail-header">
        <h2>Task Details</h2>
        <button onClick={onClose} className="close-button">
          ×
        </button>
      </div>

      <div className="task-detail-body">
        <section className="task-info">
          <h3>Task Information</h3>
          <div className="info-grid">
            <div className="info-item">
              <label>ID:</label>
              <span>{task.id}</span>
            </div>
            <div className="info-item">
              <label>Command:</label>
              <span>{task.command}</span>
            </div>
            <div className="info-item">
              <label>Status:</label>
              <span className={`status-badge status-${task.status}`}>
                {task.status}
              </span>
            </div>
            <div className="info-item">
              <label>Progress:</label>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${taskStatus.progress}%` }}
                />
                <span className="progress-text">{taskStatus.progress}%</span>
              </div>
            </div>
            {task.cost !== undefined && (
              <div className="info-item">
                <label>Cost:</label>
                <span>${task.cost.toFixed(4)}</span>
              </div>
            )}
            {task.latency_ms !== undefined && (
              <div className="info-item">
                <label>Latency:</label>
                <span>{task.latency_ms}ms</span>
              </div>
            )}
          </div>
        </section>

        {taskStatus.active_agents && taskStatus.active_agents.length > 0 && (
          <section className="active-agents">
            <h3>Active Agents</h3>
            <div className="agent-list">
              {taskStatus.active_agents.map((agent, index) => (
                <div key={index} className="agent-item">
                  <User size={16} />
                  <span>{agent}</span>
                  <Loader className="agent-spinner" size={14} />
                </div>
              ))}
            </div>
          </section>
        )}

        {taskStatus.subtasks && taskStatus.subtasks.length > 0 && (
          <section className="subtasks">
            <h3>Subtasks</h3>
            <div className="subtask-list">
              {taskStatus.subtasks.map((subtask) => (
                <div key={subtask.id} className="subtask-item">
                  <div className="subtask-header">
                    {getSubtaskIcon(subtask.status)}
                    <span className="subtask-description">
                      {subtask.description}
                    </span>
                  </div>
                  <div className="subtask-meta">
                    <span className="subtask-agent">{subtask.agent_type}</span>
                    <span className={`subtask-status status-${subtask.status}`}>
                      {subtask.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {task.result && (
          <section className="task-result">
            <h3>Result</h3>
            <pre className="result-content">
              {JSON.stringify(task.result, null, 2)}
            </pre>
          </section>
        )}
      </div>
    </div>
  );
}
