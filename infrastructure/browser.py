"""Solari Cloud Browser Driver.

Provides live browser automation, stealth scraping, proxy routing,
and rrweb session recording.
"""

import asyncio
import os
from typing import List, Optional
from infrastructure.base import BaseBrowserDriver, BrowserSessionResult


class SolariBrowserDriver(BaseBrowserDriver):
    """Production driver connecting to the Solari Cloud Browser service."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SOLARI_API_KEY", "")
        if not self.api_key:
            raise ValueError("SOLARI_API_KEY is required for live SolariBrowserDriver.")

    async def navigate_and_extract(
        self,
        url: str,
        stealth: bool = True,
        proxy: Optional[str] = None,
        recording: bool = True,
        wait_selector: Optional[str] = None,
    ) -> BrowserSessionResult:
        from solari_browser import Solari

        solari = Solari(api_key=self.api_key)
        launch_kwargs = {"recording": recording}
        if stealth:
            launch_kwargs["stealth"] = True
        if proxy:
            launch_kwargs["proxy"] = proxy

        browser = await solari.launch(**launch_kwargs)
        session_id = getattr(browser, "id", "live_session")
        try:
            page = await browser.new_page()
            response = await page.goto(url)
            status_code = response.status if response else 200

            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=10_000)

            # Allow rrweb recording buffer to flush
            if recording:
                await asyncio.sleep(1.5)

            title = await page.title()
            dom_text = await page.content()
            content_snippet = (await page.inner_text("body"))[:500] if await page.query_selector("body") else dom_text[:500]

            return BrowserSessionResult(
                session_id=session_id,
                url=url,
                title=title,
                content_snippet=content_snippet,
                dom_text=dom_text,
                status_code=status_code,
                replay_available=recording,
                replay_events_count=0,
                proxy_used=proxy or "datacenter",
            )
        finally:
            await browser.close()
            # Clean up the loopback proxy handle to allow clean process exit
            await solari.close()

    async def download_replay(self, session_id: str) -> List[str]:
        from solari_browser import Solari
        from solari_browser.errors import SolariError

        solari = Solari(api_key=self.api_key)
        try:
            # Poll for async upload completion after session release
            for attempt in range(1, 10):
                await asyncio.sleep(2.0)
                try:
                    blob = await solari.sessions.download_replay(session_id)
                    events = blob.decode("utf-8").splitlines()
                    return events
                except SolariError as err:
                    if getattr(err, "status", None) == 404:
                        continue
                    raise
            return []
        finally:
            await solari.close()
