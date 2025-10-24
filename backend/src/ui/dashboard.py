"""
Streamlit Dashboard for Universal 1Password Credential Broker
Real-time visualization of MCP, A2A, and ACP protocols with interactive testing.
"""

import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.audit_logger import AuditLogger
from src.core.credential_manager import CredentialManager


# Page configuration
st.set_page_config(
    page_title="1Password Credential Broker",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
    }
    .success-box {
        padding: 10px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        color: #155724;
    }
    .error-box {
        padding: 10px;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 5px;
        color: #721c24;
    }
    .token-display {
        font-family: 'Courier New', monospace;
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #dee2e6;
        font-size: 12px;
        word-break: break-all;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Initialize session state
def init_session_state():
    """Initialize Streamlit session state variables."""
    if "total_requests" not in st.session_state:
        st.session_state.total_requests = 0
    if "active_tokens" not in st.session_state:
        st.session_state.active_tokens = []
    if "protocol_counts" not in st.session_state:
        st.session_state.protocol_counts = {"MCP": 0, "A2A": 0, "ACP": 0}
    if "success_count" not in st.session_state:
        st.session_state.success_count = 0
    if "failure_count" not in st.session_state:
        st.session_state.failure_count = 0
    if "audit_events" not in st.session_state:
        st.session_state.audit_events = []
    if "last_token" not in st.session_state:
        st.session_state.last_token = None
    if "start_time" not in st.session_state:
        st.session_state.start_time = datetime.now(UTC)


init_session_state()


# Helper functions
def get_time_remaining(expires_at: float) -> str:
    """Calculate time remaining until expiration."""
    now = datetime.now(UTC).timestamp()
    remaining = int(expires_at - now)
    if remaining <= 0:
        return "Expired"
    minutes = remaining // 60
    seconds = remaining % 60
    return f"{minutes}m {seconds}s"


def clean_expired_tokens():
    """Remove expired tokens from active tokens list."""
    now = datetime.now(UTC).timestamp()
    st.session_state.active_tokens = [
        token
        for token in st.session_state.active_tokens
        if token["expires_at"] > now
    ]


def add_audit_event(
    protocol: str,
    agent_id: str,
    resource: str,
    outcome: str,
    metadata: dict[str, Any] | None = None,
):
    """Add an audit event to the session state."""
    event = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "protocol": protocol,
        "agent_id": agent_id,
        "resource": resource,
        "outcome": outcome,
        "metadata": metadata or {},
    }
    st.session_state.audit_events.insert(0, event)  # Most recent first
    # Keep only last 100 events
    st.session_state.audit_events = st.session_state.audit_events[:100]


# Audit log reading functions
def get_audit_log_path() -> Path:
    """Get the path to the audit log file."""
    # Get the backend directory (parent of src)
    backend_dir = Path(__file__).parent.parent.parent
    return backend_dir / "logs" / "audit.log"


