import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import type { TaskModelConfig } from '../../types';
import './TaskTypeConfig.css';

interface TaskTypeConfigProps {
  taskTypeOverrides: Record<string, TaskModelConfig>;
  onChange: (overrides: Record<string, TaskModelConfig>) => void;
}

const COMMON_TASK_TYPES = [
  'code_generation',
  'code_review',
  'simple_chat',
  'document_analysis',
  'web_search',
  'email_composition',
  'contract_review',
  'financial_calculations',
];

const AVAILABLE_MODELS = [
  'claude-sonnet-4.5',
  'claude-haiku-4.5',
  'claude-opus-4.1',
  'gpt-5.1',
  'gpt-5',
  'gpt-5-mini',
  'gpt-5-nano',
  'gpt-5-codex',
  'local:llama3-70b',
  'local:mistral-7b',
  'local:codellama',
  'local:phi-3',
];

const STRATEGIES = ['SPEED_FIRST', 'QUALITY_FIRST', 'COST_OPTIMIZED', 'TASK_SPECIFIC'];

export default function TaskTypeConfig({ taskTypeOverrides, onChange }: TaskTypeConfigProps) {
  const [newTaskType, setNewTaskType] = useState('');

  const handleAddTaskType = (taskType: string) => {
    if (taskType && !taskTypeOverrides[taskType]) {
      onChange({
        ...taskTypeOverrides,
        [taskType]: {
          model_override: undefined,
          strategy_override: undefined,
          allow_local: true,
          allow_paid: true,
        },
      });
      setNewTaskType('');
    }
  };

  const handleRemoveTaskType = (taskType: string) => {
    const newOverrides = { ...taskTypeOverrides };
    delete newOverrides[taskType];
    onChange(newOverrides);
  };

  const handleUpdateTaskType = (taskType: string, updates: Partial<TaskModelConfig>) => {
    onChange({
      ...taskTypeOverrides,
      [taskType]: {
        ...taskTypeOverrides[taskType],
        ...updates,
      },
    });
  };

  return (
    <div className="task-type-config">
      <div className="section-header">
        <h3>Task-Type Configuration</h3>
        <div className="add-task-type">
          <select
            value={newTaskType}
            onChange={(e) => setNewTaskType(e.target.value)}
          >
            <option value="">Select task type...</option>
            {COMMON_TASK_TYPES.filter((type) => !taskTypeOverrides[type]).map((type) => (
              <option key={type} value={type}>
                {type.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
          <button
            onClick={() => handleAddTaskType(newTaskType)}
            disabled={!newTaskType}
            className="add-button"
          >
            Add Override
          </button>
        </div>
      </div>

      {Object.keys(taskTypeOverrides).length === 0 ? (
        <div className="empty-state">
          <p>No task-type overrides configured. Using default routing.</p>
        </div>
      ) : (
        <div className="task-type-table">
          <table>
            <thead>
              <tr>
                <th>Task Type</th>
                <th>Model Override</th>
                <th>Strategy</th>
                <th>Local OK</th>
                <th>Paid OK</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(taskTypeOverrides).map(([taskType, config]) => (
                <tr key={taskType}>
                  <td className="task-type-name">{taskType.replace(/_/g, ' ')}</td>
                  <td>
                    <select
                      value={config.model_override || ''}
                      onChange={(e) =>
                        handleUpdateTaskType(taskType, {
                          model_override: e.target.value || undefined,
                        })
                      }
                    >
                      <option value="">Auto</option>
                      {AVAILABLE_MODELS.map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <select
                      value={config.strategy_override || ''}
                      onChange={(e) =>
                        handleUpdateTaskType(taskType, {
                          strategy_override: e.target.value || undefined,
                        })
                      }
                    >
                      <option value="">Default</option>
                      {STRATEGIES.map((strategy) => (
                        <option key={strategy} value={strategy}>
                          {strategy.replace(/_/g, ' ')}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={config.allow_local}
                      onChange={(e) =>
                        handleUpdateTaskType(taskType, { allow_local: e.target.checked })
                      }
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={config.allow_paid}
                      onChange={(e) =>
                        handleUpdateTaskType(taskType, { allow_paid: e.target.checked })
                      }
                    />
                  </td>
                  <td>
                    <button
                      className="remove-button"
                      onClick={() => handleRemoveTaskType(taskType)}
                    >
                      <Trash2 size={16} />
                    </button>
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
