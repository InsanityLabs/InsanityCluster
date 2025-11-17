# Insanity Cluster Dashboard

Web dashboard for monitoring and managing the Insanity Cluster AI orchestration system.

## Features

- **Task Monitoring**: Real-time task status, progress tracking, and agent activity
- **Metrics Dashboard**: Cost tracking, latency metrics, and system performance
- **Configuration Management**: Operating mode selection, model configuration, and routing strategies
- **WebSocket Integration**: Real-time updates for task progress and system events

## Technology Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **WebSocket**: Socket.IO Client
- **Charts**: Recharts
- **Icons**: Lucide React

## Getting Started

### Prerequisites

- Node.js 20+
- npm or yarn

### Installation

```bash
npm install
```

### Development

```bash
npm run dev
```

The dashboard will be available at `http://localhost:5173`

### Build

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Environment Variables

Create a `.env` file in the dashboard directory:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=http://localhost:8000
```

## Project Structure

```
dashboard/
├── src/
│   ├── components/       # React components
│   │   ├── tasks/       # Task monitoring components
│   │   ├── metrics/     # Metrics dashboard components
│   │   └── config/      # Configuration UI components
│   ├── lib/             # Utilities and clients
│   │   ├── api.ts       # REST API client
│   │   └── websocket.ts # WebSocket client
│   ├── types/           # TypeScript type definitions
│   ├── App.tsx          # Main application component
│   └── main.tsx         # Application entry point
├── public/              # Static assets
└── package.json
```

## API Integration

The dashboard connects to the Insanity Cluster backend API:

- **REST API**: `http://localhost:8000` (configurable via `VITE_API_URL`)
- **WebSocket**: `http://localhost:8000` (configurable via `VITE_WS_URL`)

### Authentication

The dashboard uses JWT tokens for authentication. Set the token using:

```typescript
import { apiClient } from './lib/api';

apiClient.setToken('your-jwt-token');
```

## WebSocket Events

The dashboard listens for the following WebSocket events:

- `task_update`: Real-time task progress updates
- `system_event`: System notifications and alerts

## Development Guidelines

### Code Style

- Use TypeScript for type safety
- Follow React best practices and hooks patterns
- Use functional components with hooks
- Keep components small and focused

### Component Organization

- Place reusable components in `src/components/`
- Group related components by feature
- Use index files for clean imports

### State Management

- Use React hooks (useState, useEffect, useContext) for local state
- Consider adding a state management library (Redux, Zustand) for complex state

## Testing

```bash
npm run test
```

## Deployment

The dashboard can be deployed as static files:

1. Build the production bundle: `npm run build`
2. Deploy the `dist/` directory to your hosting service
3. Configure environment variables for production API endpoints

### Docker Deployment

A Dockerfile is provided for containerized deployment:

```bash
docker build -t insanity-cluster-dashboard .
docker run -p 80:80 insanity-cluster-dashboard
```

## License

Part of the Insanity Cluster project.
