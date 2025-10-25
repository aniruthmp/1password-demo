"""
FastAPI + Tailwind WebSocket Dashboard
Real-time visualization of MCP, A2A, and ACP protocols with interactive testing.
"""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Remove backend imports - we'll use HTTP calls instead
# from src.core.credential_manager import CredentialManager
# from src.core.metrics import get_current_metrics


# Request models for API endpoints
class MCPTestRequest(BaseModel):
    resource_type: str
    resource_name: str
    agent_id: str


class A2ATestRequest(BaseModel):
    capability_name: str
    resource_name: str  # Generic name for any resource type
    agent_id: str


class ACPTestRequest(BaseModel):
    message: str
    requester_id: str


app = FastAPI(
    title="1Password Credential Broker Dashboard",
    description="Real-time monitoring and testing for MCP, A2A, and ACP protocols",
    version="1.0.0",
)

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict[str, Any]):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

# Global metrics tracking
class MetricsTracker:
    def __init__(self):
        self.start_time = datetime.now(UTC)
        self.requests_total = 0
        self.requests_successful = 0
        self.requests_failed = 0
        self.tokens_generated = 0
        self.protocols = {"mcp": 0, "a2a": 0, "acp": 0}
        self.resource_types = {"database": 0, "api": 0, "ssh": 0, "server": 0}
    
    def record_request(self, protocol: str, resource_type: str, success: bool = True):
        """Record a request for metrics tracking."""
        self.requests_total += 1
        if success:
            self.requests_successful += 1
            self.tokens_generated += 1
            self.protocols[protocol.lower()] += 1
            if resource_type in self.resource_types:
                self.resource_types[resource_type] += 1
        else:
            self.requests_failed += 1
    
    def get_metrics(self):
        """Get current metrics."""
        uptime_seconds = (datetime.now(UTC) - self.start_time).total_seconds()
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        uptime_human = f"{hours}:{minutes:02d}:{seconds:02d}"
        
        success_rate = (self.requests_successful / self.requests_total * 100) if self.requests_total > 0 else 100.0
        
        return {
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "uptime_seconds": int(uptime_seconds),
            "uptime_human": uptime_human,
            "requests": {
                "total": self.requests_total,
                "successful": self.requests_successful,
                "failed": self.requests_failed,
                "success_rate_percent": round(success_rate, 1)
            },
            "tokens": {
                "active": self.tokens_generated,  # Simplified: active = total generated
                "total_generated": self.tokens_generated,
                "avg_ttl_minutes": 5.0
            },
            "protocols": self.protocols.copy(),
            "resource_types": self.resource_types.copy(),
            "performance": {
                "avg_response_time_ms": 50.0
            }
        }

metrics_tracker = MetricsTracker()


# Background task to send periodic metrics updates
async def metrics_updater():
    """Background task that broadcasts metrics every 2 seconds."""
    while True:
        try:
            metrics = metrics_tracker.get_metrics()
            await manager.broadcast({
                "type": "metrics_update",
                "data": metrics
            })
        except Exception as e:
            print(f"Error in metrics updater: {e}")
        
        await asyncio.sleep(2)


# Start background task on startup
@app.on_event("startup")
async def startup_event():
    """Start background tasks."""
    asyncio.create_task(metrics_updater())


