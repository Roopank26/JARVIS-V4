"""
JARVIS Premium Web UI server.

A small, dependency-light async web server (aiohttp) that serves the desktop
SPA and bridges it to the orchestrator via WebSocket + JSON endpoints.

Features served:
- Dashboard with live metrics (Feature 3)
- Reasoning stages (Feature 2) and streaming responses (Feature 7)
- Workflow timeline (Feature 9) via events
- Tool Library with search/filter/favorites/recent (Feature 4)
- Command palette backend (Feature 5)
- Background task manager + queue (Feature 8/11)
- Activity center (Feature 12)
- Smart suggestions (Feature 13)
- Friendly errors (Feature 16)

Privacy-first / local-first: everything runs on 127.0.0.1, no external calls
except the LLM provider the user already configured.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from jarvis.events import get_event_bus
from jarvis.ui.app import JarvisApp

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8742


class UIServer:
    """Local web server hosting the premium JARVIS UI."""

    def __init__(
        self,
        app: JarvisApp,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        self.app = app
        self.host = host
        self.port = port
        self._runner: Any = None
        self._site: Any = None
        self._bus = get_event_bus()
        self._ws_clients: set = set()
        self._unsub = None

    # ---- Lifecycle ----
    async def start(self) -> None:
        from aiohttp import web

        self.app_ = web.Application()
        self.app_.router.add_get("/", self._index)
        self.app_.router.add_get("/favicon.ico", self._favicon)
        self.app_.router.add_get("/ws", self._ws_handler)
        self.app_.router.add_get("/api/status", self._api_status)
        self.app_.router.add_get("/api/providers", self._api_providers)
        self.app_.router.add_post("/api/chat", self._api_chat)
        self.app_.router.add_get("/api/tools", self._api_tools)
        self.app_.router.add_post("/api/tools/favorite", self._api_tools_favorite)
        self.app_.router.add_get("/api/palette", self._api_palette)
        self.app_.router.add_get("/api/tasks", self._api_tasks)
        self.app_.router.add_post("/api/tasks/{id}/{action}", self._api_task_action)
        self.app_.router.add_get("/api/activity", self._api_activity)
        self.app_.router.add_get("/api/suggestions", self._api_suggestions)
        self.app_.router.add_static("/static", STATIC_DIR, show_index=False)

        self._unsub = self._bus.subscribe(None, self._on_event)

        self._runner = web.AppRunner(self.app_)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()
        logger.info(f"JARVIS UI available at http://{self.host}:{self.port}")

    async def stop(self) -> None:
        if self._unsub:
            self._unsub()
        for ws in list(self._ws_clients):
            try:
                await ws.close()
            except Exception:
                pass
        if self._runner:
            await self._runner.cleanup()

    # ---- Event broadcast ----
    def _on_event(self, event: Any) -> None:
        if not self._ws_clients:
            return
        payload = json.dumps({
            "type": event.type.value,
            "data": event.data,
            "ts": event.timestamp,
        })
        for ws in list(self._ws_clients):
            try:
                asyncio.create_task(ws.send_str(payload))
            except Exception:
                self._ws_clients.discard(ws)

    # ---- Handlers ----
    async def _index(self, request: Any) -> Any:
        from aiohttp import web

        html_path = STATIC_DIR / "index.html"
        if html_path.exists():
            return web.FileResponse(html_path)
        return web.Response(text="<h1>JARVIS UI not built</h1>", content_type="text/html")

    async def _favicon(self, request: Any) -> Any:
        from aiohttp import web

        # Lightweight inline SVG favicon so the browser makes no failing request.
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
            "<rect width='32' height='32' rx='7' fill='#0b1120'/>"
            "<text x='16' y='22' font-size='18' text-anchor='middle' "
            "fill='#00e5ff' font-family='monospace'>J</text></svg>"
        )
        return web.Response(text=svg, content_type="image/svg+xml")

    async def _ws_handler(self, request: Any) -> Any:
        from aiohttp import web

        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        self._ws_clients.add(ws)
        # Send an initial snapshot of live state
        try:
            from jarvis.metrics import get_system_metrics

            metrics = await get_system_metrics()
            await ws.send_str(json.dumps({"type": "status", "data": metrics, "ts": time.time()}))
        except Exception:
            pass
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    await self._ws_command(ws, msg.data)
                elif msg.type == web.WSMsgType.ERROR:
                    break
        finally:
            self._ws_clients.discard(ws)
        return ws

    async def _ws_command(self, ws: Any, raw: str) -> None:
        try:
            cmd = json.loads(raw)
        except Exception:
            return
        action = cmd.get("action")
        if action == "chat":
            text = cmd.get("text", "")
            # Run orchestrator; events stream via bus -> ws
            asyncio.create_task(self.app.process(text))
        elif action == "interrupt":
            self.app.orchestrator.voice_active = False
            ie = getattr(self.app.orchestrator, "_interrupt_event", None)
            if ie:
                ie.set()
        elif action == "suggestions_scan":
            self.app.suggestions.scan()

    async def _api_status(self, request: Any) -> Any:
        from aiohttp import web

        from jarvis.metrics import get_system_metrics

        metrics = await get_system_metrics()
        return web.json_response(metrics)

    async def _api_providers(self, request: Any) -> Any:
        from aiohttp import web

        from jarvis.api.providers import get_provider_manager

        manager = get_provider_manager()
        status = manager.get_status()
        return web.json_response(status)

    async def _api_chat(self, request: Any) -> Any:
        from aiohttp import web

        body = await request.json()
        text = body.get("text", "")
        response = await self.app.process(text)
        return web.json_response({"response": response})

    async def _api_tools(self, request: Any) -> Any:
        from aiohttp import web

        self.app.tool_library.refresh()
        query = request.query.get("q", "")
        category = request.query.get("category")
        tools = self.app.tool_library.search(query, category)
        return web.json_response({
            "tools": [t.__dict__ if hasattr(t, "__dict__") else t for t in tools],
            "categories": self.app.tool_library.categories(),
            "favorites": [t.name for t in self.app.tool_library.favorites()],
            "recent": [t.name for t in self.app.tool_library.recent()],
        })

    async def _api_tools_favorite(self, request: Any) -> Any:
        from aiohttp import web

        body = await request.json()
        name = body.get("name", "")
        fav = self.app.tool_library.toggle_favorite(name)
        return web.json_response({"name": name, "favorite": fav})

    async def _api_palette(self, request: Any) -> Any:
        from aiohttp import web

        query = request.query.get("q", "")
        items = self.app.palette.search(query)
        return web.json_response({"items": items})

    async def _api_tasks(self, request: Any) -> Any:
        from aiohttp import web

        tasks = [t.to_dict() for t in self.app.tasks.list()]
        return web.json_response({"tasks": tasks})

    async def _api_task_action(self, request: Any) -> Any:
        from aiohttp import web

        task_id = request.match_info["id"]
        action = request.match_info["action"]
        ok = False
        if action == "cancel":
            ok = await self.app.tasks.cancel(task_id)
        elif action == "pause":
            ok = await self.app.tasks.pause(task_id)
        elif action == "resume":
            ok = await self.app.tasks.resume(task_id)
        return web.json_response({"ok": ok})

    async def _api_activity(self, request: Any) -> Any:
        from aiohttp import web

        category = request.query.get("category")
        items = self.app.activity.recent(category)
        return web.json_response({"activity": items, "categories": self.app.activity.categories()})

    async def _api_suggestions(self, request: Any) -> Any:
        from aiohttp import web

        items = self.app.suggestions.scan()
        return web.json_response({"suggestions": [s.__dict__ for s in items]})


async def run_ui(app: JarvisApp, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    """Start the UI server and run until cancelled."""
    server = UIServer(app, host=host, port=port)
    await server.start()
    try:
        # Keep alive; the caller cancels.
        stop = asyncio.Event()
        await stop.wait()
    finally:
        await server.stop()
