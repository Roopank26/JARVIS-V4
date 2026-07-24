import asyncio
import io
import logging
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\Users\LENOVO\JARVIS-V4")

logging.disable(logging.CRITICAL)

async def main():
    from jarvis.core.agent import create_jarvis
    agent = create_jarvis(api_key=None)
    mgr = agent.provider_manager
    await mgr.initialize()
    print("PRIMARY:", mgr.primary_provider)
    for pt, p in mgr.providers.items():
        print(f"  {pt}: available={p.is_available} model={p.model}")

    # Skip Ollama generate with deepseek (too slow); use qwen3 instead
    ollama = mgr.providers.get(mgr.primary_provider)
    if ollama and ollama.is_available and len(ollama.available_models) > 1:
        alt = [m for m in ollama.available_models if m != ollama.model][0]
        ollama.switch_model(alt)
        print("Switched to:", ollama.model)

    if ollama and ollama.is_available:
        import time
        t0 = time.time()
        r = await asyncio.wait_for(ollama.generate("Say hi in 2 words."), timeout=60)
        print("OLLAMA_GENERATE:", repr(r.content[:80]), "latency_ms:", round((time.time()-t0)*1000))

asyncio.run(main())
