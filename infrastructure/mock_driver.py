"""Mock simulation drivers for Solari infrastructure.

Provides deterministic, offline execution for unit tests and benchmark evaluations
without requiring active API credits or live network connectivity.
"""

import asyncio
import hashlib
from typing import Any, Dict, List, Optional
from infrastructure.base import (
    BaseBrowserDriver,
    BaseSandboxDriver,
    BaseDesktopDriver,
    BrowserSessionResult,
    CommandRunResult,
    CodeExecutionResult,
    PortPreviewResult,
    DesktopActionResult,
)


class MockBrowserDriver(BaseBrowserDriver):
    """Deterministic in-memory browser simulation."""

    def __init__(self, synthetic_responses: Optional[Dict[str, Dict[str, Any]]] = None):
        self.synthetic_responses = synthetic_responses or {}
        self.recorded_sessions: Dict[str, List[str]] = {}

    def set_page_mock(self, url_substring: str, title: str, dom_text: str):
        """Register a mock page response for a URL pattern."""
        self.synthetic_responses[url_substring] = {
            "title": title,
            "dom_text": dom_text,
            "status_code": 200,
        }

    async def navigate_and_extract(
        self,
        url: str,
        stealth: bool = True,
        proxy: Optional[str] = None,
        recording: bool = True,
        wait_selector: Optional[str] = None,
    ) -> BrowserSessionResult:
        await asyncio.sleep(0.05)  # Simulate network latency
        session_id = f"mock_sess_{hashlib.md5(url.encode()).hexdigest()[:8]}"

        # Look up synthetic content or generate realistic fallback
        matched_data = None
        for pattern, data in self.synthetic_responses.items():
            if pattern in url:
                matched_data = data
                break

        if matched_data:
            title = matched_data["title"]
            dom_text = matched_data["dom_text"]
            status_code = matched_data.get("status_code", 200)
        else:
            title = f"Page at {url}"
            dom_text = f"<html><body><h1>{title}</h1><p>Simulated live extraction for {url}</p></body></html>"
            status_code = 200

        # Generate synthetic rrweb NDJSON events
        if recording:
            events = [
                '{"type":4,"data":{"href":"' + url + '","width":1280,"height":720},"timestamp":1000}',
                '{"type":2,"data":{"node":{"type":1,"name":"html","children":[]}},"timestamp":1050}',
                '{"type":3,"data":{"source":1,"texts":[{"id":1,"value":"' + title + '"}]},"timestamp":1100}',
            ]
            self.recorded_sessions[session_id] = events

        return BrowserSessionResult(
            session_id=session_id,
            url=url,
            title=title,
            content_snippet=dom_text[:300],
            dom_text=dom_text,
            status_code=status_code,
            replay_available=recording,
            replay_events_count=len(self.recorded_sessions.get(session_id, [])),
            proxy_used=proxy or "us-residential",
        )

    async def download_replay(self, session_id: str) -> List[str]:
        await asyncio.sleep(0.02)
        return self.recorded_sessions.get(session_id, [
            '{"type":4,"data":{"href":"https://mock.session","width":1280,"height":720},"timestamp":1000}',
            '{"type":2,"data":{"node":{"type":1,"name":"html"}},"timestamp":1050}'
        ])


