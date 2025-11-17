import { useState, useEffect } from 'react';
import { apiClient } from '../../lib/api';
import ModeSelector from './ModeSelector';
import AgentConfig from './AgentConfig';
import TaskTypeConfig from './TaskTypeConfig';
import ProviderConfig from './ProviderConfig';
import type { ModelConfig } from '../../types';
import './ConfigManager.css';

export default function ConfigManager() {
  const [config, setConfig] = useState<ModelConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getConfiguration();
      setConfig(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;

    try {
      setSaving(true);
      await apiClient.updateConfiguration(config);
      setSuccessMessage('Configuration saved successfully');
      setTimeout(() => setSuccessMessage(null), 3000);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleConfigChange = (updates: Partial<ModelConfig>) => {
    if (config) {
      setConfig({ ...config, ...updates });
    }
  };

  if (loading) {
    return (
      <div className="config-loading">
        <div className="spinner" />
        <p>Loading configuration...</p>
      </div>
    );
  }

  if (error && !config) {
    return (
      <div className="config-error">
        <p>Error: {error}</p>
        <button onClick={loadConfig}>Retry</button>
      </div>
    );
  }

  if (!config) {
    return null;
  }

  return (
    <div className="config-manager">
      <div className="config-header">
        <h2>Configuration Management</h2>
        <div className="config-actions">
          <button onClick={loadConfig} className="reset-button" disabled={saving}>
            Reset
          </button>
          <button onClick={handleSave} className="save-button" disabled={saving}>
            {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </div>

      {successMessage && (
        <div className="success-message">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="config-sections">
        <ModeSelector
          mode={config.mode}
          defaultStrategy={config.default_strategy}
          maxCostPerTask={config.max_cost_per_task}
          maxCostPerDay={config.max_cost_per_day}
          localComplexityThreshold={config.local_complexity_threshold}
          onChange={handleConfigChange}
        />

        <AgentConfig
          agentOverrides={config.agent_overrides || {}}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onChange={(agent_overrides: Record<string, any>) => handleConfigChange({ agent_overrides })}
        />

        <TaskTypeConfig
          taskTypeOverrides={config.task_type_overrides || {}}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onChange={(task_type_overrides: Record<string, any>) => handleConfigChange({ task_type_overrides })}
        />

        <ProviderConfig />
      </div>
    </div>
  );
}
