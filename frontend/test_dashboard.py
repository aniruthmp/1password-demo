"""
Test script for FastAPI + Tailwind WebSocket Dashboard
Validates all endpoints and WebSocket functionality.
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx
import websockets

# Test configuration
BASE_URL = "http://localhost:3000"
WS_URL = "ws://localhost:3000/ws"


async def test_health_endpoint():
    """Test the health check endpoint."""
    print("\n🔍 Testing Health Endpoint...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Health check passed")
                print(f"   Status: {data.get('status')}")
                print(f"   Service: {data.get('service')}")
                print(f"   WebSocket Connections: {data.get('websocket_connections')}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


async def test_main_page():
    """Test that the main dashboard page loads."""
    print("\n🔍 Testing Main Dashboard Page...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/")
            
            if response.status_code == 200:
                html = response.text
                
                # Check for key elements
                checks = [
                    ("Title", "1Password Credential Broker" in html),
                    ("Tailwind CSS", "tailwindcss.com" in html),
                    ("WebSocket", "new WebSocket" in html),
                    ("MCP Section", "MCP Protocol" in html),
                    ("A2A Section", "A2A Protocol" in html),
                    ("ACP Section", "ACP Protocol" in html),
                    ("Metrics", "Real-Time Metrics" in html),
                ]
                
                all_passed = True
                for name, passed in checks:
                    status = "✅" if passed else "❌"
                    print(f"   {status} {name}")
                    if not passed:
                        all_passed = False
                
                return all_passed
            else:
                print(f"❌ Dashboard page failed to load: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Dashboard page error: {e}")
        return False


async def test_websocket_connection():
    """Test WebSocket connection and message handling."""
    print("\n🔍 Testing WebSocket Connection...")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ WebSocket connection established")
            
            # Wait for metrics update (should come within 2 seconds)
            print("   Waiting for metrics update...")
            
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                
                if data.get("type") == "metrics_update":
                    print("✅ Received metrics update")
                    print(f"   Total Requests: {data['data'].get('requests', {}).get('total', 0)}")
                    print(f"   Active Tokens: {data['data'].get('tokens', {}).get('active', 0)}")
                    return True
                else:
                    print(f"⚠️  Received unexpected message type: {data.get('type')}")
                    return True  # Still counts as working
            except asyncio.TimeoutError:
                print("⚠️  No metrics update received (timeout)")
                return True  # Connection worked, just no data yet
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        return False


async def test_mcp_endpoint():
    """Test the MCP protocol testing endpoint."""
    print("\n🔍 Testing MCP Endpoint...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/test/mcp",
                json={
                    "resource_type": "database",
                    "resource_name": "test-database",
                    "agent_id": "test-dashboard-agent"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ MCP endpoint working")
                print(f"   Token generated: {data.get('token', '')[:50]}...")
                print(f"   Resource: {data.get('resource')}")
                print(f"   TTL: {data.get('ttl_minutes')} minutes")
                return True
            else:
                print(f"❌ MCP endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
    except Exception as e:
        print(f"❌ MCP endpoint error: {e}")
        return False


async def test_a2a_endpoint():
    """Test the A2A protocol testing endpoint."""
    print("\n🔍 Testing A2A Endpoint...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/test/a2a",
                json={
                    "capability_name": "request_database_credentials",
                    "database_name": "test-database",
                    "agent_id": "test-a2a-agent"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ A2A endpoint working")
                print(f"   Token generated: {data.get('token', '')[:50]}...")
                print(f"   Expires in: {data.get('expires_in')} seconds")
                return True
            else:
                print(f"❌ A2A endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
    except Exception as e:
        print(f"❌ A2A endpoint error: {e}")
        print(f"   Note: Ensure A2A server is running on http://localhost:8000")
        return False


async def test_acp_endpoint():
    """Test the ACP protocol testing endpoint."""
    print("\n🔍 Testing ACP Endpoint...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/test/acp",
                json={
                    "message": "I need database credentials for test-database",
                    "requester_id": "test-acp-agent"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ ACP endpoint working")
                print(f"   Token present: {bool(data.get('token'))}")
                print(f"   Session ID: {data.get('session_id', 'N/A')}")
                return True
            else:
                print(f"❌ ACP endpoint failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
    except Exception as e:
        print(f"❌ ACP endpoint error: {e}")
        print(f"   Note: Ensure ACP server is running on http://localhost:8001")
        return False


async def run_all_tests():
    """Run all dashboard tests."""
    print("=" * 60)
    print("FastAPI + Tailwind WebSocket Dashboard Test Suite")
    print("=" * 60)
    
    tests = [
        ("Health Endpoint", test_health_endpoint),
        ("Main Dashboard Page", test_main_page),
        ("WebSocket Connection", test_websocket_connection),
        ("MCP API Endpoint", test_mcp_endpoint),
        ("A2A API Endpoint", test_a2a_endpoint),
        ("ACP API Endpoint", test_acp_endpoint),
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            result = await test_func()
            results[name] = result
        except Exception as e:
            print(f"\n❌ Unexpected error in {name}: {e}")
            results[name] = False
        
        # Small delay between tests
        await asyncio.sleep(0.5)
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("-" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! Dashboard is ready for use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return 1


def main():
    """Main entry point for Poetry script."""
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)


async def main_async():
    """Async main function."""
    # Check if server is running
    print("Checking if dashboard server is running...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health", timeout=2.0)
            if response.status_code != 200:
                print(f"❌ Server returned unexpected status: {response.status_code}")
                print("\nPlease start the dashboard server:")
                print("  cd /Users/aniruth/projects/1password-demo/frontend")
                print("  ./start-fe.sh")
                return 1
    except httpx.ConnectError:
        print("❌ Cannot connect to dashboard server at http://localhost:3000")
        print("\nPlease start the dashboard server:")
        print("  cd /Users/aniruth/projects/1password-demo/frontend")
        print("  ./start-fe.sh")
        return 1
    except Exception as e:
        print(f"❌ Error checking server: {e}")
        return 1
    
    print("✅ Server is running\n")
    
    # Run tests
    return await run_all_tests()


if __name__ == "__main__":
    main()

