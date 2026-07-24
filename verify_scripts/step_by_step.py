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

    resp = await agent.process("What is 2 plus 2?")
    print("CHAT:", repr(resp[:120]))

    agent.memory.remember("verif_key", "verif_val", category="notes")
    found = agent.memory.recall("verif_key")
    print("MEMORY:", found)
    agent.memory.forget("verif_key")
    print("AFTER_FORGET:", agent.memory.recall("verif_key"))

    tools = agent.tools.get_all()
    print("TOOLS:", len(tools))

    from jarvis.memory.long_term import LongTermMemory
    ltm = LongTermMemory()
    print("LTM.memories type:", type(ltm.memories).__name__)

    ollama = mgr.providers.get(mgr.primary_provider)
    if ollama and ollama.is_available:
        import time
        t0 = time.time()
        r = await ollama.generate("Say the word OK only.")
        print("OLLAMA_GENERATE:", repr(r.content[:80]), "latency:", round((time.time()-t0)*1000), "ms")

    # Test qwen3 streaming
    if ollama and ollama.is_available:
        try:
            ok, resolved = ollama.switch_model("qwen3")
            print("SWITCHED:", resolved)
            t0 = time.time()
            chunks = []
            async for chunk in ollama.stream_generate("Say hi"):
                chunks.append(chunk)
            streamed = "".join(chunks)
            print("QWEN3_STREAM:", repr(streamed[:80]), "latency:", round((time.time()-t0)*1000), "ms")
        except Exception as e:
            print("QWEN3_STREAM FAIL:", e)

asyncio.run(main())
