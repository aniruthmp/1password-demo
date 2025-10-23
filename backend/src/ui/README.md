# Universal 1Password Credential Broker - Dashboard

**Real-time Streamlit Dashboard for Multi-Protocol Monitoring**

## 🎯 Overview

The dashboard provides an interactive, real-time visualization of the Universal 1Password Credential Broker, supporting all three protocols (MCP, A2A, ACP) with live metrics, protocol testing, and audit event streaming.

## ✨ Features

### 1. Real-Time Metrics
- **Active Tokens**: Count of non-expired tokens currently in use
- **Total Requests**: Cumulative count of all credential requests
- **Success Rate**: Percentage of successful requests vs failures
- **Uptime**: Dashboard uptime tracking

### 2. Protocol Usage Visualization
- **Bar Chart**: Visual comparison of MCP, A2A, and ACP request volumes
- **Protocol Breakdown**: Individual protocol statistics with percentages
- **Time-series tracking**: Historical request patterns

### 3. Interactive Protocol Testing
Test each protocol directly from the dashboard:

#### MCP (Model Context Protocol)
- Select resource type (database, API, SSH, generic)
- Specify resource name and agent ID
- Execute credential retrieval via tool interface

#### A2A (Agent-to-Agent)
- Choose capability (database, API, SSH credentials)
- Configure database name and duration
- Test agent collaboration workflow

#### ACP (Agent Communication Protocol)
- Natural language credential requests
- Session management testing
- Framework-agnostic integration

### 4. Active Token Display
- View all active (non-expired) tokens
- Token expiration countdown
- Token metadata (protocol, resource, agent ID, TTL)
- Full JWT token display with copy functionality

### 5. Audit Event Stream
- Real-time audit log display
- Filter by protocol (MCP, A2A, ACP)
- Filter by outcome (success, failure, error)
- Configurable event count
- CSV export for compliance reporting

## 🚀 Quick Start

### Method 1: Using the Shell Script (Recommended)

```bash
cd /Users/aniruth/projects/1password-demo/backend
./scripts/run_dashboard.sh
```

### Method 2: Using Python

```bash
cd /Users/aniruth/projects/1password-demo/backend
python -m src.ui.run_dashboard
```

### Method 3: Using Streamlit Directly

```bash
cd /Users/aniruth/projects/1password-demo/backend
streamlit run src/ui/dashboard.py
```

## 📋 Prerequisites

### 1. Install Streamlit Dependencies

```bash
cd /Users/aniruth/projects/1password-demo/backend
poetry install --extras ui
```

This installs:
- `streamlit>=1.38.0`
- `pandas>=2.2.0`

### 2. Environment Configuration

Ensure your `.env` file is configured with:

```env
# 1Password Connect
OP_CONNECT_HOST=http://localhost:8080
OP_CONNECT_TOKEN=your-connect-token
OP_VAULT_ID=your-vault-id

# JWT Configuration
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
TOKEN_TTL_MINUTES=5

# Server URLs (for A2A/ACP testing)
A2A_SERVER_URL=http://localhost:8000
A2A_BEARER_TOKEN=dev-token-change-in-production
ACP_SERVER_URL=http://localhost:8001
ACP_BEARER_TOKEN=dev-token-change-in-production
```

### 3. Start Backend Services (Optional)

For full functionality, start the backend servers:

```bash
# Terminal 1 - A2A Server
python src/a2a/run_a2a.py

# Terminal 2 - ACP Server
python src/acp/run_acp.py
```

**Note**: MCP testing works directly through the credential manager without requiring a running server.

## 🖥️ Dashboard Interface

### Navigation

The dashboard is organized into sections:

1. **Sidebar**
   - Configuration status
   - Auto-refresh controls
   - Metrics reset button

2. **Main Content**
   - Real-time metrics (top)
   - Protocol usage charts
   - Interactive testing tabs
   - Active tokens display
   - Audit event stream

### Auto-Refresh

Enable auto-refresh in the sidebar to update metrics automatically:
- Adjustable refresh interval (1-10 seconds)
- Disabled by default for better performance during testing

## 🧪 Testing Protocols

### MCP Protocol Test

1. Navigate to the "MCP Protocol" tab
2. Select resource type from dropdown
3. Enter resource name (e.g., "prod-postgres")
4. Provide agent ID (e.g., "dashboard-test-agent")
5. Click "Test MCP Protocol"
6. View results and generated token