def read_audit_log_events(since_timestamp: str | None = None) -> list[dict[str, Any]]:
    """
    Read audit log events from the log file.
    
    Args:
        since_timestamp: Only return events after this timestamp (ISO format)
        
    Returns:
        List of parsed audit events
    """
    audit_log_path = get_audit_log_path()
    
    if not audit_log_path.exists():
        return []
    
    events = []
    try:
        with open(audit_log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    event = json.loads(line)
                    
                    # Filter by timestamp if provided
                    if since_timestamp and event.get('timestamp', '') <= since_timestamp:
                        continue
                        
                    events.append(event)
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue
                    
    except Exception as e:
        st.error(f"Error reading audit log: {e}")
        
    return events


def update_metrics_from_audit_logs():
    """Update dashboard metrics by reading audit logs."""
    # Get the last processed timestamp
    last_processed = st.session_state.get('last_audit_timestamp', None)
    
    # Read new events since last check
    new_events = read_audit_log_events(since_timestamp=last_processed)
    
    if not new_events:
        return
    
    # Update timestamp for next check
    if new_events:
        st.session_state.last_audit_timestamp = new_events[-1]['timestamp']
    
    # Process each new event
    for event in new_events:
        protocol = event.get('protocol', '').upper()
        outcome = event.get('outcome', '')
        agent_id = event.get('agent_id', 'unknown')
        resource = event.get('resource', 'unknown')
        metadata = event.get('metadata', {})
        
        # Update counters
        st.session_state.total_requests += 1
        
        if protocol in st.session_state.protocol_counts:
            st.session_state.protocol_counts[protocol] += 1
        
        # Update success/failure counts
        if outcome in ['success']:
            st.session_state.success_count += 1
            
            # Add to active tokens if it's a successful credential access
            if event.get('event_type') == 'credential_access' and 'expires_at' in metadata:
                token_info = {
                    "token": f"JWT_TOKEN_{len(st.session_state.active_tokens) + 1}",  # Placeholder
                    "protocol": protocol,
                    "resource": resource,
                    "agent_id": agent_id,
                    "issued_at": datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')).timestamp(),
                    "expires_at": metadata.get('expires_at', 0),
                    "ttl_minutes": metadata.get('ttl_minutes', 5),
                }
                st.session_state.active_tokens.append(token_info)
                
        elif outcome in ['failure', 'error', 'denied']:
            st.session_state.failure_count += 1
        
        # Add to audit events for display
        add_audit_event(
            protocol=protocol,
            agent_id=agent_id,
            resource=resource,
            outcome=outcome,
            metadata=metadata
        )


def initialize_audit_log_metrics():
    """Initialize metrics by reading all existing audit logs."""
    if 'audit_log_initialized' not in st.session_state:
        # Read all events to initialize metrics
        all_events = read_audit_log_events()
        
        # Reset counters
        st.session_state.total_requests = 0
        st.session_state.protocol_counts = {"MCP": 0, "A2A": 0, "ACP": 0}
        st.session_state.success_count = 0
        st.session_state.failure_count = 0
        st.session_state.active_tokens = []
        st.session_state.audit_events = []
        
        # Process all events
        for event in all_events:
            protocol = event.get('protocol', '').upper()
            outcome = event.get('outcome', '')
            agent_id = event.get('agent_id', 'unknown')
            resource = event.get('resource', 'unknown')
            metadata = event.get('metadata', {})
            
            # Update counters
            st.session_state.total_requests += 1
            
            if protocol in st.session_state.protocol_counts:
                st.session_state.protocol_counts[protocol] += 1
            
            # Update success/failure counts
            if outcome in ['success']:
                st.session_state.success_count += 1
                
                # Add to active tokens if it's a successful credential access and not expired
                if (event.get('event_type') == 'credential_access' and 
                    'expires_at' in metadata and 
                    metadata.get('expires_at', 0) > datetime.now(UTC).timestamp()):
                    
                    token_info = {
                        "token": f"JWT_TOKEN_{len(st.session_state.active_tokens) + 1}",  # Placeholder
                        "protocol": protocol,
                        "resource": resource,
                        "agent_id": agent_id,
                        "issued_at": datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')).timestamp(),
                        "expires_at": metadata.get('expires_at', 0),
                        "ttl_minutes": metadata.get('ttl_minutes', 5),
                    }
                    st.session_state.active_tokens.append(token_info)
                    
            elif outcome in ['failure', 'error', 'denied']:
                st.session_state.failure_count += 1
            
            # Add to audit events for display
            add_audit_event(
                protocol=protocol,
                agent_id=agent_id,
                resource=resource,
                outcome=outcome,
                metadata=metadata
            )
        
        # Set the last processed timestamp
        if all_events:
            st.session_state.last_audit_timestamp = all_events[-1]['timestamp']
        
        st.session_state.audit_log_initialized = True


# Test protocol functions
async def test_mcp_protocol(resource_type: str, resource_name: str, agent_id: str):
    """Test MCP protocol by calling the credential manager directly."""
    try:
        # Initialize credential manager
        credential_manager = CredentialManager()

        # Fetch and issue token
        result = credential_manager.fetch_and_issue_token(
            resource_type=resource_type,
            resource_name=resource_name,
            agent_id=agent_id,
            ttl_minutes=5,
        )

        # Update metrics
        st.session_state.total_requests += 1
        st.session_state.protocol_counts["MCP"] += 1
        st.session_state.success_count += 1

        # Add token to active tokens
        token_info = {
            "token": result["token"],
            "protocol": "MCP",
            "resource": result["resource"],
            "agent_id": agent_id,
            "issued_at": datetime.fromisoformat(
                str(result["issued_at"]).replace("Z", "+00:00")
            ).timestamp(),
            "expires_at": datetime.fromisoformat(
                str(result["expires_at"]).replace("Z", "+00:00")
            ).timestamp(),
            "ttl_minutes": result["ttl_minutes"],
        }
        st.session_state.active_tokens.append(token_info)
        st.session_state.last_token = result["token"]

        # Add audit event
        add_audit_event(
            protocol="MCP",
            agent_id=agent_id,
            resource=result["resource"],
            outcome="success",
            metadata={"ttl_minutes": result["ttl_minutes"]},
        )

        return {"success": True, "result": result}

    except Exception as e:
        st.session_state.total_requests += 1
        st.session_state.protocol_counts["MCP"] += 1
        st.session_state.failure_count += 1

        # Add audit event
        add_audit_event(
            protocol="MCP",
            agent_id=agent_id,
            resource=f"{resource_type}/{resource_name}",
            outcome="error",
            metadata={"error": str(e)},
        )

        return {"success": False, "error": str(e)}


async def test_a2a_protocol(
    capability_name: str, database_name: str, agent_id: str, duration_minutes: int = 5
):
    """Test A2A protocol via HTTP API."""
    try:
        base_url = os.getenv("A2A_SERVER_URL", "http://localhost:8000")
        bearer_token = os.getenv(
            "A2A_BEARER_TOKEN", "dev-token-change-in-production"
        )

        async with httpx.AsyncClient() as client:
            # Make request to A2A server
            response = await client.post(
                f"{base_url}/task",
                json={
                    "task_id": f"task-{datetime.now(UTC).timestamp()}",
                    "capability_name": capability_name,
                    "parameters": {
                        "database_name": database_name,
                        "duration_minutes": duration_minutes,
                    },
                    "requesting_agent_id": agent_id,
                },
                headers={"Authorization": f"Bearer {bearer_token}"},
                timeout=10.0,
            )

            if response.status_code == 200:
                result = response.json()

                # Update metrics
                st.session_state.total_requests += 1
                st.session_state.protocol_counts["A2A"] += 1
                st.session_state.success_count += 1

                # Extract token from result
                token = result["result"]["ephemeral_token"]
                expires_in = result["result"]["expires_in_seconds"]

                # Add token to active tokens
                token_info = {
                    "token": token,
                    "protocol": "A2A",
                    "resource": f"database/{database_name}",
                    "agent_id": agent_id,
                    "issued_at": datetime.now(UTC).timestamp(),
                    "expires_at": datetime.now(UTC).timestamp() + expires_in,
                    "ttl_minutes": duration_minutes,
                }
                st.session_state.active_tokens.append(token_info)
                st.session_state.last_token = token

                # Add audit event
                add_audit_event(
                    protocol="A2A",
                    agent_id=agent_id,
                    resource=f"database/{database_name}",
                    outcome="success",
                    metadata={"ttl_minutes": duration_minutes},
                )

                return {"success": True, "result": result}
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

    except Exception as e:
        st.session_state.total_requests += 1
        st.session_state.protocol_counts["A2A"] += 1
        st.session_state.failure_count += 1

        # Add audit event
        add_audit_event(
            protocol="A2A",
            agent_id=agent_id,
            resource=f"database/{database_name}",
            outcome="error",
            metadata={"error": str(e)},
        )

        return {"success": False, "error": str(e)}


async def test_acp_protocol(agent_name: str, message: str, requester_id: str):
    """Test ACP protocol via HTTP API."""
    try:
        base_url = os.getenv("ACP_SERVER_URL", "http://localhost:8001")
        bearer_token = os.getenv(
            "ACP_BEARER_TOKEN", "dev-token-change-in-production"
        )

        async with httpx.AsyncClient() as client:
            # Make request to ACP server
            response = await client.post(
                f"{base_url}/run",
                json={
                    "agent_name": agent_name,
                    "input": [
                        {
                            "parts": [
                                {"content": message, "content_type": "text/plain"}
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

                # Update metrics
                st.session_state.total_requests += 1
                st.session_state.protocol_counts["ACP"] += 1
                st.session_state.success_count += 1

                # Extract token from output if present
                token = None
                for output in result.get("output", []):
                    for part in output.get("parts", []):
                        if part.get("content_type") == "application/jwt":
                            token = part["content"]
                            break

                if token:
                    # Add token to active tokens
                    token_info = {
                        "token": token,
                        "protocol": "ACP",
                        "resource": "parsed_from_message",
                        "agent_id": requester_id,
                        "issued_at": datetime.now(UTC).timestamp(),
                        "expires_at": datetime.now(UTC).timestamp()
                        + 300,  # 5 minutes default
                        "ttl_minutes": 5,
                    }
                    st.session_state.active_tokens.append(token_info)
                    st.session_state.last_token = token

                # Add audit event
                add_audit_event(
                    protocol="ACP",
                    agent_id=requester_id,
                    resource="natural_language_request",
                    outcome="success",
                    metadata={"session_id": result.get("session_id")},
                )

                return {"success": True, "result": result}
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

    except Exception as e:
        st.session_state.total_requests += 1
        st.session_state.protocol_counts["ACP"] += 1
        st.session_state.failure_count += 1

        # Add audit event
        add_audit_event(
            protocol="ACP",
            agent_id=requester_id,
            resource="natural_language_request",
            outcome="error",
            metadata={"error": str(e)},
        )

        return {"success": False, "error": str(e)}


# Main dashboard
def main():
    """Main dashboard rendering function."""
    # Initialize audit log metrics on first run
    initialize_audit_log_metrics()
    
    # Update metrics from audit logs
    update_metrics_from_audit_logs()
    
    # Clean expired tokens
    clean_expired_tokens()

    # Header
    st.title("🔐 Universal 1Password Credential Broker")
    st.markdown(
        "**Multi-Protocol Dashboard** | Real-time monitoring for MCP, A2A, and ACP"
    )
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.info(
            "This dashboard provides real-time monitoring and testing "
            "for all three protocols."
        )

        st.subheader("Environment Status")
        # Check environment variables
        op_host = os.getenv("OP_CONNECT_HOST", "Not set")
        op_token = "✓ Set" if os.getenv("OP_CONNECT_TOKEN") else "✗ Not set"

        st.text(f"1Password Host: {op_host}")
        st.text(f"1Password Token: {op_token}")

        st.markdown("---")

        # Audit Log Status
        st.subheader("📋 Audit Log Status")
        audit_log_path = get_audit_log_path()
        if audit_log_path.exists():
            st.success("✓ Audit log file found")
            st.text(f"Path: {audit_log_path}")
            
            # Show last processed timestamp
            last_processed = st.session_state.get('last_audit_timestamp', 'None')
            if last_processed != 'None':
                st.text(f"Last processed: {last_processed[:19]}")
            else:
                st.text("Last processed: Not set")
        else:
            st.error("✗ Audit log file not found")
            st.text(f"Expected: {audit_log_path}")

        st.markdown("---")

        # Auto-refresh control
        st.subheader("🔄 Auto-Refresh")
        auto_refresh = st.checkbox("Enable auto-refresh", value=True)
        if auto_refresh:
            refresh_interval = st.slider(
                "Refresh interval (seconds)", 1, 10, 3, key="refresh_interval"
            )
            st.markdown(f"Refreshing every **{refresh_interval}s**")

        st.markdown("---")

        # Reset metrics
        if st.button("🔄 Reset All Metrics", width='stretch'):
            st.session_state.total_requests = 0
            st.session_state.active_tokens = []
            st.session_state.protocol_counts = {"MCP": 0, "A2A": 0, "ACP": 0}
            st.session_state.success_count = 0
            st.session_state.failure_count = 0
            st.session_state.audit_events = []
            st.session_state.last_token = None
            st.session_state.start_time = datetime.now(UTC)
            # Reset audit log tracking
            st.session_state.last_audit_timestamp = None
            st.session_state.audit_log_initialized = False
            st.rerun()

    # Main content area
    # Section 1: Real-time Metrics
    st.header("📊 Real-Time Metrics")

    # Calculate uptime
    uptime = datetime.now(UTC) - st.session_state.start_time
    uptime_str = str(uptime).split(".")[0]  # Remove microseconds

    # Calculate success rate
    total = st.session_state.total_requests
    success_rate = (
        (st.session_state.success_count / total * 100) if total > 0 else 0.0
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Active Tokens",
            value=len(st.session_state.active_tokens),
            delta=None,
        )

    with col2:
        st.metric(
            label="Total Requests",
            value=st.session_state.total_requests,
            delta=None,
        )

    with col3:
        st.metric(
            label="Success Rate",
            value=f"{success_rate:.1f}%",
            delta=f"{st.session_state.success_count}/{total}",
        )

    with col4:
        st.metric(label="Uptime", value=uptime_str, delta=None)

    st.markdown("---")

    # Section 2: Available Vault Resources
    st.header("🗄️ Available 1Password Vault Resources")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.subheader("🖥️ Servers")
        st.markdown("""
        - **dev-server** (dev-login)
        - **staging-server** (stage-login)
        - **production-server** (prod-login)
        """)
    
    with col2:
        st.subheader("🔌 APIs")
        st.markdown("""
        - **aws-api**
        - **slack-api**
        - **github-api**
        - **stripe-api**
        - **test-api**
        """)
    
    with col3:
        st.subheader("🗃️ Databases")
        st.markdown("""
        - **dev-mysql** (demo-)
        - **staging-postgres** (dbuser)
        - **production-db** (dbuser)
        - **production-postgres** (test)
        - **test-database** (dbuser)
        """)
    
    with col4:
        st.subheader("🔑 SSH & Generic")
        st.markdown("""
        - **test-ssh** (SHA256:ms2+8dvzsl/sjzueHVDFAd/...)
        - **generic** (test)
        """)

    st.markdown("---")

    # Section 3: Protocol Usage Visualization
    st.header("📈 Protocol Usage")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Bar chart
        protocol_df = pd.DataFrame(
            {
                "Protocol": ["MCP", "A2A", "ACP"],
                "Requests": [
                    st.session_state.protocol_counts["MCP"],
                    st.session_state.protocol_counts["A2A"],
                    st.session_state.protocol_counts["ACP"],
                ],
            }
        )

        st.bar_chart(protocol_df.set_index("Protocol"), width='stretch')

    with col2:
        st.subheader("Protocol Breakdown")
        for protocol in ["MCP", "A2A", "ACP"]:
            count = st.session_state.protocol_counts[protocol]
            percentage = (count / total * 100) if total > 0 else 0
            st.metric(label=protocol, value=count, delta=f"{percentage:.1f}%")

    st.markdown("---")

    # Section 4: Interactive Protocol Testing
    st.header("🧪 Interactive Protocol Testing")

    tab1, tab2, tab3 = st.tabs(["MCP Protocol", "A2A Protocol", "ACP Protocol"])

    with tab1:
        st.subheader("Model Context Protocol (MCP)")
        st.markdown(
            "Test MCP protocol by requesting credentials directly through the tool interface."
        )

        col1, col2 = st.columns(2)

        with col1:
            resource_type = st.selectbox(
                "Resource Type",
                ["server", "api", "database", "ssh", "generic"],
                key="mcp_resource_type",
            )
            
            # Dynamic resource name options based on type
            if resource_type == "server":
                resource_name = st.selectbox(
                    "Server Name",
                    ["dev-server", "staging-server", "production-server"],
                    key="mcp_resource_name",
                )
            elif resource_type == "api":
                resource_name = st.selectbox(
                    "API Name",
                    ["aws-api", "slack-api", "github-api", "stripe-api", "test-api"],
                    key="mcp_resource_name",
                )
            elif resource_type == "database":
                resource_name = st.selectbox(
                    "Database Name",
                    ["dev-mysql", "staging-postgres", "production-db", "production-postgres", "test-database"],
                    key="mcp_resource_name",
                )
            elif resource_type == "ssh":
                resource_name = st.selectbox(
                    "SSH Key Name",
                    ["test-ssh"],
                    key="mcp_resource_name",
                )
            else:  # generic
                resource_name = st.selectbox(
                    "Generic Resource Name",
                    ["generic"],
                    key="mcp_resource_name",
                )

        with col2:
            agent_id = st.text_input(
                "Agent ID",
                value="dashboard-test-agent",
                key="mcp_agent_id",
            )

        if st.button("🚀 Test MCP Protocol", width='stretch', key="test_mcp"):
            with st.spinner("Requesting credentials via MCP..."):
                result = asyncio.run(
                    test_mcp_protocol(resource_type, resource_name, agent_id)
                )

                if result["success"]:
                    st.success("✅ MCP request successful!")
                    st.json(result["result"])
                else:
                    st.error(f"❌ MCP request failed: {result['error']}")

    with tab2:
        st.subheader("Agent-to-Agent (A2A) Protocol")
        st.markdown(
            "Test A2A protocol by simulating agent collaboration via REST API."
        )

        col1, col2 = st.columns(2)

        with col1:
            capability = st.selectbox(
                "Capability",
                [
                    "request_database_credentials",
                    "request_api_credentials",
                    "request_ssh_credentials",
                    "request_generic_secret",
                ],
                key="a2a_capability",
            )
            database_name = st.selectbox(
                "Database Name",
                ["dev-mysql", "staging-postgres", "production-db", "production-postgres", "test-database"],
                key="a2a_database_name",
            )

        with col2:
            a2a_agent_id = st.text_input(
                "Agent ID",
                value="data-analysis-agent",
                key="a2a_agent_id",
            )
            duration = st.number_input(
                "Duration (minutes)", min_value=1, max_value=15, value=5, key="a2a_ttl"
            )

        if st.button("🚀 Test A2A Protocol", width='stretch', key="test_a2a"):
            with st.spinner("Requesting credentials via A2A..."):
                result = asyncio.run(
                    test_a2a_protocol(
                        capability, database_name, a2a_agent_id, duration
                    )
                )

                if result["success"]:
                    st.success("✅ A2A request successful!")
                    st.json(result["result"])
                else:
                    st.error(f"❌ A2A request failed: {result['error']}")

    with tab3:
        st.subheader("Agent Communication Protocol (ACP)")
        st.markdown(
            "Test ACP protocol with natural language credential requests via REST API."
        )

        col1, col2 = st.columns(2)

        with col1:
            agent_name = st.text_input(
                "Agent Name",
                value="credential-broker",
                key="acp_agent_name",
            )
            message = st.text_area(
                "Natural Language Request",
                value="I need database credentials for production-postgres",
                key="acp_message",
                height=100,
            )

        with col2:
            acp_requester = st.text_input(
                "Requester ID",
                value="crewai-agent-001",
                key="acp_requester",
            )

        if st.button("🚀 Test ACP Protocol", width='stretch', key="test_acp"):
            with st.spinner("Requesting credentials via ACP..."):
                result = asyncio.run(test_acp_protocol(agent_name, message, acp_requester))

                if result["success"]:
                    st.success("✅ ACP request successful!")
                    st.json(result["result"])
                else:
                    st.error(f"❌ ACP request failed: {result['error']}")

    st.markdown("---")

    # Section 5: Active Tokens Display
    st.header("🎟️ Active Tokens")

    if st.session_state.active_tokens:
        for i, token_info in enumerate(st.session_state.active_tokens):
            with st.expander(
                f"Token {i+1} - {token_info['protocol']} | {token_info['resource']} | "
                f"Expires: {get_time_remaining(token_info['expires_at'])}"
            ):
                col1, col2 = st.columns([1, 3])

                with col1:
                    st.markdown("**Details:**")
                    st.text(f"Protocol: {token_info['protocol']}")
                    st.text(f"Resource: {token_info['resource']}")
                    st.text(f"Agent: {token_info['agent_id']}")
                    st.text(f"TTL: {token_info['ttl_minutes']} minutes")

                    time_left = get_time_remaining(token_info["expires_at"])
                    if time_left == "Expired":
                        st.error(f"⏰ Status: {time_left}")
                    else:
                        st.success(f"⏰ Time Left: {time_left}")

                with col2:
                    st.markdown("**Token:**")
                    st.code(token_info["token"], language=None)

                    if st.button(f"📋 Copy Token {i+1}", key=f"copy_{i}"):
                        st.info("Token copied to description above!")
    else:
        st.info("No active tokens. Test a protocol to generate credentials.")

    st.markdown("---")

    # Section 6: Audit Event Stream
    st.header("📜 Audit Event Stream")

    # Filter controls
    col1, col2, col3 = st.columns(3)

    with col1:
        protocol_filter = st.multiselect(
            "Filter by Protocol",
            ["MCP", "A2A", "ACP"],
            default=["MCP", "A2A", "ACP"],
            key="audit_protocol_filter",
        )

    with col2:
        outcome_filter = st.multiselect(
            "Filter by Outcome",
            ["success", "failure", "error"],
            default=["success", "failure", "error"],
            key="audit_outcome_filter",
        )

    with col3:
        max_events = st.number_input(
            "Max Events", min_value=5, max_value=100, value=20, key="max_events"
        )

    # Display audit events
    if st.session_state.audit_events:
        # Filter events
        filtered_events = [
            event
            for event in st.session_state.audit_events
            if event["protocol"] in protocol_filter
            and event["outcome"] in outcome_filter
        ][:max_events]

        if filtered_events:
            # Convert to DataFrame for better display
            events_df = pd.DataFrame(filtered_events)

            # Format timestamp
            if "timestamp" in events_df.columns:
                events_df["timestamp"] = pd.to_datetime(
                    events_df["timestamp"]
                ).dt.strftime("%Y-%m-%d %H:%M:%S")

            # Reorder columns
            columns = ["timestamp", "protocol", "agent_id", "resource", "outcome"]
            events_df = events_df[columns]

            st.dataframe(
                events_df,
                width='stretch',
                hide_index=True,
            )

            # Download button
            csv = events_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Audit Log (CSV)",
                data=csv,
                file_name=f"audit_log_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
        else:
            st.info("No events match the selected filters.")
    else:
        st.info(
            "No audit events yet. Test a protocol to generate audit trail data."
        )

    # Auto-refresh
    if auto_refresh:
        import time

        time.sleep(refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()

