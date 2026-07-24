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
    # Simulate a real generate() call going through provider priority.
    # AirLLM is first. Try to load its current model and generate.
    airllm = mgr.providers[mgr.primary_provider]
    print("AirLLM current model:", airllm.model)
    try:
        # Try to load + generate with a short timeout-ish approach
        meta = await asyncio.wait_for(airllm.load_model(airllm.model), timeout=20)
        print("loaded meta:", meta)
        resp = await asyncio.wait_for(airllm.generate("Say hi"), timeout=30)
        print("AirLLM generate result:", repr(resp.content[:200]))
    except Exception as e:
        print("AirLLM generate FAILED:", type(e).__name__, str(e)[:300])


if __name__ == "__main__":
    asyncio.run(main())
