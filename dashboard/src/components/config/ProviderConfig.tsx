import { useState } from 'react';
import { CheckCircle, XCircle, Loader } from 'lucide-react';
import './ProviderConfig.css';

interface Provider {
  name: string;
  endpoint?: string;
  apiKey?: string;
  enabled: boolean;
  status?: 'connected' | 'disconnected' | 'testing';
}

export default function ProviderConfig() {
  const [providers, setProviders] = useState<Provider[]>([
    { name: 'OpenAI', enabled: true, status: 'connected' },
    { name: 'Anthropic', enabled: true, status: 'connected' },
    { name: 'OpenRouter', enabled: false, status: 'disconnected' },
    { name: 'Ollama', endpoint: 'http://localhost:11434', enabled: true, status: 'connected' },
    { name: 'LM Studio', endpoint: 'http://localhost:1234', enabled: false, status: 'disconnected' },
  ]);

  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);

  const handleTestConnection = async (providerName: string) => {
    setProviders((prev) =>
      prev.map((p) =>
        p.name === providerName ? { ...p, status: 'testing' } : p
      )
    );

    // Simulate API test
    setTimeout(() => {
      setProviders((prev) =>
        prev.map((p) =>
          p.name === providerName
            ? { ...p, status: Math.random() > 0.3 ? 'connected' : 'disconnected' }
            : p
        )
      );
    }, 1500);
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="status-icon success" size={16} />;
      case 'disconnected':
        return <XCircle className="status-icon error" size={16} />;
      case 'testing':
        return <Loader className="status-icon testing" size={16} />;
      default:
        return null;
    }
  };

  return (
    <div className="provider-config">
      <h3>Model Provider Configuration</h3>

      <div className="provider-list">
        {providers.map((provider) => (
          <div key={provider.name} className="provider-item">
            <div
              className="provider-header"
              onClick={() =>
                setExpandedProvider(expandedProvider === provider.name ? null : provider.name)
              }
            >
              <div className="provider-info">
                <h4>{provider.name}</h4>
                {getStatusIcon(provider.status)}
              </div>
              <label
                className="provider-toggle"
                onClick={(e) => e.stopPropagation()}
              >
                <input
                  type="checkbox"
                  checked={provider.enabled}
                  onChange={(e) =>
                    setProviders((prev) =>
                      prev.map((p) =>
                        p.name === provider.name ? { ...p, enabled: e.target.checked } : p
                      )
                    )
                  }
                />
                <span className="toggle-slider" />
              </label>
            </div>

            {expandedProvider === provider.name && (
              <div className="provider-details">
                {provider.endpoint && (
                  <div className="input-group">
                    <label>Endpoint</label>
                    <input
                      type="text"
                      value={provider.endpoint}
                      onChange={(e) =>
                        setProviders((prev) =>
                          prev.map((p) =>
                            p.name === provider.name ? { ...p, endpoint: e.target.value } : p
                          )
                        )
                      }
                    />
                  </div>
                )}

                {!provider.endpoint && (
                  <div className="input-group">
                    <label>API Key</label>
                    <input
                      type="password"
                      value={provider.apiKey || ''}
                      onChange={(e) =>
                        setProviders((prev) =>
                          prev.map((p) =>
                            p.name === provider.name ? { ...p, apiKey: e.target.value } : p
                          )
                        )
                      }
                      placeholder="Enter API key..."
                    />
                  </div>
                )}

                <button
                  className="test-button"
                  onClick={() => handleTestConnection(provider.name)}
                  disabled={provider.status === 'testing'}
                >
                  {provider.status === 'testing' ? 'Testing...' : 'Test Connection'}
                </button>

                <div className="provider-models">
                  <label>Available Models</label>
                  <div className="model-tags">
                    {provider.name === 'OpenAI' && (
                      <>
                        <span className="model-tag">gpt-5.1</span>
                        <span className="model-tag">gpt-5</span>
                        <span className="model-tag">gpt-5-mini</span>
                        <span className="model-tag">gpt-5-nano</span>
                        <span className="model-tag">gpt-5-codex</span>
                      </>
                    )}
                    {provider.name === 'Anthropic' && (
                      <>
                        <span className="model-tag">claude-sonnet-4.5</span>
                        <span className="model-tag">claude-haiku-4.5</span>
                        <span className="model-tag">claude-opus-4.1</span>
                      </>
                    )}
                    {provider.name === 'Ollama' && (
                      <>
                        <span className="model-tag">llama3-70b</span>
                        <span className="model-tag">mistral-7b</span>
                        <span className="model-tag">codellama</span>
                        <span className="model-tag">phi-3</span>
                      </>
                    )}
                    {(provider.name === 'OpenRouter' || provider.name === 'LM Studio') && (
                      <span className="model-tag">Various models</span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
