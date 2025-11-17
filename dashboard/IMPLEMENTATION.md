# Web Dashboard Implementation

## Overview

The Insanity Cluster web dashboard is a React-based single-page application that provides real-time monitoring, metrics visualization, and configuration management for the AI orchestration system.

## Implementation Status

✅ **Task 8.1: Set up frontend framework** - COMPLETED
- React 18 with TypeScript
- Vite build system
- WebSocket client (Socket.IO)
- REST API client
- Docker deployment configuration

✅ **Task 8.2: Create task monitoring interface** - COMPLETED
- Task list view with real-time updates
- Task detail panel with subtask breakdown
- Active agent display
- Task cancellation functionality
- Progress tracking with WebSocket streaming

✅ **Task 8.3: Build cost and metrics dashboard** - COMPLETED
- Cost metrics display (total spend, daily spend, cost per task)
- System metrics (completion rate, error rate, active tasks, queue depth)
- Latency charts (p50, p95, p99, average)
- Task history viewer
- Auto-refresh functionality

✅ **Task 8.4: Implement configuration management UI** - COMPLETED
- Operating mode selection (Local, OpenRouter Free, Mixed, Web, OpenRouter Paid)
- Routing strategy configuration
- Cost limits and thresholds
- Agent-specific model configuration
- Task-type overrides
- Model provider management

## Architecture

### Technology Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite 7
- **WebSocket**: Socket.IO Client
- **Charts**: Recharts
- **Icons**: Lucide React
- **Styling**: CSS Modules with CSS Variables

### Project Structure

```
dashboard/
├── src/
│   ├── components/
│   │   ├── tasks/           # Task monitoring components
│   │   │   ├── TaskMonitor.tsx
│   │   │   ├── TaskList.tsx
│   │   │   ├── TaskItem.tsx
│   │   │   └── TaskDetail.tsx
│   │   ├── metrics/         # Metrics dashboard components
│   │   │   ├── MetricsDashboard.tsx
│   │   │   ├── CostMetrics.tsx
│   │   │   ├── SystemMetrics.tsx
│   │   │   ├── LatencyMetrics.tsx
│   │   │   └── TaskHistory.tsx
│   │   └── config/          # Configuration UI components
│   │       ├── ConfigManager.tsx
│   │       ├── ModeSelector.tsx
│   │       ├── AgentConfig.tsx
│   │       ├── TaskTypeConfig.tsx
│   │       └── ProviderConfig.tsx
│   ├── lib/
│   │   ├── api.ts           # REST API client
│   │   └── websocket.ts     # WebSocket client
│   ├── types/
│   │   └── index.ts         # TypeScript type definitions
│   ├── App.tsx              # Main application component
│   └── main.tsx             # Application entry point
├── public/                  # Static assets
├── Dockerfile               # Docker build configuration
├── nginx.conf               # Nginx configuration for production
└── package.json
```

## Features

### 1. Task Monitoring

**Components**: TaskMonitor, TaskList, TaskItem, TaskDetail

**Features**:
- Real-time task list with status indicators
- Click to view detailed task information
- Subtask breakdown with agent assignments
- Active agent display with current operations
- Task cancellation for running tasks
- Progress bars with percentage completion
- Cost and latency metrics per task
- WebSocket integration for live updates

**Status Indicators**:
- 🟢 Completed (green)
- 🔴 Failed (red)
- 🔵 Running (blue, animated)
- 🟡 Cancelled (yellow)
- ⚪ Pending (gray)

### 2. Metrics Dashboard

**Components**: MetricsDashboard, CostMetrics, SystemMetrics, LatencyMetrics, TaskHistory

**Features**:
- **Cost Metrics**:
  - Total spend across all tasks
  - Daily spend tracking
  - Average cost per task
  - Total task count

- **System Metrics**:
  - Task completion rate (%)
  - Error rate (%)
  - Active tasks count
  - Queue depth

- **Latency Metrics**:
  - Average latency
  - P50, P95, P99 percentiles
  - Visual bar chart
  - Real-time updates

- **Task History**:
  - Recent completed/failed tasks
  - Cost and latency per task
  - Completion timestamps
  - Sortable table view

**Auto-refresh**: Configurable 5-second refresh interval

### 3. Configuration Management

**Components**: ConfigManager, ModeSelector, AgentConfig, TaskTypeConfig, ProviderConfig

**Features**:
- **Operating Mode Selection**:
  - Local (💰 Free) - Only local models
  - OpenRouter Free (💰 Free) - Free tier models
  - Mixed (💰💰 Balanced) - Hybrid local + paid
  - Web (💰💰💰💰 Premium) - Premium paid models
  - OpenRouter Paid (💰💰💰 Paid) - Unified billing

- **Routing Strategies**:
  - Speed First - Prioritize fast responses
  - Quality First - Prioritize best quality
  - Cost Optimized - Minimize costs
  - Task Specific - Optimize per task type

- **Cost Limits**:
  - Max cost per task
  - Max cost per day
  - Local complexity threshold (Mixed mode)

