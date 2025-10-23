#!/usr/bin/env python3
"""
Interactive Phase 1 Testing Script

IMPORTANT: Run this script from the backend directory using Poetry:
    cd backend
    poetry run python scripts/test_phase1.py
    
Or activate the Poetry shell first:
    cd backend
    poetry shell
    python scripts/test_phase1.py
"""
import os
import sys

# Add the parent directory to the Python path so we can import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.core.credential_manager import CredentialManager
except ImportError as e:
    print("❌ Import Error: Missing dependencies")
    print(f"   Error: {e}")
    print("\n💡 Solution: Run this script using Poetry:")
    print("   cd backend")
    print("   poetry run python scripts/test_phase1.py")
    print("\n   Or activate Poetry shell first:")
    print("   cd backend")
    print("   poetry shell")
    print("   python scripts/test_phase1.py")
    sys.exit(1)

def main():
    print("🔐 Phase 1 Validation Test")
    print("=" * 40)
    
    # Test 1: Health Check
    print("\n1. Health Check...")
    try:
        manager = CredentialManager()
        health = manager.health_check()
        print(f"   Status: {health['status']}")
        print(f"   1Password: {health['components']['onepassword']['status']}")
        print(f"   Token Manager: {health['components']['token_manager']['status']}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return
    
    # Test 2: Get user input
    print("\n2. Credential Testing...")
    resource_type = input("   Enter resource type (database/api/ssh/generic): ").strip()
    resource_name = input("   Enter 1Password item name: ").strip()
    agent_id = input("   Enter agent ID: ").strip() or "test-agent"
    
    if not resource_type or not resource_name:
        print("   ❌ Resource type and name are required")
        return
    
    # Test 3: Fetch credentials
    print(f"\n3. Fetching credentials for {resource_type}/{resource_name}...")
    try:
        creds = manager.fetch_credentials(resource_type, resource_name)
        print(f"   ✅ Success! Found {len(creds)} credential fields")
        print(f"   Fields: {list(creds.keys())}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return
    
    # Test 4: Generate token
    print(f"\n4. Generating token for agent {agent_id}...")
    try:
        token_data = manager.fetch_and_issue_token(
            resource_type=resource_type,
            resource_name=resource_name,
            agent_id=agent_id,
            ttl_minutes=5
        )
        print(f"   ✅ Token generated successfully")
        print(f"   Expires in: {token_data['expires_in']} seconds")
        print(f"   Resource: {token_data['resource']}")
    except Exception as e:
        print(f"   ❌ Token generation failed: {e}")
        return
    
    # Test 5: Validate token
    print(f"\n5. Validating token...")
    try:
        validation = manager.validate_token(token_data['token'])
        print(f"   ✅ Token is valid")
        print(f"   Agent: {validation['agent_id']}")
        print(f"   Time remaining: {validation['time_remaining']} seconds")
    except Exception as e:
        print(f"   ❌ Token validation failed: {e}")
        return
    
    # Test 6: Decrypt credentials
    print(f"\n6. Decrypting credentials...")
    try:
        decrypted = manager.get_credentials_from_token(token_data['token'])
        print(f"   ✅ Credentials decrypted successfully")
        print(f"   Available fields: {list(decrypted['credentials'].keys())}")
        
        # Show sample credentials (masked)
        for key, value in decrypted['credentials'].items():
            if isinstance(value, str) and len(value) > 4:
                masked_value = value[:2] + "*" * (len(value) - 4) + value[-2:]
                print(f"   {key}: {masked_value}")
            else:
                print(f"   {key}: {value}")
                
    except Exception as e:
        print(f"   ❌ Credential decryption failed: {e}")
        return
    
    print(f"\n🎉 Phase 1 validation completed successfully!")
    print(f"   All core components are working correctly.")

if __name__ == "__main__":
    main()