**Example**:
- Resource Type: `database`
- Resource Name: `test-database`
- Agent ID: `dashboard-test-agent`

### A2A Protocol Test

1. Navigate to the "A2A Protocol" tab
2. Select capability from dropdown
3. Enter database name
4. Provide agent ID
5. Set duration (1-15 minutes)
6. Click "Test A2A Protocol"

**Example**:
- Capability: `request_database_credentials`
- Database Name: `analytics-db`
- Agent ID: `data-analysis-agent`
- Duration: `5` minutes

**Note**: Requires A2A server running on port 8000.

### ACP Protocol Test

1. Navigate to the "ACP Protocol" tab
2. Enter agent name (e.g., "credential-broker")
3. Write natural language request (e.g., "I need database credentials for production-db")
4. Provide requester ID
5. Click "Test ACP Protocol"

**Example**:
- Agent Name: `credential-broker`
- Request: `I need database credentials for production-db`
- Requester ID: `crewai-agent-001`

**Note**: Requires ACP server running on port 8001.

## 📊 Metrics & Analytics

### Tracked Metrics

- **Active Tokens**: Live count of non-expired tokens
- **Total Requests**: All credential requests across protocols
- **Success Count**: Successfully completed requests
- **Failure Count**: Failed requests
- **Protocol Breakdown**: Per-protocol request counts
- **Success Rate**: Percentage calculation
- **Uptime**: Dashboard session duration

### Audit Events

Each credential request generates an audit event with:
- Timestamp (ISO 8601)
- Protocol (MCP, A2A, ACP)
- Agent ID
- Resource identifier
- Outcome (success, failure, error)
- Metadata (TTL, error details, session ID)

## 🔐 Security Considerations

### Token Display

- Full JWT tokens are displayed for testing purposes
- In production, implement token masking
- Use HTTPS for dashboard access

### Environment Variables

- Never commit `.env` files
- Use secure token storage in production
- Rotate bearer tokens regularly

### Audit Logging

- Audit events are stored in session state (in-memory)
- Events persist until dashboard restart
- Export to CSV for long-term compliance

## 🎨 Customization

### Changing Dashboard Port

Edit the port in any startup method:

```bash
# Shell script
# Edit scripts/run_dashboard.sh, change --server.port=8501

# Python entry point
# Edit src/ui/run_dashboard.py, change port value

# Direct Streamlit
streamlit run src/ui/dashboard.py --server.port=8502
```

### Styling

Custom CSS is defined in `dashboard.py` at the top:
- Modify colors, fonts, spacing
- Add new component styles
- Customize metric cards

### Adding New Metrics

1. Add to `init_session_state()` function
2. Update in protocol test functions
3. Display in metrics section

## 🐛 Troubleshooting

### Dashboard Won't Start

**Error**: `streamlit: command not found`

**Solution**: Install Streamlit dependencies
```bash
poetry install --extras ui
```

### Protocol Tests Failing

**Error**: Connection refused for A2A/ACP

**Solution**: Start the backend servers
```bash
python src/a2a/run_a2a.py  # Port 8000
python src/acp/run_acp.py  # Port 8001
```

### MCP Tests Failing

**Error**: 1Password connection failed

**Solution**: Check environment variables
- Verify `OP_CONNECT_HOST` is accessible
- Validate `OP_CONNECT_TOKEN` is correct
- Ensure 1Password Connect server is running

### Tokens Not Showing

**Issue**: Tokens expire immediately

**Solution**: Check system time
- Ensure server and client times are synchronized
- Verify TTL settings in `.env`

### Audit Events Not Appearing

**Issue**: No audit events displayed

**Solution**: Test a protocol first
- Audit events are generated on protocol test
- Check outcome filters (success/failure/error)

## 📚 Additional Resources

- [Streamlit Documentation](https://docs.streamlit.io)
- [Project README](../../../README.md)
- [API Documentation](../../../docs/README.md)
- [1Password Connect API](https://developer.1password.com/docs/connect)

## 🤝 Contributing

To extend the dashboard:

1. Fork the repository
2. Create feature branch
3. Add new components to `dashboard.py`
4. Test with all three protocols
5. Submit pull request

## 📝 License

This dashboard is part of the Universal 1Password Credential Broker project.
See main project LICENSE for details.

---

**Created**: October 23, 2025  
**Last Updated**: October 23, 2025  
**Version**: 1.0.0  
**Status**: ✅ Complete

