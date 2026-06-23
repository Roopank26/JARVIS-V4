"""
JARVIS main entry point.
"""

import sys
import asyncio


def main():
    """Main entry point for JARVIS."""
    from jarvis.ui.cli import run_cli

    # Check for API key in arguments
    api_key = None
    if len(sys.argv) > 1:
        api_key = sys.argv[1]

    try:
        asyncio.run(run_cli(api_key=api_key))
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
