"""
ACP Server Entry Point

Launches the ACP (Agent Communication Protocol) server with proper configuration
and environment setup.

Usage:
    python src/acp/run_acp.py [--host HOST] [--port PORT] [--log-level LEVEL] [--reload]

Examples:
    python src/acp/run_acp.py
    python src/acp/run_acp.py --port 8001 --log-level DEBUG
    python src/acp/run_acp.py --reload --log-level DEBUG
"""

import argparse
import os
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

import uvicorn
from dotenv import load_dotenv
import logging

from src.core.logging_config import configure_logging

# Load environment variables
load_dotenv()

# Setup logging
configure_logging(log_level="INFO")
logger = logging.getLogger("acp-launcher")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="1Password ACP Credential Broker Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/acp/run_acp.py
  python src/acp/run_acp.py --port 8001
  python src/acp/run_acp.py --reload --log-level DEBUG
  python src/acp/run_acp.py --host 127.0.0.1 --port 9000
        """,
    )

    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Server host address (default: 0.0.0.0)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Server port (default: 8001 or ACP_PORT env var)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level (default: info)",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1, ignored with --reload)",
    )

    return parser.parse_args()


def validate_environment():
    """Validate required environment variables."""
    required_vars = [
        "OP_CONNECT_HOST",
        "OP_CONNECT_TOKEN",
        "OP_VAULT_ID",
        "JWT_SECRET_KEY",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error("❌ Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"   - {var}")
        logger.error("")
        logger.error("Please set these variables in your .env file or environment.")
        sys.exit(1)

    logger.info("✅ All required environment variables present")


def main():
    """Main entry point."""
    args = parse_args()

    # Determine port
    port = args.port or int(os.getenv("ACP_PORT", "8001"))

    # Validate environment
    logger.info("=" * 60)
    logger.info("  1Password ACP Credential Broker Server")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Validating environment...")
    validate_environment()
    logger.info("")

    # Display configuration
    logger.info("Configuration:")
    logger.info(f"  Host:             {args.host}")
    logger.info(f"  Port:             {port}")
    logger.info(f"  Log Level:        {args.log_level.upper()}")
    logger.info(f"  Connect Host:     {os.getenv('OP_CONNECT_HOST')}")
    logger.info(f"  Vault ID:         {os.getenv('OP_VAULT_ID')}")
    logger.info(f"  Workers:          {args.workers if not args.reload else 1}")
    if args.reload:
        logger.info(f"  Auto-reload:      Enabled")
    logger.info("")
    logger.info("API Endpoints:")
    logger.info(f"  Agents List:      http://{args.host}:{port}/agents")
    logger.info(f"  Run Agent:        http://{args.host}:{port}/run")
    logger.info(f"  Session History:  http://{args.host}:{port}/sessions/{{session_id}}")
    logger.info(f"  Health Check:     http://{args.host}:{port}/health")
    logger.info(f"  API Docs:         http://{args.host}:{port}/docs")
    logger.info("")
    logger.info("=" * 60)
    logger.info("")

    # Prepare uvicorn configuration
    config = {
        "app": "src.acp.acp_server:app",
        "host": args.host,
        "port": port,
        "log_level": args.log_level,
    }

    if args.reload:
        config["reload"] = True
    else:
        config["workers"] = args.workers

    # Start server
    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Shutting down ACP server gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

