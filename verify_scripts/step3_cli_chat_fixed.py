import asyncio
import io
import logging
import sys

from jarvis.core.agent import create_jarvis

logging.disable(logging.CRITICAL)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\Users\LENOVO\JARVIS-V4")


async def main():
    agent = create_jarvis(api_key=None)
    mgr = agent.provider_manager
    await mgr.initialize()
    print("PRIMARY:", mgr.primary_provider)
    for pt, p in mgr.providers.items():
        print(f"  {pt}: available={p.is_available} model={p.model} err={p.last_error}")

    resp = await agent.process("What is 2 plus 2? Just give the number.")
    print("=== CHAT RESPONSE ===")
    print(repr(resp))


if __name__ == "__main__":
    asyncio.run(main())
