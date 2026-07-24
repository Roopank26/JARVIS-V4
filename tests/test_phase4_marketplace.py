"""
Tests for JARVIS Phase 4 — Plugin Marketplace.
"""


def test_marketplace_singleton():
    from jarvis.plugins.marketplace import get_marketplace
    mp = get_marketplace()
    assert mp is not None


def test_marketplace_register():
    from jarvis.plugins.marketplace import PluginCapabilities, get_marketplace
    from jarvis.plugins.plugin_manager import PluginInfo
    mp = get_marketplace()
    info = PluginInfo(id="test_plugin", name="Test Plugin", version="1.0.0", description="A test plugin")
    caps = PluginCapabilities(capabilities=["search"], required_permissions=[])
    mp.register_local("test_plugin", info, caps)
    found = mp.discover("test_plugin")
    assert found is not None
    assert found["id"] == "test_plugin"


def test_marketplace_search():
    from jarvis.plugins.marketplace import get_marketplace
    from jarvis.plugins.plugin_manager import PluginInfo
    mp = get_marketplace()
    info = PluginInfo(id="search_plugin", name="Search Helper", version="1.0.0", description="Helps with searches")
    mp.register_local("search_plugin", info)
    results = mp.search("search")
    assert len(results) == 1


def test_capability_registry():
    from jarvis.plugins.marketplace import EnhancedPluginCapability
    registry = EnhancedPluginCapability()
    registry.register("plugin_a", ["read", "write"])
    registry.register("plugin_b", ["read"])
    assert registry.get_plugin_capabilities("plugin_a") == ["read", "write"]
    found = registry.find_plugins_by_capability("read")
    assert "plugin_a" in found
    assert "plugin_b" in found


def test_plugin_sandbox():
    from jarvis.plugins.marketplace import PermissionLevel, PluginSandbox
    sandbox = PluginSandbox(permissions=[PermissionLevel.READ, PermissionLevel.EXECUTE])
    assert sandbox.allows(PermissionLevel.READ)
    assert sandbox.allows(PermissionLevel.EXECUTE)
    assert not sandbox.allows(PermissionLevel.SYSTEM)
