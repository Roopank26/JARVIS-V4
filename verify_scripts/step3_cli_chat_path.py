import asyncio
import sys

sys.path.insert(0, r"C:\Users\LENOVO\JARVIS-V4")

from jarvis.core.agent import create_jarvis


async def main():
    # No API key at all => SimpleLLMClient backend = groq with no key
    agent = create_jarvis(api_key=None)
    mgr = agent.provider_manager
    # Force only Ollama available, initialize manager (selects primary)
    ok = await mgr.initialize()
    print("ProviderManager.initialize:", ok, "primary:", mgr.primary_provider)
    print("Provider status:", mgr.format_status())

    # Now ask a real chat question - which path does process() use?
    # Use a clearly non-command question.
    try:
        resp = await agent.process("What is the capital of France? Answer in one sentence.")
        print("=== CHAT RESPONSE (CLI process path) ===")
        print(repr(resp))
    except Exception as e:
        print("CHAT ERROR:", repr(e))


if __name__ == "__main__":
    asyncio.run(main())
