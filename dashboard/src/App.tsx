import { useState, useEffect } from 'react';
import { wsClient } from './lib/websocket';
import TaskMonitor from './components/tasks/TaskMonitor';
import MetricsDashboard from './components/metrics/MetricsDashboard';
import ConfigManager from './components/config/ConfigManager';
import './App.css';

function App() {
  const [connected, setConnected] = useState(false);
  const [activeView, setActiveView] = useState<'tasks' | 'metrics' | 'config'>('tasks');

  useEffect(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || 'http://localhost:8000';
    const socket = wsClient.connect(wsUrl);

    socket.on('connect', () => {
      setConnected(true);
    });

    socket.on('disconnect', () => {
      setConnected(false);
    });

    return () => {
      wsClient.disconnect();
    };
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Insanity Cluster Dashboard</h1>
        <div className="connection-status">
          <span className={`status-indicator ${connected ? 'connected' : 'disconnected'}`} />
          {connected ? 'Connected' : 'Disconnected'}
        </div>
      </header>

      <nav className="app-nav">
        <button
          className={activeView === 'tasks' ? 'active' : ''}
          onClick={() => setActiveView('tasks')}
        >
          Tasks
        </button>
        <button
          className={activeView === 'metrics' ? 'active' : ''}
          onClick={() => setActiveView('metrics')}
        >
          Metrics
        </button>
        <button
          className={activeView === 'config' ? 'active' : ''}
          onClick={() => setActiveView('config')}
        >
          Configuration
        </button>
      </nav>

      <main className="app-main">
        {activeView === 'tasks' && <TaskMonitor />}
        {activeView === 'metrics' && <MetricsDashboard />}
        {activeView === 'config' && <ConfigManager />}
      </main>
    </div>
  );
}

export default App;
