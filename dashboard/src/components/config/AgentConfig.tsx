import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import type { AgentModelConfig } from '../../types';
import './AgentConfig.css';

interface AgentConfigProps {
  agentOverrides: Record<string, AgentModelConfig>;
  onChange: (overrides: Record<string, AgentModelConfig>) => void;
}

const AGENT_TYPES = [
  'Developer',
  'Communication',
  'Business',
  'Research',
  'Creative',
  'Finance',
  'ProjectManager',
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

export default function AgentConfig({ agentOverrides, onChange }: AgentConfigProps) {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  const handleAddAgent = (agentType: string) => {
    onChange({
      ...agentOverrides,
      [agentType]: {
        preferred_models: [],
        fallback_to_paid: true,
        max_cost: undefined,
      },
    });
    setExpandedAgent(agentType);
  };

  const handleRemoveAgent = (agentType: string) => {
    const newOverrides = { ...agentOverrides };
    delete newOverrides[agentType];
    onChange(newOverrides);
    if (expandedAgent === agentType) {
      setExpandedAgent(null);
    }
  };

  const handleUpdateAgent = (agentType: string, updates: Partial<AgentModelConfig>) => {
    onChange({
      ...agentOverrides,
      [agentType]: {
        ...agentOverrides[agentType],
        ...updates,
      },
    });
  };

  const handleAddModel = (agentType: string, model: string) => {
    const agent = agentOverrides[agentType];
    if (!agent.preferred_models.includes(model)) {
      handleUpdateAgent(agentType, {
        preferred_models: [...agent.preferred_models, model],
      });
    }
  };

  const handleRemoveModel = (agentType: string, model: string) => {
    const agent = agentOverrides[agentType];
    handleUpdateAgent(agentType, {
      preferred_models: agent.preferred_models.filter((m) => m !== model),
    });
  };

  return (
    <div className="agent-config">
      <div className="section-header">
        <h3>Agent-Specific Configuration</h3>
        <div className="add-agent-dropdown">
          <select
            onChange={(e) => {
              if (e.target.value) {
                handleAddAgent(e.target.value);
                e.target.value = '';
              }
            }}
            value=""
          >
            <option value="">Add Agent Override...</option>
            {AGENT_TYPES.filter((type) => !agentOverrides[type]).map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>
      </div>

      {Object.keys(agentOverrides).length === 0 ? (
        <div className="empty-state">
          <p>No agent overrides configured. Using default settings.</p>
        </div>
      ) : (
        <div className="agent-list">
          {Object.entries(agentOverrides).map(([agentType, config]) => (
            <div key={agentType} className="agent-item">
              <div
                className="agent-header"
                onClick={() => setExpandedAgent(expandedAgent === agentType ? null : agentType)}
              >
                <h4>{agentType} Agent</h4>
                <button
                  className="remove-button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveAgent(agentType);
                  }}
                >
                  <Trash2 size={16} />
                </button>
              </div>

              {expandedAgent === agentType && (
                <div className="agent-details">
                  <div className="model-selection">
                    <label>Preferred Models (in order)</label>
                    <div className="model-list">
                      {config.preferred_models.map((model, index) => (
                        <div key={index} className="model-chip">
                          <span>{model}</span>
                          <button onClick={() => handleRemoveModel(agentType, model)}>×</button>
                        </div>
                      ))}
                    </div>
                    <select
                      onChange={(e) => {
                        if (e.target.value) {
                          handleAddModel(agentType, e.target.value);
                          e.target.value = '';
                        }
                      }}
                      value=""
                    >
                      <option value="">Add model...</option>
                      {AVAILABLE_MODELS.filter(
                        (m) => !config.preferred_models.includes(m)
                      ).map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="agent-options">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={config.fallback_to_paid}
                        onChange={(e) =>
                          handleUpdateAgent(agentType, { fallback_to_paid: e.target.checked })
                        }
                      />
                      Fallback to paid models if local fails
                    </label>

                    <div className="input-group">
                      <label>Max Cost per Task ($)</label>
                      <input
                        type="number"
                        step="0.01"
                        min="0"
                        value={config.max_cost || ''}
                        onChange={(e) =>
                          handleUpdateAgent(agentType, {
                            max_cost: e.target.value ? parseFloat(e.target.value) : undefined,
                          })
                        }
                        placeholder="No limit"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
