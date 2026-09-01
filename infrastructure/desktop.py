"""Solari Managed Desktop Driver.

Provides X11 Linux GUI session management, application launching,
humanized mouse movements, keyboard input, and screenshot streaming.
"""

import asyncio
import os
import pathlib
from typing import Any, Dict, Optional
from infrastructure.base import BaseDesktopDriver


class SolariDesktopDriver(BaseDesktopDriver):
    """Production driver connecting to Solari Managed Desktops."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.getsolari.com"):
        self.api_key = api_key or os.environ.get("SOLARI_API_KEY", "")
        self.base_url = base_url
        if not self.api_key:
            raise ValueError("SOLARI_API_KEY is required for live SolariDesktopDriver.")
        self._active_clients: Dict[str, Any] = {}
        self._active_desktops: Dict[str, Any] = {}

    async def create_desktop(
        self,
        resolution: str = "1280x720",
        timeout_ms: int = 600_000,
    ) -> Dict[str, str]:
        from solari_desktop import DesktopClient

        client = DesktopClient(api_key=self.api_key, base_url=self.base_url)
        desktop = await client.create(template="default", resolution=resolution, timeout_ms=timeout_ms)
        await desktop.connect()

        # Wait for X11 server to initialize
        for _ in range(30):
            health = await desktop.health()
            if getattr(health, "ready", False):
                break
            await asyncio.sleep(1)

        session_id = getattr(desktop, "sessionId", getattr(desktop, "id", "dsk_live"))
        stream_url = getattr(desktop, "streamUrl", getattr(desktop, "stream_url", ""))

        self._active_clients[session_id] = client
        self._active_desktops[session_id] = desktop

        return {"session_id": session_id, "stream_url": stream_url}

    async def _get_desktop(self, session_id: str):
        if session_id in self._active_desktops:
            return self._active_desktops[session_id]
        raise RuntimeError(f"Desktop session {session_id} not found.")

    async def launch_app(
        self,
        session_id: str,
        app_name: str,
    ) -> int:
        desktop = await self._get_desktop(session_id)
        pid = await desktop.open(app_name)
        await asyncio.sleep(3)  # Allow window to map
        return pid

    async def click(
        self,
        session_id: str,
        x: int,
        y: int,
        humanize: bool = True,
    ) -> None:
        desktop = await self._get_desktop(session_id)
        await desktop.mouse.click(x, y, humanize=humanize)
        await asyncio.sleep(0.5)

    async def type_text(
        self,
        session_id: str,
        text: str,
    ) -> None:
        desktop = await self._get_desktop(session_id)
        await desktop.keyboard.type(text)
        await asyncio.sleep(0.5)

    async def capture_screenshot(
        self,
        session_id: str,
        output_path: Optional[str] = None,
    ) -> bytes:
        desktop = await self._get_desktop(session_id)
        shot_bytes = await desktop.screenshot(format="png")
        if output_path:
            path = pathlib.Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(shot_bytes)
        return shot_bytes

    async def destroy_desktop(self, session_id: str) -> None:
        desktop = self._active_desktops.pop(session_id, None)
        client = self._active_clients.pop(session_id, None)
        if desktop:
            await desktop.close()
        if client:
            await client.destroy(session_id)
