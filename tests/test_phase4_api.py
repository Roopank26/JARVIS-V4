"""
Tests for JARVIS Phase 4 — Unified API.
"""


def test_unified_api_singleton():
    from jarvis.api.os import get_unified_api, reset_unified_api
    api = get_unified_api()
    assert api is get_unified_api()
    reset_unified_api()


def test_unified_api_register():
    from jarvis.api.os import UnifiedAPI
    api = UnifiedAPI()
    api.register("test_module", None, capabilities=["test"])
    info = api.get_module_info("test_module")
    assert info is not None
    assert info.name == "test_module"


def test_unified_api_list_modules():
    from jarvis.api.os import UnifiedAPI
    api = UnifiedAPI()
    api.register("mod1", None)
    modules = api.list_modules()
    assert len(modules) == 1
    assert modules[0].name == "mod1"
