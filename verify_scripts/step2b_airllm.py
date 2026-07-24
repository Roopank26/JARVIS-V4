import asyncio
import io
import sys

from jarvis.core.agent import create_jarvis
from jarvis.providers.airllm import utils as airllm_utils

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"C:\Users\LENOVO\JARVIS-V4")


async def main():
    agent = create_jarvis(api_key=None)
    mgr = agent.provider_manager
    print("provider types registered:", list(mgr.providers.keys()))
    print("AirLLM runtime available?:", airllm_utils.is_airllm_available())
    try:
        print("AirLLM missing reqs:", airllm_utils.get_airllm_requirements())
    except Exception as e:
        print("reqs err:", e)
    ok = await mgr.initialize()
    print("ProviderManager.initialize:", ok)
    print("primary:", mgr.primary_provider)
    import json
    print("diag:", json.dumps(mgr.get_startup_diagnostics(), default=str))
    for pt, p in mgr.providers.items():
        print(f"  {pt}: available={p.is_available} model={p.model} models={p.available_models} err={p.last_error}")


if __name__ == "__main__":
    asyncio.run(main())