- **Agent Configuration**:
  - Per-agent model preferences
  - Fallback model chains
  - Max cost per agent
  - Fallback to paid models toggle

- **Task-Type Overrides**:
  - Model override per task type
  - Strategy override per task type
  - Allow/disallow local models
  - Allow/disallow paid models

- **Provider Management**:
  - Enable/disable providers
  - API key configuration
  - Endpoint configuration (local models)
  - Connection testing
  - Available models display

## API Integration

### REST API Endpoints

The dashboard connects to the backend API at `http://localhost:8000` (configurable):

- `POST /tasks` - Create new task
- `GET /tasks` - List tasks
- `GET /tasks/{task_id}` - Get task details
- `GET /tasks/{task_id}/status` - Get task status
- `POST /tasks/{task_id}/cancel` - Cancel task
- `GET /metrics/cost` - Get cost metrics
- `GET /metrics/latency` - Get latency metrics
- `GET /metrics/system` - Get system metrics
- `GET /config` - Get configuration
- `PUT /config` - Update configuration

### WebSocket Events

The dashboard listens for real-time events:

- `task_update` - Task progress updates
  ```typescript
  {
    task_id: string;
    status: string;
    progress: number;
    message?: string;
    agent?: string;
    subtask?: string;
    timestamp: string;
  }
  ```

- `system_event` - System notifications
  ```typescript
  {
    type: string;
    message: string;
    severity: 'info' | 'warning' | 'error';
    timestamp: string;
  }
  ```

## Deployment

### Development

```bash
cd dashboard
npm install
npm run dev
```

Dashboard available at `http://localhost:5173`

### Production Build

```bash
npm run build
```

Outputs to `dist/` directory

### Docker Deployment

```bash
docker build -t insanity-cluster-dashboard ./dashboard
docker run -p 3001:80 insanity-cluster-dashboard
```

Or use docker-compose:

```bash
docker-compose up dashboard
```

Dashboard available at `http://localhost:3001`

### Environment Variables

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=http://localhost:8000
```

## Design System

### Color Palette

- **Primary**: `#646cff` (blue)
- **Success**: `#4ade80` (green)
- **Error**: `#f87171` (red)
- **Warning**: `#fbbf24` (yellow)
- **Background Dark**: `#1a1a1a`
- **Background Light**: `#242424`
- **Text Primary**: `rgba(255, 255, 255, 0.87)`
- **Text Secondary**: `rgba(255, 255, 255, 0.6)`
- **Border**: `rgba(255, 255, 255, 0.1)`

### Typography

- **Font Family**: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif
- **Headings**: 600 weight
- **Body**: 400 weight
- **Small Text**: 0.75rem - 0.875rem
- **Regular Text**: 0.875rem - 1rem
- **Large Text**: 1.25rem - 1.5rem

### Spacing

- **Small**: 0.5rem (8px)
- **Medium**: 1rem (16px)
- **Large**: 1.5rem (24px)
- **XLarge**: 2rem (32px)

### Components

- **Border Radius**: 0.375rem - 0.5rem
- **Transitions**: 0.2s ease
- **Shadows**: Subtle with primary color
- **Hover States**: Slight background change + border color

## Performance Optimizations

1. **Code Splitting**: Consider implementing dynamic imports for routes
2. **Memoization**: Use React.memo for expensive components
3. **Virtual Scrolling**: For large task lists (future enhancement)
4. **Debouncing**: For search and filter inputs
5. **WebSocket Throttling**: Limit update frequency for high-volume events

## Accessibility

- Semantic HTML elements
- ARIA labels where needed
- Keyboard navigation support
- Focus indicators
- Color contrast compliance
- Screen reader friendly

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Modern mobile browsers

## Future Enhancements

1. **Authentication UI**: Login/logout, user profile
2. **Dark/Light Theme Toggle**: User preference
3. **Advanced Filtering**: Filter tasks by status, date, cost
4. **Export Functionality**: Export metrics to CSV/JSON
5. **Notifications**: Browser notifications for task completion
6. **Mobile Optimization**: Responsive design improvements
7. **Internationalization**: Multi-language support
8. **Custom Dashboards**: User-configurable layouts
9. **Real-time Logs**: Stream task execution logs
10. **Performance Profiling**: Detailed performance analysis

## Testing

### Unit Tests

```bash
npm run test
```

### E2E Tests

```bash
npm run test:e2e
```

### Build Verification

```bash
npm run build
npm run preview
```

## Troubleshooting

### WebSocket Connection Issues

- Verify backend is running on correct port
- Check CORS configuration
- Ensure WebSocket endpoint is accessible
- Check browser console for errors

### API Connection Issues

- Verify API_URL environment variable
- Check network tab for failed requests
- Ensure backend API is running
- Verify authentication tokens

### Build Issues

- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Clear Vite cache: `rm -rf node_modules/.vite`
- Check TypeScript errors: `npm run type-check`

## Contributing

When adding new features:

1. Follow existing component structure
2. Use TypeScript for type safety
3. Add CSS modules for styling
4. Update this documentation
5. Test in development mode
6. Verify production build

## License

Part of the Insanity Cluster project.
