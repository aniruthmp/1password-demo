#!/usr/bin/env python3
"""
MCP Server Entry Point
Runs the 1Password Credential Broker MCP server with configurable transport options.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.mcp_server import run_mcp_server


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure logging for the MCP server.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),  # Log to stderr to keep stdout clean for MCP
        ],
    )


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="1Password Credential Broker MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default stdio transport
  python src/mcp/run_mcp.py
  
  # Run with debug logging
  python src/mcp/run_mcp.py --log-level DEBUG
  
  # Run with INFO logging (default)
  python src/mcp/run_mcp.py --log-level INFO
        """,
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: INFO)",
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="1Password Credential Broker MCP Server v1.0.0",
        help="Show version information",
    )
    
    return parser.parse_args()


async def main() -> None:
    """
    Main entry point for the MCP server.
    """
    args = parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("1Password Credential Broker - MCP Server")
    logger.info("=" * 60)
    logger.info(f"Version: 1.0.0")
    logger.info(f"Transport: stdio")
    logger.info(f"Log Level: {args.log_level}")
    logger.info("=" * 60)
    
    try:
        # Run the MCP server
        await run_mcp_server()
    except KeyboardInterrupt:
        logger.info("\nMCP Server shutting down gracefully (KeyboardInterrupt)...")
    except Exception as e:
        logger.error(f"MCP Server failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

