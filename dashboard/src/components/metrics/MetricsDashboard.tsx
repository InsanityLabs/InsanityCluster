import { useState, useEffect } from 'react';
import { apiClient } from '../../lib/api';
import CostMetrics from './CostMetrics';
import LatencyMetrics from './LatencyMetrics';
import SystemMetrics from './SystemMetrics';
import TaskHistory from './TaskHistory';
import type { MetricsData } from '../../types';
import './MetricsDashboard.css';

export default function MetricsDashboard() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    loadMetrics();

    if (autoRefresh) {
      const interval = setInterval(loadMetrics, 5000); // Refresh every 5 seconds
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const loadMetrics = async () => {
    try {
      const [cost, latency, system] = await Promise.all([
        apiClient.getCostMetrics(),
        apiClient.getLatencyMetrics(),
        apiClient.getSystemMetrics(),
      ]);

      setMetrics({ cost, latency, system });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load metrics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="metrics-loading">
        <div className="spinner" />
        <p>Loading metrics...</p>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="metrics-error">
        <p>Error: {error || 'Failed to load metrics'}</p>
        <button onClick={loadMetrics}>Retry</button>
      </div>
    );
  }

  return (
    <div className="metrics-dashboard">
      <div className="metrics-header">
        <h2>Cost & Metrics Dashboard</h2>
        <div className="metrics-controls">
          <label className="auto-refresh-toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (5s)
          </label>
          <button onClick={loadMetrics} className="refresh-button">
            Refresh Now
          </button>
        </div>
      </div>

      <div className="metrics-grid">
        <CostMetrics data={metrics.cost} />
        <SystemMetrics data={metrics.system} />
      </div>

      <div className="metrics-charts">
        <LatencyMetrics data={metrics.latency} />
      </div>

      <div className="metrics-history">
        <TaskHistory />
      </div>
    </div>
  );
}
