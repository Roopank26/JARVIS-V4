import asyncio
import io
import logging
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\Users\LENOVO\JARVIS-V4")

logging.disable(logging.CRITICAL)

results = {}

async def main():
    from jarvis.core.agent import create_jarvis
    agent = create_jarvis(api_key=None)
    mgr = agent.provider_manager
    await mgr.initialize()
    print("PRIMARY:", mgr.primary_provider)
    for pt, p in mgr.providers.items():
        print(f"  {pt}: available={p.is_available} model={p.model}")

    # STEP 3: Ollama generate
    ollama = mgr.providers.get(mgr.primary_provider)
    if ollama and ollama.is_available:
        import time
        t0 = time.time()
        r = await ollama.generate("Say the word OK only.")
        results["ollama_generate"] = "PASS" if r.content.strip() else "FAIL"
        print("OLLAMA_GENERATE:", repr(r.content[:80]), "latency_ms:", round((time.time()-t0)*1000))

    # STEP 4: Agent chat
    resp = await agent.process("What is 2 plus 2? One sentence.")
    results["agent_chat"] = "PASS" if "4" in resp else f"FAIL: {resp}"
    print("CHAT:", repr(resp[:120]))

    # STEP 5: Memory
    agent.memory.remember("verif_key", "verif_val_99", category="notes")
    found = agent.memory.recall("verif_key")
    results["memory_store_recall"] = "PASS" if found and found[0]["value"] == "verif_val_99" else "FAIL"
    print("MEMORY:", found)

    # STEP 6: Tools
    tools = agent.tools.get_all()
    results["tools_count"] = f"PASS ({len(tools)})"
    print("TOOLS:", len(tools))

    # STEP 7: LongTermMemory.memories property
    from jarvis.memory.long_term import LongTermMemory
    ltm = LongTermMemory()
    results["ltm_memories_prop"] = "PASS" if isinstance(ltm.memories, dict) else "FAIL"
    print("LTM.memories type:", type(ltm.memories).__name__)

    # STEP 8: Desktop automation
    try:
        from jarvis.desktop.automation import get_desktop_automation
        da = get_desktop_automation()
        windows = await da.list_windows()
        results["desktop_windows"] = f"PASS ({len(windows)} windows)"
        print("DESKTOP windows:", len(windows))
    except Exception as e:
        results["desktop_windows"] = f"FAIL: {e}"
        print("DESKTOP FAIL:", e)

    # STEP 9: RAG init
    try:
        from jarvis.rag import get_rag_system
        rag = get_rag_system()
        await rag.initialize()
        results["rag_init"] = "PASS"
        print("RAG initialized")
    except Exception as e:
        results["rag_init"] = f"FAIL: {e}"
        print("RAG FAIL:", e)

    # STEP 10: Plugins
    try:
        from jarvis.plugins import get_plugin_manager
        pm = get_plugin_manager()
        plugins = pm.get_plugins()
        results["plugins"] = f"PASS ({len(plugins)} plugins)"
        print("PLUGINS:", len(plugins))
    except Exception as e:
        results["plugins"] = f"FAIL: {e}"
        print("PLUGINS FAIL:", e)

    # STEP 11: Tasks
    try:
        from jarvis.tasks import get_task_manager
        get_task_manager()
        results["tasks"] = "PASS"
        print("Task manager initialized")
    except Exception as e:
        results["tasks"] = f"FAIL: {e}"
        print("TASKS FAIL:", e)

    # STEP 12: Provider manager status format
    try:
        status = mgr.format_status()
        results["provider_status"] = "PASS" if "Ollama" in status else "FAIL"
        print("Provider status format: OK")
    except Exception as e:
        results["provider_status"] = f"FAIL: {e}"
        print("Provider status FAIL:", e)

    print("\n=== RESULTS ===")
    for k, v in results.items():
        print(f"  {k}: {v}")

asyncio.run(main())
