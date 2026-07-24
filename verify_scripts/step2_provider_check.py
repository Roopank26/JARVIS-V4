import asyncio
import sys

sys.path.insert(0, r"C:\Users\LENOVO\JARVIS-V4")

from jarvis.api.providers import (
    GroqProvider,
    LLMConfig,
    OllamaProvider,
    ProviderType,
    get_provider_manager,
)


async def main():
    mgr = get_provider_manager()
    ollama_cfg = LLMConfig(
        provider=ProviderType.OLLAMA, base_url="http://localhost:11434", timeout=120.0
    )
    mgr.add_provider(OllamaProvider(ollama_cfg))
    mgr.add_provider(
        GroqProvider(
            LLMConfig(provider=ProviderType.GROQ, model="llama-3.3-70b-versatile", api_key="test")
        )
    )

    print("=== Health checks ===")
    ok_ollama = await mgr.providers[ProviderType.OLLAMA].check_health()
    print("Ollama health:", ok_ollama)
    print("Ollama models:", mgr.providers[ProviderType.OLLAMA].available_models)
    try:
        ok_groq = await mgr.providers[ProviderType.GROQ].check_health()
        print("Groq health:", ok_groq, "err:", mgr.providers[ProviderType.GROQ].last_error)
    except Exception as e:
        print("Groq check exception:", repr(e))


if __name__ == "__main__":
    asyncio.run(main())
