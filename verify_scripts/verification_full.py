import asyncio
import io
import logging
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\Users\LENOVO\JARVIS-V4")

logging.disable(logging.CRITICAL)

results = {}

async def main():
    from jarvis.ui.cli import JarvisCLI

    cli = JarvisCLI()
    await cli.initialize(api_key=None)
    agent = cli.agent

    mgr = agent.provider_manager
    await mgr.initialize()
    print("PRIMARY:", mgr.primary_provider)

    # 1. AI Chat
    t0 = time.time()
    resp = await asyncio.wait_for(
        agent.process("What is 2 plus 2? Answer with just the number."),
        timeout=120
    )
    results["ai_chat"] = "PASS" if "4" in resp else "FAIL"
    print(f"CHAT: {repr(resp[:80])} ({round(time.time()-t0,1)}s)")

    # 2. Memory
    agent.memory.remember("test_chat_key", "chat_val_42", category="notes")
    found = agent.memory.recall("test_chat_key")
    results["memory"] = "PASS" if found and found[0]["value"] == "chat_val_42" else "FAIL"
    print(f"MEMORY: {found}")

    # 3. Tools
    tools = agent.tools.get_all()
    results["tools"] = f"PASS ({len(tools)})"
    print(f"TOOLS: {len(tools)}")
    if tools:
        print(f"  First: {tools[0].name}")

    # 4. RAG init + search
    try:
        from jarvis.rag import get_rag_system
        rag = get_rag_system()
        await rag.initialize()
        results["rag"] = "PASS"
        print("RAG: initialized")
    except Exception as e:
        results["rag"] = f"FAIL: {e}"
        print(f"RAG FAIL: {e}")

    # 5. Desktop automation
    try:
        from jarvis.desktop.automation import get_desktop_automation
        da = get_desktop_automation()
        wins = await da.list_windows()
        results["desktop"] = f"PASS ({len(wins)} windows)"
        print(f"DESKTOP: {len(wins)} windows")
    except Exception as e:
        results["desktop"] = f"FAIL: {e}"
        print(f"DESKTOP FAIL: {e}")

    # 6. Plugins
    try:
        from jarvis.plugins import get_plugin_manager
        pm = get_plugin_manager()
        plugins = pm.get_plugins()
        results["plugins"] = f"PASS ({len(plugins)})"
        print(f"PLUGINS: {len(plugins)}")
    except Exception as e:
        results["plugins"] = f"FAIL: {e}"
        print(f"PLUGINS FAIL: {e}")

    # 7. Tasks
    try:
        from jarvis.tasks import get_task_manager
        get_task_manager()
        results["tasks"] = "PASS"
        print("TASKS: initialized")
    except Exception as e:
        results["tasks"] = f"FAIL: {e}"
        print(f"TASKS FAIL: {e}")

    # 8. Provider status
    try:
        mgr.format_status()
        results["provider_status"] = "PASS"
        print("PROVIDER_STATUS: OK")
    except Exception as e:
        results["provider_status"] = f"FAIL: {e}"
        print(f"PROVIDER_STATUS FAIL: {e}")

    # 9. Ollama streaming (deepseek-r1 is slow; use qwen3)
    if mgr.primary_provider:
        p = mgr.providers.get(mgr.primary_provider)
        if p and p.is_available and hasattr(p, "switch_model"):
            try:
                ok, resolved = p.switch_model("qwen3")
                print(f"Switched to qwen3: {resolved}")
                t0 = time.time()
                chunks = []
                async for chunk in p.stream_generate("Say OK"):
                    chunks.append(chunk)
                    if time.time() - t0 > 90:
                        break
                streamed = "".join(chunks)
                results["ollama_streaming"] = "PASS" if streamed.strip() else "FAIL"
                print(f"QWEN3_STREAM: {repr(streamed[:80])}")
            except Exception as e:
                results["ollama_streaming"] = f"FAIL: {e}"
                print(f"QWEN3_STREAM FAIL: {e}")

    # 10. Doctor
    try:
        from jarvis.diagnostics import run_jarvis_doctor
        await asyncio.wait_for(run_jarvis_doctor(), timeout=60)
        results["doctor"] = "PASS"
        print("DOCTOR: completed")
    except Exception as e:
        results["doctor"] = f"FAIL: {e}"
        print(f"DOCTOR FAIL: {e}")

    print("\n=== RESULTS ===")
    for k, v in results.items():
        print(f"  {k}: {v}")

asyncio.run(main())
