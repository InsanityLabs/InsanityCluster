import { useState, useEffect } from 'react';
import { apiClient } from '../../lib/api';
import { wsClient } from '../../lib/websocket';
import type { Task } from '../../types';
import TaskItem from './TaskItem';
import './TaskList.css';

interface TaskListProps {
  onTaskSelect: (taskId: string) => void;
}

export default function TaskList({ onTaskSelect }: TaskListProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTasks();

    // Listen for task updates via WebSocket
    wsClient.onTaskUpdate((update) => {
      setTasks((prevTasks) =>
        prevTasks.map((task) =>
          task.id === update.task_id
            ? { ...task, status: update.status as Task['status'] }
            : task
        )
      );
    });
  }, []);

  const loadTasks = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getTasks(50);
      setTasks(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  const handleCancelTask = async (taskId: string) => {
    try {
      await apiClient.cancelTask(taskId);
      setTasks((prevTasks) =>
        prevTasks.map((task) =>
          task.id === taskId ? { ...task, status: 'cancelled' } : task
        )
      );
    } catch (err) {
      console.error('Failed to cancel task:', err);
    }
  };

  if (loading) {
    return (
      <div className="task-list-loading">
        <div className="spinner" />
        <p>Loading tasks...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="task-list-error">
        <p>Error: {error}</p>
        <button onClick={loadTasks}>Retry</button>
      </div>
    );
  }

  return (
    <div className="task-list">
      <div className="task-list-header">
        <h2>Tasks</h2>
        <button onClick={loadTasks} className="refresh-button">
          Refresh
        </button>
      </div>

      {tasks.length === 0 ? (
        <div className="task-list-empty">
          <p>No tasks found</p>
        </div>
      ) : (
        <div className="task-list-items">
          {tasks.map((task) => (
            <TaskItem
              key={task.id}
              task={task}
              onSelect={() => onTaskSelect(task.id)}
              onCancel={() => handleCancelTask(task.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
