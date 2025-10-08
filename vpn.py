#!/usr/bin/env python3
"""
cURL Command Executor
Accepts a cURL command from the user (single or multi-line) and executes it.
"""

import argparse
import subprocess
import sys


test_curl_command = """
curl --location 'https://api.restful-api.dev/objects'
"""


def print_banner():
    """Print a welcome banner."""
    print("=" * 60)
    print("cURL Command Executor")
    print("=" * 60)
    print()


def get_curl_command():
    """
    Get cURL command from user.
    Supports both single-line and multi-line input.
    """
    print("Enter your cURL command below.")
    print("For multi-line commands, press Enter after each line.")
    print("When done, press Enter on an empty line to execute.")
    print("-" * 60)

    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "":
                if lines:  # Only break if we have at least one line
                    break
                continue  # Skip empty lines at the beginning
            lines.append(line.strip())
        except EOFError:
            break

    # Join all lines into a single command
    curl_command = " ".join(lines)
    return curl_command


def execute_curl(curl_command):
    """
    Execute the cURL command and display results.

    Args:
        curl_command: The cURL command string to execute
    """
    if not curl_command:
        print("Error: No command provided.")
        return

    print()
    print("=" * 60)
    print("Executing command:")
    print(curl_command)
    print("=" * 60)
    print()

    try:
        # Execute the command
        result = subprocess.run(
            curl_command,
            shell=True,
            check=True,
            text=True,
            capture_output=True,
            timeout=60,  # 60 second timeout
        )

        # Display output
        if result.stdout:
            print("Output:")
            print("-" * 60)
            print(result.stdout)
        else:
            print("Command executed successfully with no output.")

        # Display any warnings/errors (stderr)
        if result.stderr:
            print()
            print("Warnings/Additional Info:")
            print("-" * 60)
            print(result.stderr)

    except subprocess.TimeoutExpired:
        print("Error: Command timed out after 60 seconds.")
        sys.exit(1)

    except subprocess.CalledProcessError as e:
        print("Error: Command failed with non-zero exit code.")
        print("-" * 60)
        if e.stdout:
            print("Output:")
            print(e.stdout)
        if e.stderr:
            print()
            print("Error Details:")
            print(e.stderr)
        sys.exit(e.returncode)

    except KeyboardInterrupt:
        print()
        print("Execution interrupted by user.")
        sys.exit(130)

    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")
        sys.exit(1)

    print()
    print("=" * 60)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="cURL Command Executor - Execute cURL commands and display output"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Execute the predefined test cURL command instead of prompting for input",
    )
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_arguments()

    print_banner()

    if args.test:
        # Use the test command
        print("Running test cURL command...")
        print("-" * 60)
        # Process multi-line command by removing newlines and extra spaces
        curl_command = " ".join(
            line.strip()
            for line in test_curl_command.strip().splitlines()
            if line.strip()
        )
    else:
        # Get command from user
        curl_command = get_curl_command()

    execute_curl(curl_command)


if __name__ == "__main__":
    main()