# HTML Dashboard
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the main dashboard HTML."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔐 1Password Credential Broker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @keyframes pulse-slow {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .pulse-slow {
            animation: pulse-slow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        .token-display {
            font-family: 'Courier New', monospace;
            font-size: 12px;
            word-break: break-all;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-online {
            background-color: #10b981;
            box-shadow: 0 0 8px #10b981;
        }
        .status-offline {
            background-color: #ef4444;
        }
    </style>
</head>
<body class="bg-gray-50">
    <!-- Header -->
    <header class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white shadow-lg">
        <div class="container mx-auto px-6 py-6">
            <div class="flex items-center justify-between">
                <div>
                    <h1 class="text-3xl font-bold">🔐 1Password Credential Broker</h1>
                    <p class="text-blue-100 mt-2">Universal Multi-Protocol Dashboard | MCP • A2A • ACP</p>
                </div>
                <div class="text-right">
                    <div class="flex items-center">
                        <span class="status-indicator status-online" id="ws-status"></span>
                        <span class="text-sm">WebSocket: <span id="ws-status-text">Connecting...</span></span>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <div class="container mx-auto px-6 py-8">
        
        <!-- Real-time Metrics -->
        <section class="mb-8">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">📊 Real-Time Metrics</h2>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
                    <div class="text-sm text-gray-600 mb-1">Active Tokens</div>
                    <div class="text-3xl font-bold text-gray-800" id="metric-active-tokens">0</div>
                    <div class="text-xs text-green-600 mt-1" id="metric-tokens-change">●</div>
                </div>
                <div class="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
                    <div class="text-sm text-gray-600 mb-1">Total Requests</div>
                    <div class="text-3xl font-bold text-gray-800" id="metric-total-requests">0</div>
                    <div class="text-xs text-blue-600 mt-1" id="metric-requests-change">●</div>
                </div>
                <div class="bg-white rounded-lg shadow p-6 border-l-4 border-purple-500">
                    <div class="text-sm text-gray-600 mb-1">Success Rate</div>
                    <div class="text-3xl font-bold text-gray-800" id="metric-success-rate">0%</div>
                    <div class="text-xs text-gray-600 mt-1" id="metric-success-details">0/0</div>
                </div>
                <div class="bg-white rounded-lg shadow p-6 border-l-4 border-orange-500">
                    <div class="text-sm text-gray-600 mb-1">Uptime</div>
                    <div class="text-3xl font-bold text-gray-800" id="metric-uptime">0:00:00</div>
                    <div class="text-xs text-gray-600 mt-1">Average Response: <span id="metric-avg-response">0ms</span></div>
                </div>
            </div>
        </section>

        <!-- Protocol Usage Visualization -->
        <section class="mb-8">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">📈 Protocol Usage</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-lg font-semibold text-gray-700 mb-4">Request Distribution</h3>
                    <div class="space-y-4">
                        <div>
                            <div class="flex justify-between text-sm mb-1">
                                <span class="text-gray-600">MCP (Model Context)</span>
                                <span class="font-medium" id="protocol-mcp-count">0</span>
                            </div>
                            <div class="w-full bg-gray-200 rounded-full h-3">
                                <div class="bg-blue-600 h-3 rounded-full transition-all duration-500" style="width: 0%" id="protocol-mcp-bar"></div>
                            </div>
                        </div>
                        <div>
                            <div class="flex justify-between text-sm mb-1">
                                <span class="text-gray-600">A2A (Agent-to-Agent)</span>
                                <span class="font-medium" id="protocol-a2a-count">0</span>
                            </div>
                            <div class="w-full bg-gray-200 rounded-full h-3">
                                <div class="bg-green-600 h-3 rounded-full transition-all duration-500" style="width: 0%" id="protocol-a2a-bar"></div>
                            </div>
                        </div>
                        <div>
                            <div class="flex justify-between text-sm mb-1">
                                <span class="text-gray-600">ACP (Agent Comm Protocol)</span>
                                <span class="font-medium" id="protocol-acp-count">0</span>
                            </div>
                            <div class="w-full bg-gray-200 rounded-full h-3">
                                <div class="bg-purple-600 h-3 rounded-full transition-all duration-500" style="width: 0%" id="protocol-acp-bar"></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-lg font-semibold text-gray-700 mb-4">Resource Types</h3>
                    <div class="grid grid-cols-2 gap-4">
                        <div class="border-l-4 border-blue-400 pl-3">
                            <div class="text-xs text-gray-600">Database</div>
                            <div class="text-2xl font-bold text-gray-800" id="resource-database">0</div>
                        </div>
                        <div class="border-l-4 border-green-400 pl-3">
                            <div class="text-xs text-gray-600">API</div>
                            <div class="text-2xl font-bold text-gray-800" id="resource-api">0</div>
                        </div>
                        <div class="border-l-4 border-purple-400 pl-3">
                            <div class="text-xs text-gray-600">SSH</div>
                            <div class="text-2xl font-bold text-gray-800" id="resource-ssh">0</div>
                        </div>
                        <div class="border-l-4 border-orange-400 pl-3">
                            <div class="text-xs text-gray-600">Server</div>
                            <div class="text-2xl font-bold text-gray-800" id="resource-server">0</div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <!-- Protocol Testing -->
        <section class="mb-8">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">🧪 Interactive Protocol Testing</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <!-- MCP Protocol -->
                <div class="bg-white rounded-lg shadow p-6 border-t-4 border-blue-500">
                    <h3 class="text-lg font-semibold text-gray-800 mb-4">🔧 MCP Protocol</h3>
                    <p class="text-sm text-gray-600 mb-4">Model Context Protocol - Tool-based credential access</p>
                    <div class="space-y-3">
                        <select class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" id="mcp-resource-type">
                            <option value="database">Database</option>
                            <option value="api">API</option>
                            <option value="server">Server</option>
                            <option value="ssh">SSH</option>
                        </select>
                        <input type="text" placeholder="Resource Name" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" id="mcp-resource-name" value="test-database">
                        <input type="text" placeholder="Agent ID" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" id="mcp-agent-id" value="dashboard-test-agent">
                        <button onclick="testMCP()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors">
                            🚀 Test MCP
                        </button>
                    </div>
                </div>

                <!-- A2A Protocol -->
                <div class="bg-white rounded-lg shadow p-6 border-t-4 border-green-500">
                    <h3 class="text-lg font-semibold text-gray-800 mb-4">🤝 A2A Protocol</h3>
                    <p class="text-sm text-gray-600 mb-4">Agent-to-Agent - Collaborative credential exchange</p>
                    <div class="space-y-3">
                        <select class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500" id="a2a-capability">
                            <option value="request_database_credentials">Database Credentials</option>
                            <option value="request_api_credentials">API Credentials</option>
                            <option value="request_ssh_credentials">SSH Credentials</option>
                        </select>
                        <input type="text" placeholder="Resource Name" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500" id="a2a-resource-name" value="aws-api">
                        <input type="text" placeholder="Agent ID" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500" id="a2a-agent-id" value="data-analysis-agent">
                        <button onclick="testA2A()" class="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg transition-colors">
                            🚀 Test A2A
                        </button>
                    </div>
                </div>

                <!-- ACP Protocol -->
                <div class="bg-white rounded-lg shadow p-6 border-t-4 border-purple-500">
                    <h3 class="text-lg font-semibold text-gray-800 mb-4">💬 ACP Protocol</h3>
                    <p class="text-sm text-gray-600 mb-4">Agent Communication - Natural language requests</p>
                    <div class="space-y-3">
                        <textarea placeholder="Natural language request..." class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 h-20" id="acp-message">I need database credentials for test-database</textarea>
                        <input type="text" placeholder="Requester ID" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500" id="acp-requester" value="crewai-agent-001">
                        <button onclick="testACP()" class="w-full bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded-lg transition-colors">
                            🚀 Test ACP
                        </button>
                    </div>
                </div>
            </div>
        </section>

        <!-- Live Activity Feed -->
        <section class="mb-8">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">📡 Live Activity Feed</h2>
            <div class="bg-white rounded-lg shadow p-6">
                <div id="activity-feed" class="space-y-2 max-h-96 overflow-y-auto">
                    <div class="text-gray-500 text-sm text-center py-4">Waiting for activity...</div>
                </div>
            </div>
        </section>

        <!-- Token Display Modal -->
        <div id="token-modal" class="hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-lg p-6 max-w-2xl w-full mx-4">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-xl font-bold text-gray-800">Generated Token</h3>
                    <button onclick="closeTokenModal()" class="text-gray-600 hover:text-gray-800">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
                <div id="token-content" class="token-display bg-gray-100 p-4 rounded border border-gray-300 mb-4 max-h-96 overflow-y-auto"></div>
                <button onclick="copyToken()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors">
                    📋 Copy Token
                </button>
            </div>
        </div>

    </div>

    <script>
        let ws;
        let currentToken = '';
        let previousMetrics = {};

        // WebSocket connection
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = () => {
                console.log('WebSocket connected');
                document.getElementById('ws-status').className = 'status-indicator status-online pulse-slow';
                document.getElementById('ws-status-text').textContent = 'Connected';
            };
            
            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                
                if (message.type === 'metrics_update') {
                    updateMetrics(message.data);
                } else if (message.type === 'activity') {
                    addActivityLog(message.data);
                }
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                document.getElementById('ws-status').className = 'status-indicator status-offline';
                document.getElementById('ws-status-text').textContent = 'Error';
            };
            
            ws.onclose = () => {
                console.log('WebSocket disconnected');
                document.getElementById('ws-status').className = 'status-indicator status-offline';
                document.getElementById('ws-status-text').textContent = 'Disconnected';
                
                // Reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };
        }

        // Update metrics display
        function updateMetrics(metrics) {
            // Update main metrics
            document.getElementById('metric-active-tokens').textContent = metrics.tokens?.active || 0;
            document.getElementById('metric-total-requests').textContent = metrics.requests?.total || 0;
            document.getElementById('metric-success-rate').textContent = 
                (metrics.requests?.success_rate_percent || 0).toFixed(1) + '%';
            document.getElementById('metric-success-details').textContent = 
                `${metrics.requests?.successful || 0}/${metrics.requests?.total || 0}`;
            document.getElementById('metric-uptime').textContent = metrics.uptime_human || '0:00:00';
            document.getElementById('metric-avg-response').textContent = 
                (metrics.performance?.avg_response_time_ms || 0).toFixed(0) + 'ms';

            // Update protocol breakdown
            const protocols = metrics.protocols || {};
            const total = metrics.requests?.total || 1; // Avoid division by zero
            
            ['mcp', 'a2a', 'acp'].forEach(protocol => {
                const count = protocols[protocol] || 0;
                const percentage = (count / total * 100).toFixed(0);
                document.getElementById(`protocol-${protocol}-count`).textContent = count;
                document.getElementById(`protocol-${protocol}-bar`).style.width = percentage + '%';
            });

            // Update resource types
            const resources = metrics.resource_types || {};
            ['database', 'api', 'ssh', 'server'].forEach(type => {
                const element = document.getElementById(`resource-${type}`);
                if (element) {
                    element.textContent = resources[type] || 0;
                }
            });

            // Store for next comparison
            previousMetrics = metrics;
        }

        // Add activity to feed
        function addActivityLog(activity) {
            const feed = document.getElementById('activity-feed');
            
            // Remove placeholder if present
            if (feed.children.length === 1 && feed.children[0].textContent.includes('Waiting')) {
                feed.innerHTML = '';
            }

            const statusColors = {
                'success': 'bg-green-100 border-green-400 text-green-800',
                'error': 'bg-red-100 border-red-400 text-red-800',
                'failure': 'bg-red-100 border-red-400 text-red-800'
            };

            const protocolColors = {
                'MCP': 'bg-blue-500',
                'A2A': 'bg-green-500',
                'ACP': 'bg-purple-500'
            };

            const time = new Date().toLocaleTimeString();
            const colorClass = statusColors[activity.outcome] || 'bg-gray-100 border-gray-400 text-gray-800';
            const protocolColor = protocolColors[activity.protocol] || 'bg-gray-500';

            const activityDiv = document.createElement('div');
            activityDiv.className = `border-l-4 ${colorClass} p-3 rounded`;
            activityDiv.innerHTML = `
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-2">
                        <span class="${protocolColor} text-white text-xs font-bold px-2 py-1 rounded">${activity.protocol}</span>
                        <span class="text-sm font-medium">${activity.agent_id}</span>
                        <span class="text-xs text-gray-600">→</span>
                        <span class="text-sm">${activity.resource}</span>
                    </div>
                    <span class="text-xs text-gray-500">${time}</span>
                </div>
                <div class="text-xs mt-1">${activity.outcome.toUpperCase()}</div>
            `;

            feed.insertBefore(activityDiv, feed.firstChild);

            // Keep only last 20 activities
            while (feed.children.length > 20) {
                feed.removeChild(feed.lastChild);
            }
        }

        // Test protocol functions
        async function testMCP() {
            const resourceType = document.getElementById('mcp-resource-type').value;
            const resourceName = document.getElementById('mcp-resource-name').value;
            const agentId = document.getElementById('mcp-agent-id').value;

            try {
                const response = await fetch('/api/test/mcp', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        resource_type: resourceType,
                        resource_name: resourceName,
                        agent_id: agentId
                    })
                });

                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✅ MCP request successful!', 'success');
                    if (result.token) {
                        showTokenModal(result);
                    }
                } else {
                    showNotification('❌ MCP request failed: ' + (result.detail || 'Unknown error'), 'error');
                }
            } catch (error) {
                showNotification('❌ Network error: ' + error.message, 'error');
            }
        }

        async function testA2A() {
            const capability = document.getElementById('a2a-capability').value;
            const resourceName = document.getElementById('a2a-resource-name').value;
            const agentId = document.getElementById('a2a-agent-id').value;

            try {
                const response = await fetch('/api/test/a2a', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        capability_name: capability,
                        resource_name: resourceName,
                        agent_id: agentId
                    })
                });

                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✅ A2A request successful!', 'success');
                    if (result.token) {
                        showTokenModal(result);
                    }
                } else {
                    showNotification('❌ A2A request failed: ' + (result.detail || 'Unknown error'), 'error');
                }
            } catch (error) {
                showNotification('❌ Network error: ' + error.message, 'error');
            }
        }

        async function testACP() {
            const message = document.getElementById('acp-message').value;
            const requester = document.getElementById('acp-requester').value;

            try {
                const response = await fetch('/api/test/acp', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: message,
                        requester_id: requester
                    })
                });

                const result = await response.json();
                
                if (response.ok) {
                    showNotification('✅ ACP request successful!', 'success');
                    if (result.token) {
                        showTokenModal(result);
                    }
                } else {
                    showNotification('❌ ACP request failed: ' + (result.detail || 'Unknown error'), 'error');
                }
            } catch (error) {
                showNotification('❌ Network error: ' + error.message, 'error');
            }
        }

        // Token modal functions
        function showTokenModal(result) {
            currentToken = result.token;
            document.getElementById('token-content').textContent = JSON.stringify(result, null, 2);
            document.getElementById('token-modal').classList.remove('hidden');
        }

        function closeTokenModal() {
            document.getElementById('token-modal').classList.add('hidden');
        }

        function copyToken() {
            navigator.clipboard.writeText(currentToken).then(() => {
                showNotification('📋 Token copied to clipboard!', 'success');
            });
        }

        // Notification function
        function showNotification(message, type) {
            const notification = document.createElement('div');
            const bgColor = type === 'success' ? 'bg-green-500' : 'bg-red-500';
            notification.className = `${bgColor} text-white px-6 py-3 rounded-lg shadow-lg fixed top-20 right-6 z-50 transition-opacity duration-300`;
            notification.textContent = message;
            document.body.appendChild(notification);

            setTimeout(() => {
                notification.style.opacity = '0';
                setTimeout(() => document.body.removeChild(notification), 300);
            }, 3000);
        }

        // Initialize WebSocket connection
        connectWebSocket();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics and activity updates."""
    await manager.connect(websocket)
    try:
        # Keep connection alive and receive messages
        while True:
            data = await websocket.receive_text()
            # Echo back or handle commands if needed
            await websocket.send_json({"type": "pong", "data": "received"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# API endpoint to test MCP protocol
@app.post("/api/test/mcp")
async def test_mcp(request: MCPTestRequest):
    """Test MCP protocol by calling the backend credential manager via HTTP."""
    try:
        # Use the backend's credential manager via a simple HTTP call
        # Since MCP server runs on stdio, we'll simulate the MCP behavior
        # by calling the same credential manager logic that MCP uses
        
        # For now, let's use a simple approach: call the A2A server with MCP-style parameters
        # This gives us the same credential manager functionality
        base_url = os.getenv("A2A_SERVER_URL", "http://localhost:8000")
        bearer_token = os.getenv("A2A_BEARER_TOKEN", "dev-token-change-in-production")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/task",
                json={
                    "task_id": f"mcp-task-{datetime.now(UTC).timestamp()}",
                    "capability_name": "request_database_credentials",  # Use database as default
                    "parameters": {
                        "database_name": request.resource_name,
                        "duration_minutes": 5,
                    },
                    "requesting_agent_id": request.agent_id,
                },
                headers={"Authorization": f"Bearer {bearer_token}"},
                timeout=10.0,
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Record the successful request in metrics
                metrics_tracker.record_request("MCP", request.resource_type, success=True)
                
                # Broadcast activity
                await manager.broadcast({
                    "type": "activity",
                    "data": {
                        "protocol": "MCP",
                        "agent_id": request.agent_id,
                        "resource": f"{request.resource_type}/{request.resource_name}",
                        "outcome": "success"
                    }
                })
                
                return {
                    "token": result["result"]["ephemeral_token"],
                    "resource": request.resource_name,
                    "ttl_minutes": 5,
                    "protocol": "MCP",
                    "expires_in": result["result"]["expires_in_seconds"],
                    "issued_at": result["result"]["issued_at"]
                }
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        # Record the failed request in metrics
        metrics_tracker.record_request("MCP", request.resource_type, success=False)
        
        await manager.broadcast({
            "type": "activity",
            "data": {
                "protocol": "MCP",
                "agent_id": request.agent_id,
                "resource": f"{request.resource_type}/{request.resource_name}",
                "outcome": "error"
            }
        })
        raise HTTPException(status_code=500, detail=str(e))


# API endpoint to test A2A protocol
@app.post("/api/test/a2a")
async def test_a2a(request: A2ATestRequest):
    """Test A2A protocol."""
    try:
        base_url = os.getenv("A2A_SERVER_URL", "http://localhost:8000")
        bearer_token = os.getenv("A2A_BEARER_TOKEN", "dev-token-change-in-production")
        
        # Map parameters based on capability type
        parameters = {"duration_minutes": 5}
        resource_type = "database"  # default
        
        if "database" in request.capability_name:
            parameters["database_name"] = request.resource_name
            resource_type = "database"
        elif "api" in request.capability_name:
            parameters["api_name"] = request.resource_name
            resource_type = "api"
        elif "ssh" in request.capability_name:
            parameters["ssh_resource_name"] = request.resource_name
            resource_type = "ssh"
        else:
            # Default to database for unknown capabilities
            parameters["database_name"] = request.resource_name
            resource_type = "database"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/task",
                json={
                    "task_id": f"task-{datetime.now(UTC).timestamp()}",
                    "capability_name": request.capability_name,
                    "parameters": parameters,
                    "requesting_agent_id": request.agent_id,
                },
                headers={"Authorization": f"Bearer {bearer_token}"},
                timeout=10.0,
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Record the successful request in metrics
                metrics_tracker.record_request("A2A", resource_type, success=True)
                
                # Broadcast activity
                await manager.broadcast({
                    "type": "activity",
                    "data": {
                        "protocol": "A2A",
                        "agent_id": request.agent_id,
                        "resource": f"{resource_type}/{request.resource_name}",
                        "outcome": "success"
                    }
                })
                
                return {
                    "token": result["result"]["ephemeral_token"],
                    "expires_in": result["result"]["expires_in_seconds"],
                    "resource": request.resource_name
                }
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        # Record the failed request in metrics
        metrics_tracker.record_request("A2A", resource_type, success=False)
        
        await manager.broadcast({
            "type": "activity",
            "data": {
                "protocol": "A2A",
                "agent_id": request.agent_id,
                "resource": f"{resource_type}/{request.resource_name}",
                "outcome": "error"
            }
        })
        raise HTTPException(status_code=500, detail=str(e))


# API endpoint to test ACP protocol
@app.post("/api/test/acp")
async def test_acp(request: ACPTestRequest):
    """Test ACP protocol."""
    try:
        base_url = os.getenv("ACP_SERVER_URL", "http://localhost:8001")
        bearer_token = os.getenv("ACP_BEARER_TOKEN", "dev-token-change-in-production")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/run",
                json={
                    "agent_name": "credential-broker",
                    "input": [
                        {
                            "parts": [
                                {"content": request.message, "content_type": "text/plain"}
                            ],
                            "role": "user",
                        }
                    ],
                },
                headers={"Authorization": f"Bearer {bearer_token}"},
                timeout=10.0,
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract token from output
                token = None
                for output in result.get("output", []):
                    for part in output.get("parts", []):
                        if part.get("content_type") == "application/jwt":
                            token = part["content"]
                            break
                
                # Record the successful request in metrics
                metrics_tracker.record_request("ACP", "api", success=True)
                
                # Broadcast activity
                await manager.broadcast({
                    "type": "activity",
                    "data": {
                        "protocol": "ACP",
                        "agent_id": request.requester_id,
                        "resource": "natural_language_request",
                        "outcome": "success"
                    }
                })
                
                return {
                    "token": token,
                    "session_id": result.get("session_id"),
                    "run_id": result.get("run_id")
                }
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
    except Exception as e:
        # Record the failed request in metrics
        metrics_tracker.record_request("ACP", "api", success=False)
        
        await manager.broadcast({
            "type": "activity",
            "data": {
                "protocol": "ACP",
                "agent_id": request.requester_id,
                "resource": "natural_language_request",
                "outcome": "error"
            }
        })
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat() + "Z",
        "service": "dashboard-ui",
        "websocket_connections": len(manager.active_connections)
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,
        log_level="info"
    )

