import { useState } from 'react';
import TaskList from './TaskList';
import TaskDetail from './TaskDetail';
import './TaskMonitor.css';

export default function TaskMonitor() {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);

  return (
    <div className="task-monitor">
      <TaskList onTaskSelect={setSelectedTaskId} />
      {selectedTaskId && (
        <TaskDetail
          taskId={selectedTaskId}
          onClose={() => setSelectedTaskId(null)}
        />
      )}
    </div>
  );
}
