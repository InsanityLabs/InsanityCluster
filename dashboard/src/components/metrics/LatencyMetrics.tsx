import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './LatencyMetrics.css';

interface LatencyMetricsProps {
  data: {
    p50: number;
    p95: number;
    p99: number;
    avg: number;
  };
}

export default function LatencyMetrics({ data }: LatencyMetricsProps) {
  const chartData = [
    { name: 'Average', value: data.avg },
    { name: 'P50', value: data.p50 },
    { name: 'P95', value: data.p95 },
    { name: 'P99', value: data.p99 },
  ];

  return (
    <div className="latency-metrics">
      <h3>Latency Metrics (ms)</h3>
      <div className="latency-stats">
        <div className="latency-stat">
          <span className="stat-label">Average</span>
          <span className="stat-value">{data.avg.toFixed(0)}ms</span>
        </div>
        <div className="latency-stat">
          <span className="stat-label">P50</span>
          <span className="stat-value">{data.p50.toFixed(0)}ms</span>
        </div>
        <div className="latency-stat">
          <span className="stat-label">P95</span>
          <span className="stat-value">{data.p95.toFixed(0)}ms</span>
        </div>
        <div className="latency-stat">
          <span className="stat-label">P99</span>
          <span className="stat-value">{data.p99.toFixed(0)}ms</span>
        </div>
      </div>
      <div className="latency-chart">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
            <XAxis dataKey="name" stroke="rgba(255, 255, 255, 0.6)" />
            <YAxis stroke="rgba(255, 255, 255, 0.6)" />
            <Tooltip
              contentStyle={{
                backgroundColor: '#242424',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '0.375rem',
              }}
            />
            <Legend />
            <Bar dataKey="value" fill="#646cff" name="Latency (ms)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
