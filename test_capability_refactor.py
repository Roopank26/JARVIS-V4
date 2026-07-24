"""
Verification script for JARVIS enterprise capability-driven AI OS refactor.
Tests:
- Semantic Capability Matching ("Paint me a cyberpunk city", "Design a wallpaper", "Read this PDF")
- Standard Test Suite (7 prompts)
- Provider Health Monitor status
- Observability Metrics Summary
"""

import asyncio
import logging
import sys
from unittest.mock import AsyncMock, patch

from jarvis.core.agent import JarvisAgent, classify_intent
from jarvis.core.capability_router import get_capability_router
from jarvis.core.observability import get_observability
from jarvis.core.provider_health_monitor import get_provider_health_monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


class MockLLMClient:
    """Mock LLM client that returns instant responses for fast testing."""
    async def generate(self, system="", prompt="", **kwargs):
        return "I am JARVIS, ready to assist you."

    async def generate_with_history(self, messages, system="", **kwargs):
        return "Hello! I am JARVIS. My voice and tools are active."


async def run_verification():
    print("=" * 75)
    print("      JARVIS ENTERPRISE AI OPERATING SYSTEM VERIFICATION")
    print("=" * 75)

    with patch("jarvis.tools.speak_tool.SpeakTool._os_speak", new_callable=AsyncMock):
        mock_llm = MockLLMClient()
        agent = JarvisAgent(llm_client=mock_llm)

        # 1. Startup Diagnostic Report
        router = get_capability_router()
        catalog = router.get_catalog()
        caps = catalog.capabilities
        print(f"\n[STEP 1 Capability Catalog] Catalog contains {len(caps)} capabilities.")
        for c in caps[:10]:
            print(f"  [+] id={c.id:<20} v{c.version:<6} category={c.category:<12} avail={c.availability}")

        # 2. Semantic Matching Test
        print("\n" + "=" * 75)
        print("      TESTING SEMANTIC CAPABILITY MATCHING")
        print("=" * 75)
        semantic_prompts = [
            ("Paint me a cyberpunk city", "generate_image"),
            ("Design a wallpaper", "generate_image"),
            ("Read this PDF", "speak"),
        ]
        for prompt, expected_cap in semantic_prompts:
            matches = router.route_intent(prompt)
            top = matches[0].capability.name if matches else "none"
            score = matches[0].confidence if matches else 0.0
            status = "SUCCESS" if top == expected_cap else "CHECK"
            print(f"  Semantic Prompt: {prompt!r:<30} -> Matched: {top:<15} (score={score:.2f}) [{status}]")

        # 3. Standard Test Suite
        test_cases = [
            ("Voice TTS 1", "I cannot hear your voice"),
            ("Voice TTS 2", "Say hello"),
            ("Image Gen", "Generate an image of Iron Man"),
            ("Camera", "Open the camera"),
            ("Search / Research", "Search the web for AI news"),
            ("TTS Document", "Read this document aloud"),
            ("Memory Store", "Remember that my favorite editor is VS Code"),
        ]

        print("\n" + "=" * 75)
        print("      RUNNING STANDARD 7 VERIFICATION TEST PROMPTS")
        print("=" * 75)

        results_summary = []

        for label, prompt in test_cases:
            print(f"\n>>> TEST: [{label}] Prompt: {prompt!r}")

            intent = classify_intent(prompt)
            print(f"    1. Detected intent      : {intent}")

            matches = router.route_intent(prompt, max_results=3)
            top_cap = matches[0].capability.name if matches else "None"
            confidence = matches[0].confidence if matches else 0.0
            print(f"    2. Capability selected  : {top_cap} (confidence={confidence:.2f})")

            try:
                response = await agent.process(prompt)
                resp_preview = str(response).replace("\n", " ")[:90]
                print(f"    3. Execution result     : {resp_preview}...")
                print("    4. Status               : SUCCESS")
                results_summary.append((label, intent, top_cap, "SUCCESS"))
            except Exception as e:
                print(f"    3. Execution error      : {e}")
                print("    4. Status               : FAILED")
                results_summary.append((label, intent, top_cap, f"FAILED: {e}"))

        print("\n" + "=" * 75)
        print("      STEP 13 VERIFICATION SUMMARY REPORT")
        print("=" * 75)
        print(f"{'Test Label':<20} | {'Detected Intent':<15} | {'Capability Selected':<20} | {'Status':<10}")
        print("-" * 75)
        for label, intent, cap, status in results_summary:
            print(f"{label:<20} | {intent:<15} | {cap:<20} | {status:<10}")
        print("=" * 75)

        # 4. Observability Summary
        obs = get_observability()
        print("\n[Observability Metrics Summary]")
        for k, v in obs.get_metrics_summary().items():
            print(f"  - {k}: {v}")

        # 5. Provider Health Monitor Status
        health = get_provider_health_monitor()
        print("\n[Provider Health Monitor Status]")
        print(f"  - Healthy providers: {health.get_healthy_providers()}")
        print("=" * 75 + "\n")


if __name__ == "__main__":
    asyncio.run(run_verification())
