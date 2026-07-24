"""
Tests for Phase 2.0 - Capability Discovery Service.

Validates capability inventory for providers, tools, plugins,
system, hardware, services, filesystem, and network.
"""

import pytest

from jarvis.core.capabilities import Capabilities, CapabilityDiscovery, get_capability_discovery


class TestCapabilityDiscovery:
    @pytest.mark.asyncio
    async def test_discover_returns_capabilities(self):
        cd = CapabilityDiscovery()
        caps = await cd.discover()
        assert isinstance(caps, Capabilities)
        assert isinstance(caps.providers, list)
        assert isinstance(caps.tools, list)
        assert isinstance(caps.system, dict)

    @pytest.mark.asyncio
    async def test_discover_system_info(self):
        cd = CapabilityDiscovery()
        caps = await cd.discover()
        assert "os" in caps.system

    @pytest.mark.asyncio
    async def test_discover_hardware_info(self):
        cd = CapabilityDiscovery()
        caps = await cd.discover()
        assert "cpu_count" in caps.hardware

    @pytest.mark.asyncio
    async def test_discover_tools_from_registry(self):
        cd = CapabilityDiscovery()
        caps = await cd.discover()
        assert isinstance(caps.tools, list)

    @pytest.mark.asyncio
    async def test_discover_network(self):
        cd = CapabilityDiscovery()
        caps = await cd.discover()
        assert "internet_available" in caps.network

    @pytest.mark.asyncio
    async def test_discover_filesystem(self):
        cd = CapabilityDiscovery()
        caps = await cd.discover()
        assert "cwd_writable" in caps.filesystem
        assert "jarvis_dir" in caps.filesystem

    @pytest.mark.asyncio
    async def test_discover_cache_invalidation(self):
        cd = CapabilityDiscovery()
        caps1 = await cd.discover()
        cd.invalidate_cache()
        caps2 = await cd.discover()
        assert isinstance(caps1, Capabilities)
        assert isinstance(caps2, Capabilities)

    def test_capabilities_prompt_context(self):
        caps = Capabilities(
            providers=[{"name": "ollama", "status": "ok"}],
            tools=["read_file", "write_file"],
            system={"os": "Windows"},
        )
        out = caps.to_prompt_context()
        assert "ollama" in out
        assert "read_file" in out
        assert "Windows" in out

    def test_get_capability_discovery_singleton(self):
        cd1 = get_capability_discovery()
        cd2 = get_capability_discovery()
        assert cd1 is cd2
