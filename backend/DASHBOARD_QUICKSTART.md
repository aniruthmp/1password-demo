# Dashboard Quick Start Guide

**Universal 1Password Credential Broker - Streamlit Dashboard**

## 🚀 5-Minute Quick Start

### Step 1: Install UI Dependencies

```bash
cd /Users/aniruth/projects/1password-demo/backend
poetry install --extras ui
```

### Step 2: Configure Environment

Ensure your `.env` file has the required variables:

```env
# 1Password Connect (Required for MCP testing)
OP_CONNECT_HOST=http://localhost:8080
OP_CONNECT_TOKEN=your-connect-token
OP_VAULT_ID=your-vault-id

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256
TOKEN_TTL_MINUTES=5

# A2A Server (Optional - for A2A protocol testing)
A2A_SERVER_URL=http://localhost:8000
A2A_BEARER_TOKEN=dev-token-change-in-production

# ACP Server (Optional - for ACP protocol testing)
ACP_SERVER_URL=http://localhost:8001
ACP_BEARER_TOKEN=dev-token-change-in-production
```

### Step 3: Start the Dashboard

**Option A: Using the startup script (Recommended)**
```bash
./scripts/run_dashboard.sh
```

**Option B: Using Python**
```bash
python -m src.ui.run_dashboard
```

**Option C: Using Streamlit directly**
```bash
streamlit run src/ui/dashboard.py
```

### Step 4: Access the Dashboard

Open your browser and navigate to:
```
http://localhost:8501
```

## 🧪 Testing Protocols

### MCP Protocol (No server required)

1. Navigate to the "MCP Protocol" tab
2. Select resource type: `database`
3. Enter resource name: `test-database` (or your actual 1Password item)
4. Enter agent ID: `dashboard-test-agent`
5. Click "🚀 Test MCP Protocol"

**Result**: Token generated instantly via direct credential manager integration.

### A2A Protocol (Requires A2A server)

**Start A2A server first:**
```bash
# In a new terminal
cd /Users/aniruth/projects/1password-demo/backend
python src/a2a/run_a2a.py
```

**Then test:**
1. Navigate to the "A2A Protocol" tab
2. Select capability: `request_database_credentials`
3. Enter database name: `analytics-db`
4. Enter agent ID: `data-analysis-agent`
5. Set duration: `5` minutes
6. Click "🚀 Test A2A Protocol"

### ACP Protocol (Requires ACP server)

**Start ACP server first:**
```bash
# In a new terminal
cd /Users/aniruth/projects/1password-demo/backend
python src/acp/run_acp.py
```

**Then test:**
1. Navigate to the "ACP Protocol" tab
2. Agent name: `credential-broker`
3. Natural language request: `I need database credentials for production-db`
4. Requester ID: `crewai-agent-001`
5. Click "🚀 Test ACP Protocol"

## 📊 Dashboard Features

### Real-Time Metrics
- **Active Tokens**: Number of non-expired tokens
- **Total Requests**: Cumulative request count
- **Success Rate**: Percentage of successful requests
- **Uptime**: Dashboard session duration

### Protocol Usage Visualization
- Bar chart comparing protocol usage
- Individual protocol statistics
- Time-series tracking

### Active Tokens Display
- View all active tokens with expiration countdown
- Token metadata and full JWT display
- Automatic cleanup of expired tokens

### Audit Event Stream
- Real-time audit log
- Filter by protocol and outcome
- CSV export for compliance

## 🔧 Troubleshooting

### Dashboard won't start

**Error**: `streamlit: command not found`

**Solution**:
```bash
poetry install --extras ui
```

### MCP tests failing

**Error**: "Failed to fetch credentials"

**Check**:
1. Is 1Password Connect running? `curl http://localhost:8080/health`
2. Is `OP_CONNECT_TOKEN` correct in `.env`?
3. Does the item exist in your 1Password vault?
4. Is `OP_VAULT_ID` correct?

### A2A/ACP tests failing

**Error**: "Connection refused"

**Solution**: Start the respective server:
```bash
# For A2A
python src/a2a/run_a2a.py

# For ACP
python src/acp/run_acp.py
```

### Tokens expire immediately

**Issue**: Time synchronization

**Check**: Ensure your system time is correct
```bash
date
```

## 📚 Advanced Features

### Auto-Refresh

Enable in the sidebar to automatically update metrics:
- Adjustable interval (1-10 seconds)
- Real-time token countdown
- Live audit event stream

### Export Audit Logs

1. Scroll to "Audit Event Stream" section
2. Apply desired filters (protocol, outcome)
3. Click "📥 Download Audit Log (CSV)"
4. Opens in Excel/CSV viewer

### Reset Metrics

Click "🔄 Reset All Metrics" in the sidebar to:
- Clear all tokens
- Reset request counters
- Clear audit event history
- Reset uptime tracking

## 🎯 Demo Scenario

**Complete end-to-end demonstration:**

1. **Start all services** (in separate terminals):
   ```bash
   # Terminal 1 - A2A Server
   python src/a2a/run_a2a.py
   
   # Terminal 2 - ACP Server
   python src/acp/run_acp.py
   
   # Terminal 3 - Dashboard
   ./scripts/run_dashboard.sh
   ```

2. **Test MCP Protocol**:
   - Generate database credentials
   - Observe token in "Active Tokens" section
   - Watch expiration countdown

3. **Test A2A Protocol**:
   - Request credentials via agent collaboration
   - Compare with MCP in "Protocol Usage" chart

4. **Test ACP Protocol**:
   - Use natural language request
   - View session management in action

5. **Monitor Audit Trail**:
   - Filter by protocol
   - Export CSV for compliance
   - Verify all requests logged

6. **Watch Token Expiration**:
   - Wait 5 minutes
   - Observe tokens automatically removed
   - Success rate remains accurate

## 🌐 Production Considerations

**Security**:
- Use HTTPS in production
- Implement token masking for sensitive displays
- Rotate bearer tokens regularly
- Enable authentication for dashboard access

**Performance**:
- Disable auto-refresh for high-volume scenarios
- Limit audit event display count
- Use pagination for large token lists

**Compliance**:
- Export audit logs regularly
- Archive to secure storage
- Implement log retention policies

## 📖 Additional Resources

- **Dashboard Documentation**: `src/ui/README.md`
- **Backend README**: `README.md`
- **Project Documentation**: `../docs/README.md`
- **API Documentation**: `../docs/PRD-ver-1.0.md`

## 💡 Tips

1. **Testing tip**: Create a dedicated test vault in 1Password for dashboard testing
2. **Development tip**: Use DEBUG log level to see detailed credential flow
3. **Demo tip**: Enable auto-refresh for live demonstrations
4. **Performance tip**: Use longer refresh intervals (5-10s) for production monitoring

## 🎉 Success Indicators

Your dashboard is working correctly when:
- ✅ Health check shows all green statuses
- ✅ MCP protocol test generates tokens
- ✅ Active tokens display with countdown
- ✅ Audit events appear after requests
- ✅ Protocol usage charts update
- ✅ Token expiration works automatically

---

**Version**: 1.0.0  
**Last Updated**: October 23, 2025  
**Status**: ✅ Production Ready

For issues or questions, see `src/ui/README.md` or the main project documentation.

