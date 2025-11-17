import type { ModelConfig } from '../../types';
import './ModeSelector.css';

interface ModeSelectorProps {
  mode: ModelConfig['mode'];
  defaultStrategy: ModelConfig['default_strategy'];
  maxCostPerTask?: number;
  maxCostPerDay?: number;
  localComplexityThreshold?: number;
  onChange: (updates: Partial<ModelConfig>) => void;
}

const MODES = [
  { value: 'LOCAL', label: 'Local', cost: '💰 Free', description: 'Only local models' },
  { value: 'OPENROUTER_FREE', label: 'OpenRouter Free', cost: '💰 Free', description: 'Free tier models' },
  { value: 'MIXED', label: 'Mixed', cost: '💰💰 Balanced', description: 'Hybrid local + paid' },
  { value: 'WEB', label: 'Web', cost: '💰💰💰💰 Premium', description: 'Premium paid models' },
  { value: 'OPENROUTER_PAID', label: 'OpenRouter Paid', cost: '💰💰💰 Paid', description: 'Unified billing' },
] as const;

const STRATEGIES = [
  { value: 'SPEED_FIRST', label: 'Speed First', description: 'Prioritize fast responses' },
  { value: 'QUALITY_FIRST', label: 'Quality First', description: 'Prioritize best quality' },
  { value: 'COST_OPTIMIZED', label: 'Cost Optimized', description: 'Minimize costs' },
  { value: 'TASK_SPECIFIC', label: 'Task Specific', description: 'Optimize per task type' },
] as const;

export default function ModeSelector({
  mode,
  defaultStrategy,
  maxCostPerTask,
  maxCostPerDay,
  localComplexityThreshold,
  onChange,
}: ModeSelectorProps) {
  return (
    <div className="mode-selector">
      <h3>Operating Mode</h3>

      <div className="mode-buttons">
        {MODES.map((m) => (
          <button
            key={m.value}
            className={`mode-button ${mode === m.value ? 'active' : ''}`}
            onClick={() => onChange({ mode: m.value })}
          >
            <div className="mode-label">{m.label}</div>
            <div className="mode-cost">{m.cost}</div>
            <div className="mode-description">{m.description}</div>
          </button>
        ))}
      </div>

      <div className="strategy-section">
        <h4>Routing Strategy</h4>
        <div className="strategy-buttons">
          {STRATEGIES.map((s) => (
            <button
              key={s.value}
              className={`strategy-button ${defaultStrategy === s.value ? 'active' : ''}`}
              onClick={() => onChange({ default_strategy: s.value })}
            >
              <div className="strategy-label">{s.label}</div>
              <div className="strategy-description">{s.description}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="cost-limits">
        <h4>Cost Limits</h4>
        <div className="limit-inputs">
          <div className="input-group">
            <label>Max Cost per Task ($)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={maxCostPerTask || ''}
              onChange={(e) =>
                onChange({ max_cost_per_task: e.target.value ? parseFloat(e.target.value) : undefined })
              }
              placeholder="No limit"
            />
          </div>
          <div className="input-group">
            <label>Max Cost per Day ($)</label>
            <input
              type="number"
              step="1"
              min="0"
              value={maxCostPerDay || ''}
              onChange={(e) =>
                onChange({ max_cost_per_day: e.target.value ? parseFloat(e.target.value) : undefined })
              }
              placeholder="No limit"
            />
          </div>
        </div>
      </div>

      {mode === 'MIXED' && (
        <div className="mixed-mode-settings">
          <h4>Mixed Mode Settings</h4>
          <div className="input-group">
            <label>
              Local Complexity Threshold: {(localComplexityThreshold || 0.5).toFixed(2)}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={localComplexityThreshold || 0.5}
              onChange={(e) =>
                onChange({ local_complexity_threshold: parseFloat(e.target.value) })
              }
            />
            <div className="threshold-hint">
              Tasks below this complexity use local models
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
