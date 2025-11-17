#!/usr/bin/env python3
"""
Example Web Integration using Insanity Cluster

This example demonstrates how to integrate Insanity Cluster into a web application
using Flask and WebSockets for real-time updates.

Usage:
    pip install flask flask-socketio python-socketio
    python web_integration_example.py
    
Then open http://localhost:5000 in your browser.
"""

from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit
import asyncio
import httpx
from threading import Thread
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Insanity Cluster configuration
INSANITY_CLUSTER_API_KEY = "ic_test_demo"
INSANITY_CLUSTER_BASE_URL = "http://localhost:8000/v1"

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Insanity Cluster Web Integration</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 30px;
        }
        .input-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input[type="text"], textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 5px;
            display: none;
        }
        .status.info {
            background-color: #e3f2fd;
            border-left: 4px solid #2196F3;
            display: block;
        }
        .status.success {
            background-color: #e8f5e9;
            border-left: 4px solid #4CAF50;
            display: block;
        }
        .status.error {
            background-color: #ffebee;
            border-left: 4px solid #f44336;
            display: block;
        }
        .progress {
            margin-top: 20px;
            display: none;
        }
        .progress.active {
            display: block;
        }
        .progress-bar {
            width: 100%;
            height: 30px;
            background-color: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background-color: #4CAF50;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 5px;
            display: none;
        }
        .result.active {
            display: block;
        }
        .result pre {
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        .metric {
            background-color: white;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
        }
        .metric-label {
            font-size: 12px;
            color: #888;
            text-transform: uppercase;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Insanity Cluster Web Integration</h1>
        
        <div class="input-group">
            <label for="command">Command:</label>
            <textarea id="command" placeholder="Enter your command here, e.g., 'Write a Python function to calculate fibonacci numbers'"></textarea>
        </div>
        
        <div class="input-group">
            <label for="priority">Priority:</label>
            <select id="priority" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                <option value="low">Low</option>
                <option value="normal" selected>Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
            </select>
        </div>
        
        <button id="submitBtn" onclick="submitTask()">Execute Task</button>
        
        <div id="status" class="status"></div>
        
        <div id="progress" class="progress">
            <div class="progress-bar">
                <div id="progressFill" class="progress-fill" style="width: 0%">0%</div>
            </div>
            <div id="progressText" style="margin-top: 10px; color: #666;"></div>
        </div>
        
        <div id="result" class="result">
            <h3>Result:</h3>
            <pre id="resultContent"></pre>
            
            <h3>Metrics:</h3>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">Cost</div>
                    <div class="metric-value" id="metricCost">$0.00</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Latency</div>
                    <div class="metric-value" id="metricLatency">0ms</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Models Used</div>
                    <div class="metric-value" id="metricModels">-</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const socket = io();
        let currentTaskId = null;
        
        socket.on('connect', function() {
            console.log('Connected to server');
        });
        
        socket.on('task_update', function(data) {
            console.log('Task update:', data);
            updateProgress(data);
        });
        
        socket.on('task_completed', function(data) {
            console.log('Task completed:', data);
            showResult(data);
        });
        
        socket.on('task_failed', function(data) {
            console.log('Task failed:', data);
            showError(data.error);
        });
        
        function submitTask() {
            const command = document.getElementById('command').value;
            const priority = document.getElementById('priority').value;
            
            if (!command.trim()) {
                showStatus('Please enter a command', 'error');
                return;
            }
            
            // Disable button
            document.getElementById('submitBtn').disabled = true;
            
            // Reset UI
            document.getElementById('result').classList.remove('active');
            document.getElementById('progress').classList.add('active');
            document.getElementById('progressFill').style.width = '0%';
            document.getElementById('progressFill').textContent = '0%';
            
            // Show status
            showStatus('Creating task...', 'info');
            
            // Submit task
            fetch('/api/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    command: command,
                    priority: priority
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                    document.getElementById('submitBtn').disabled = false;
                } else {
                    currentTaskId = data.task_id;
                    showStatus(`Task created: ${data.task_id}`, 'info');
                    socket.emit('subscribe', {task_id: data.task_id});
                }
            })
            .catch(error => {
                showError(error.message);
                document.getElementById('submitBtn').disabled = false;
            });
        }
        
        function updateProgress(data) {
            const progress = data.progress || {};
            const percentage = progress.percentage || 0;
            
            document.getElementById('progressFill').style.width = percentage + '%';
            document.getElementById('progressFill').textContent = Math.round(percentage) + '%';
            
            const activeAgents = data.active_agents || [];
            const agentText = activeAgents.length > 0 ? 
                `Active agents: ${activeAgents.join(', ')}` : 
                'Processing...';
            document.getElementById('progressText').textContent = agentText;
            
            showStatus(`Status: ${data.status} (${Math.round(percentage)}%)`, 'info');
        }
        
        function showResult(data) {
            document.getElementById('progress').classList.remove('active');
            document.getElementById('result').classList.add('active');
            document.getElementById('submitBtn').disabled = false;
            
            // Show result
            const resultContent = JSON.stringify(data.result, null, 2);
            document.getElementById('resultContent').textContent = resultContent;
            
            // Show metrics
            const metrics = data.metrics || {};
            document.getElementById('metricCost').textContent = '$' + (metrics.total_cost || 0).toFixed(4);
            document.getElementById('metricLatency').textContent = (metrics.total_latency_ms || 0) + 'ms';
            document.getElementById('metricModels').textContent = (metrics.models_used || []).join(', ') || '-';
            
            showStatus('Task completed successfully!', 'success');
        }
        
        function showError(message) {
            document.getElementById('progress').classList.remove('active');
            document.getElementById('submitBtn').disabled = false;
            showStatus('Error: ' + message, 'error');
        }
        
        function showStatus(message, type) {
            const statusEl = document.getElementById('status');
            statusEl.textContent = message;
            statusEl.className = 'status ' + type;
        }
    </script>