class MockSandboxDriver(BaseSandboxDriver):
    """Deterministic in-memory microVM sandbox simulation."""

    def __init__(self):
        self.sandboxes: Dict[str, Dict[str, Any]] = {}

    async def create_sandbox(
        self,
        template: str = "base",
        timeout_ms: int = 300_000,
    ) -> str:
        await asyncio.sleep(0.05)
        sandbox_id = f"sbx_sim_{len(self.sandboxes) + 1}_{template}"
        self.sandboxes[sandbox_id] = {
            "template": template,
            "timeout_ms": timeout_ms,
            "files": {},
            "code_contexts": {},
            "alive": True,
        }
        return sandbox_id

    async def run_command(
        self,
        sandbox_id: str,
        command: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> CommandRunResult:
        await asyncio.sleep(0.05)
        args = args or []
        full_cmd = f"{command} {' '.join(args)}".strip()

        # Simulated shell/python behaviors
        if "pytest" in full_cmd or "test" in full_cmd:
            stdout = "================ 4 passed in 0.42s ================\nPASSED"
            exit_code = 0
            stderr = ""
        elif "git status" in full_cmd:
            stdout = "On branch main\nChanges not staged for commit:\n  modified: app/main.py\n"
            exit_code = 0
            stderr = ""
        elif "git diff" in full_cmd:
            stdout = "diff --git a/app/main.py b/app/main.py\n--- a/app/main.py\n+++ b/app/main.py\n@@ -10,3 +10,4 @@\n+    return {'status': 'healthy', 'version': '2.4.1'}\n"
            exit_code = 0
            stderr = ""
        else:
            stdout = f"Command '{full_cmd}' executed successfully in {sandbox_id}"
            exit_code = 0
            stderr = ""

        return CommandRunResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            command=command,
            args=args,
        )

    async def write_file(
        self,
        sandbox_id: str,
        path: str,
        content: str,
    ) -> None:
        if sandbox_id not in self.sandboxes:
            raise RuntimeError(f"Sandbox {sandbox_id} does not exist.")
        self.sandboxes[sandbox_id]["files"][path] = content

    async def read_file(
        self,
        sandbox_id: str,
        path: str,
    ) -> str:
        if sandbox_id not in self.sandboxes:
            raise RuntimeError(f"Sandbox {sandbox_id} does not exist.")
        files = self.sandboxes[sandbox_id]["files"]
        if path not in files:
            # Fallback default file contents for testing
            return f"# Simulated file content for {path}\nSTATUS = 'OK'\n"
        return files[path]

    async def execute_code_kernel(
        self,
        sandbox_id: str,
        code: str,
        language: str = "python",
        context_id: Optional[str] = None,
    ) -> CodeExecutionResult:
        await asyncio.sleep(0.05)
        if sandbox_id not in self.sandboxes:
            raise RuntimeError(f"Sandbox {sandbox_id} does not exist.")

        ctx_id = context_id or f"ctx_{len(self.sandboxes[sandbox_id]['code_contexts']) + 1}"
        if ctx_id not in self.sandboxes[sandbox_id]["code_contexts"]:
            self.sandboxes[sandbox_id]["code_contexts"][ctx_id] = {}

        # Simulated kernel execution
        outputs = []
        if "print(" in code:
            printed = code.split("print(")[1].split(")")[0].replace("'", "").replace('"', '')
            outputs.append({"type": "stdout", "text": printed})
        else:
            outputs.append({"type": "result", "text": "Kernel execution evaluated successfully."})

        return CodeExecutionResult(
            context_id=ctx_id,
            output_items=outputs,
            final_result="Success",
            error=None,
        )

    async def get_port_preview(
        self,
        sandbox_id: str,
        port: int,
    ) -> PortPreviewResult:
        await asyncio.sleep(0.02)
        url = f"https://{sandbox_id}-{port}.preview.getsolari.com"
        return PortPreviewResult(port=port, url=url, status="active")

    async def kill_sandbox(self, sandbox_id: str) -> None:
        if sandbox_id in self.sandboxes:
            self.sandboxes[sandbox_id]["alive"] = False


class MockDesktopDriver(BaseDesktopDriver):
    """Deterministic in-memory desktop simulation."""

    def __init__(self):
        self.desktops: Dict[str, Dict[str, Any]] = {}

    async def create_desktop(
        self,
        resolution: str = "1280x720",
        timeout_ms: int = 600_000,
    ) -> Dict[str, str]:
        await asyncio.sleep(0.05)
        session_id = f"dsk_sim_{len(self.desktops) + 1}"
        stream_url = f"wss://stream.getsolari.com/vnc/{session_id}"
        self.desktops[session_id] = {
            "resolution": resolution,
            "timeout_ms": timeout_ms,
            "running_apps": [],
            "actions": [],
        }
        return {"session_id": session_id, "stream_url": stream_url}

    async def launch_app(
        self,
        session_id: str,
        app_name: str,
    ) -> int:
        await asyncio.sleep(0.05)
        pid = 1000 + len(self.desktops.get(session_id, {}).get("running_apps", []))
        if session_id in self.desktops:
            self.desktops[session_id]["running_apps"].append({"name": app_name, "pid": pid})
        return pid

    async def click(
        self,
        session_id: str,
        x: int,
        y: int,
        humanize: bool = True,
    ) -> None:
        await asyncio.sleep(0.02)
        if session_id in self.desktops:
            self.desktops[session_id]["actions"].append({"type": "click", "x": x, "y": y})

    async def type_text(
        self,
        session_id: str,
        text: str,
    ) -> None:
        await asyncio.sleep(0.02)
        if session_id in self.desktops:
            self.desktops[session_id]["actions"].append({"type": "type", "text": text})

    async def capture_screenshot(
        self,
        session_id: str,
        output_path: Optional[str] = None,
    ) -> bytes:
        await asyncio.sleep(0.05)
        # Minimal 1x1 valid PNG byte sequence
        png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\r\xefe\r\x00\x00\x00\x00IEND\xaeB`\x82'
        if output_path:
            with open(output_path, "wb") as f:
                f.write(png_bytes)
        return png_bytes

    async def destroy_desktop(self, session_id: str) -> None:
        if session_id in self.desktops:
            del self.desktops[session_id]
