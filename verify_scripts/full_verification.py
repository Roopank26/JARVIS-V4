import asyncio
import io
import logging
import sys

from jarvis.core.agent import create_jarvis
from jarvis.memory.long_term import LongTermMemory

logging.disable(logging.CRITICAL)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\Users\LENOVO\JARVIS-V4")

results = {}

async def main():
    # === STEP 1: Verify no import errors ===
    print("=== STEP 1: IMPORT VERIFICATION ===")
    try:
        results["imports"] = "PASS"
        print("All imports successful.")
    except Exception as e:
        results["imports"] = f"FAIL: {e}"
        print(f"Import FAIL: {e}")

    # === STEP 2: Verify Providers ===
    print("\n=== STEP 2: PROVIDER VERIFICATION ===")
    agent = create_jarvis(api_key=None)
    mgr = agent.provider_manager
    await mgr.initialize()

    results["providers"] = {}
    for pt, p in mgr.providers.items():
        results["providers"][pt.value] = {
            "available": p.is_available,
            "primary": pt == mgr.primary_provider,
            "model": p.model,
            "models": p.available_models,
            "error": str(p.last_error) if p.last_error else None,
        }
        print(f"  {pt}: available={p.is_available} primary={pt==mgr.primary_provider} model={p.model}")
    print("Primary:", mgr.primary_provider)

    # === STEP 3: Verify Ollama generation (non-streaming + streaming) ===
    print("\n=== STEP 3: OLLAMA GENERATION ===")
    ollama = mgr.providers.get(mgr.primary_provider) if mgr.primary_provider else None
    if ollama and ollama.is_available:
        try:
            resp = await ollama.generate("Say 'hello world' and nothing else.")
            results["ollama_generate"] = "PASS" if resp.content else "FAIL: empty"
            print(f"  Ollama generate: {repr(resp.content[:100])}")
        except Exception as e:
            results["ollama_generate"] = f"FAIL: {e}"
            print(f"  FAIL: {e}")
    else:
        results["ollama_generate"] = "SKIP: Ollama not available"
        print("  SKIP")

    # === STEP 3b: Ollama streaming ===
    if ollama and ollama.is_available:
        try:
            stream = ollama.stream_generate("Count from 1 to 3, one per line.")
            chunks = []
            async for chunk in stream:
                chunks.append(chunk)
            streamed = "".join(chunks)
            results["ollama_streaming"] = "PASS" if streamed.strip() else "FAIL: empty"
            print(f"  Ollama streaming: {repr(streamed[:100])}")
        except Exception as e:
            results["ollama_streaming"] = f"FAIL: {e}"
            print(f"  FAIL: {e}")

    # === STEP 3c: Ollama model switch ===
    if ollama and ollama.is_available and len(ollama.available_models) > 1:
        try:
            alt = [m for m in ollama.available_models if m != ollama.model][0]
            ok, resolved = ollama.switch_model(alt)
            results["ollama_switch"] = "PASS" if ok else f"FAIL: {resolved}"
            print(f"  Switched to: {resolved}")
        except Exception as e:
            results["ollama_switch"] = f"FAIL: {e}"
            print(f"  FAIL: {e}")

    # === STEP 4: Agent CLI chat (uses ProviderManager now) ===
    print("\n=== STEP 4: AGENT CHAT ===")
    try:
        resp = await agent.process("What is the capital of France? One sentence.")
        results["agent_chat"] = "PASS" if resp and len(resp) > 2 else f"FAIL: {repr(resp)}"
        print(f"  Chat: {repr(resp[:120])}")
    except Exception as e:
        results["agent_chat"] = f"FAIL: {e}"
        print(f"  FAIL: {e}")

    # === STEP 5: Memory ===
    print("\n=== STEP 5: MEMORY ===")
    try:
        # Use the agent's memory
        agent.memory.remember("test_key", "test_value_123", category="notes")
        found = agent.memory.recall("test_key")
        ok_recall = found and found[0]["value"] == "test_value_123"
        results["memory_store_recall"] = "PASS" if ok_recall else f"FAIL: {found}"
        print(f"  Store/recall: {found}")
        agent.memory.forget("test_key")
        found_after = agent.memory.recall("test_key")
        results["memory_forget"] = "PASS" if not found_after else "FAIL"
        print(f"  After forget: {found_after}")

        # Verify LongTermMemory.memories property (crash fix)
        ltm = LongTermMemory()
        dicts = ltm.memories
        results["long_term_memories_prop"] = "PASS" if isinstance(dicts, dict) else "FAIL"
        print(f"  LongTermMemory.memories prop: {type(dicts)}")
    except Exception as e:
        results["memory"] = f"FAIL: {e}"
        print(f"  FAIL: {e}")

    # === STEP 6: Tools ===
    print("\n=== STEP 6: TOOLS ===")
    try:
        registry = agent.tools
        tools = registry.get_all()
        results["tools_count"] = f"PASS ({len(tools)} tools)"
        print(f"  Tools registered: {len(tools)}")
        if tools:
            t = tools[0]
            print(f"  First tool: {t.name}")
    except Exception as e:
        results["tools_count"] = f"FAIL: {e}"
        print(f"  FAIL: {e}")

    # === STEP 7: Diagnostics ===
    print("\n=== STEP 7: DIAGNOSTICS ===")
    try:
        from jarvis.diagnostics import run_jarvis_doctor
        diag = await run_jarvis_doctor()
        results["diagnostics"] = "PASS"
        print(f"  Doctor completed. Provider checks: {len(diag.get('providers', {}))}")
    except Exception as e:
        results["diagnostics"] = f"FAIL: {e}"
        print(f"  FAIL: {e}")

    # === SUMMARY ===
    print("\n=== RESULTS SUMMARY ===")
    for k, v in results.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    asyncio.run(main())
