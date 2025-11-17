import { useState, useEffect } from 'react';
import { apiClient } from '../../lib/api';
import type { Task } from '../../types';
import { CheckCircle, XCircle, Clock, DollarSign } from 'lucide-react';
import './TaskHistory.css';

export default function TaskHistory() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTasks();
  }, []);

  const loadTasks = async () => {
    try {
      const data = await apiClient.getTasks(20);
      setTasks(data.filter((t) => t.status === 'completed' || t.status === 'failed'));
    } catch (err) {
      console.error('Failed to load task history:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="task-history">
        <h3>Task History</h3>
        <div className="history-loading">
          <div className="spinner" />
        </div>
      </div>
    );
  }

  return (
    <div className="task-history">
      <h3>Task History</h3>
      {tasks.length === 0 ? (
        <div className="history-empty">
          <p>No completed tasks yet</p>
        </div>
      ) : (
        <div className="history-table">
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Command</th>
                <th>Cost</th>
                <th>Latency</th>
                <th>Completed</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.id}>
                  <td>
                    {task.status === 'completed' ? (
                      <CheckCircle className="status-icon success" size={16} />
                    ) : (
                      <XCircle className="status-icon error" size={16} />
                    )}
                  </td>
                  <td className="command-cell">{task.command}</td>
                  <td>
                    {task.cost !== undefined ? (
                      <span className="cost-cell">
                        <DollarSign size={12} />
                        {task.cost.toFixed(4)}
                      </span>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td>
                    {task.latency_ms !== undefined ? (
                      <span className="latency-cell">
                        <Clock size={12} />
                        {task.latency_ms}ms
                      </span>
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="date-cell">
                    {task.completed_at ? formatDate(task.completed_at) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