</body>
</html>
"""


class InsanityClusterClient:
    """Async client for Insanity Cluster API"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
    
    async def create_task(self, command: str, priority: str = "normal") -> dict:
        """Create a new task"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/tasks",
                headers={"X-API-Key": self.api_key},
                json={"command": command, "priority": priority},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_task_status(self, task_id: str) -> dict:
        """Get task status"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/tasks/{task_id}",
                headers={"X-API-Key": self.api_key},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    async def get_task_result(self, task_id: str) -> dict:
        """Get task result"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/tasks/{task_id}/result",
                headers={"X-API-Key": self.api_key},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()


# Initialize client
ic_client = InsanityClusterClient(
    INSANITY_CLUSTER_API_KEY,
    INSANITY_CLUSTER_BASE_URL
)


@app.route('/')
def index():
    """Render main page"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    try:
        data = request.json
        command = data.get('command')
        priority = data.get('priority', 'normal')
        
        if not command:
            return jsonify({'error': 'Command is required'}), 400
        
        # Create task asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(ic_client.create_task(command, priority))
        loop.close()
        
        # Start monitoring task in background
        task_id = result['task_id']
        thread = Thread(target=monitor_task, args=(task_id,))
        thread.daemon = True
        thread.start()
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def monitor_task(task_id: str):
    """Monitor task progress and emit updates via WebSocket"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        while True:
            # Get task status
            status = loop.run_until_complete(ic_client.get_task_status(task_id))
            
            # Emit update
            socketio.emit('task_update', status)
            
            # Check if complete
            if status['status'] in ['completed', 'failed', 'cancelled']:
                if status['status'] == 'completed':
                    # Get full result
                    result = loop.run_until_complete(ic_client.get_task_result(task_id))
                    socketio.emit('task_completed', result)
                elif status['status'] == 'failed':
                    socketio.emit('task_failed', {'error': status.get('error', 'Unknown error')})
                break
            
            # Wait before next poll
            loop.run_until_complete(asyncio.sleep(2))
    
    except Exception as e:
        socketio.emit('task_failed', {'error': str(e)})
    
    finally:
        loop.close()


@socketio.on('subscribe')
def handle_subscribe(data):
    """Handle task subscription"""
    task_id = data.get('task_id')
    print(f"Client subscribed to task: {task_id}")


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')


if __name__ == '__main__':
    print("Starting Insanity Cluster Web Integration Example")
    print("Open http://localhost:5000 in your browser")
    socketio.run(app, debug=True, port=5000)
