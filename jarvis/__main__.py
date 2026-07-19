"""
JARVIS main entry point.
"""

import asyncio
import io
import os
import sys


def _fix_encoding():
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if sys.stderr.encoding != "utf-8":
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


_fix_encoding()


def main():
    """Main entry point for JARVIS."""
    from jarvis.ui.cli import run_cli

    # Check for API key in arguments
    api_key = None
    if len(sys.argv) > 1:
        api_key = sys.argv[1]

    try:
        if len(sys.argv) > 1 and sys.argv[1] in ("ui", "web", "--ui"):
            asyncio.run(_run_ui())
        else:
            asyncio.run(run_cli(api_key=api_key))
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


async def _run_ui():
    """Launch the premium web UI."""
    from jarvis.ui.app import create_app
    from jarvis.ui.server import run_ui

    api_key = os.environ.get("JARVIS_API_KEY")
    app = create_app(api_key=api_key)
    await app.initialize()
    try:
        await run_ui(app)
    finally:
        await app.shutdown()


if __name__ == "__main__":
    main()
