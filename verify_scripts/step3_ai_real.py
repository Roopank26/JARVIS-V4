import asyncio
import io
import logging
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\Users\LENOVO\JARVIS-V4")

logging.disable(logging.CRITICAL)

async def main():
    from jarvis.core.agent import create_jarvis
    agent = create_jarvis(api_key=None)
    mgr = agent.provider_manager
    await mgr.initialize()
    print("PRIMARY:", mgr.primary_provider)

    ollama = mgr.providers.get(mgr.primary_provider)
    if ollama and ollama.is_available:
        # Use the agent's process path which worked before
        t0 = time.time()
        resp = await asyncio.wait_for(
            agent.process("What is 2 plus 2? Answer with just the number."),
            timeout=120
        )
        print("RESP:", repr(resp), "elapsed:", round(time.time()-t0, 1), "s")

        # Test memory store + recall
        agent.memory.remember("speed_test", "fast_val", category="notes")
        f = agent.memory.recall("speed_test")
        print("MEMORY:", f)

        # Test tools
        tools = agent.tools.get_all()
        print("TOOLS:", len(tools))

        # Test desktop
        try:
            from jarvis.desktop.automation import get_desktop_automation
            da = get_desktop_automation()
            wins = await da.list_windows()
            print("WINDOWS:", len(wins))
        except Exception as e:
            print("DESKTOP FAIL:", e)

asyncio.run(main())
