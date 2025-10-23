#!/usr/bin/env python3
"""
Entry point for running the Streamlit dashboard.
Usage: python -m src.ui.run_dashboard
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """Run the Streamlit dashboard."""
    # Get the dashboard file path
    dashboard_path = Path(__file__).parent / "dashboard.py"

    if not dashboard_path.exists():
        print(f"Error: Dashboard file not found at {dashboard_path}")
        sys.exit(1)

    # Check if .env file exists
    env_file = Path(__file__).parent.parent.parent / ".env"
    if not env_file.exists():
        print(f"Warning: .env file not found at {env_file}")
        print("Please copy .env.example to .env and configure it.")
        print("")

    # Streamlit command
    cmd = [
        "streamlit",
        "run",
        str(dashboard_path),
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]

    print("=" * 60)
    print("  1Password Credential Broker Dashboard")
    print("=" * 60)
    print("")
    print("Starting Streamlit dashboard...")
    print(f"Dashboard will be available at: http://localhost:8501")
    print("")
    print("Press Ctrl+C to stop the dashboard")
    print("")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")
    except FileNotFoundError:
        print("\nError: Streamlit not found.")
        print("Please install it with: poetry install --extras ui")
        sys.exit(1)


if __name__ == "__main__":
    main()

