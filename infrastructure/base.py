"""Base interfaces for Solari infrastructure drivers.

Implements the Strategy pattern to decouple agent logic from concrete
SDK implementations or offline mock simulators.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BrowserSessionResult(BaseModel):
    """Result of a browser navigation and extraction session."""
    session_id: str
    url: str
    title: str
    content_snippet: str
    dom_text: str
    status_code: int = 200
    replay_available: bool = False
    replay_events_count: int = 0
    proxy_used: Optional[str] = None


class CommandRunResult(BaseModel):
    """Result of running a command inside a sandbox."""
    exit_code: int
    stdout: str
    stderr: str
    command: str
    args: List[str] = Field(default_factory=list)


class CodeExecutionResult(BaseModel):
    """Result of executing code in a stateful kernel context."""
    context_id: str
    output_items: List[Dict[str, Any]] = Field(default_factory=list)
    final_result: Optional[str] = None
    error: Optional[str] = None


class PortPreviewResult(BaseModel):
    """Public URL preview for a server running inside a sandbox."""
    port: int
    url: str
    status: str = "active"


class DesktopActionResult(BaseModel):
    """Result of an action performed on a managed desktop."""
    session_id: str
    stream_url: str
    action_type: str
    screenshot_bytes: Optional[bytes] = None
    screenshot_path: Optional[str] = None
    success: bool = True
    details: Dict[str, Any] = Field(default_factory=dict)


class BaseBrowserDriver(ABC):
    """Interface for browser automation and stealth scraping."""

    @abstractmethod
    async def navigate_and_extract(
        self,
        url: str,
        stealth: bool = True,
        proxy: Optional[str] = None,
        recording: bool = True,
        wait_selector: Optional[str] = None,
    ) -> BrowserSessionResult:
        """Launch browser session, navigate to url, extract content and recording."""
        pass

    @abstractmethod
    async def download_replay(self, session_id: str) -> List[str]:
        """Download raw rrweb NDJSON events for a recorded session."""
        pass


class BaseSandboxDriver(ABC):
    """Interface for microVM sandboxes and stateful execution."""

    @abstractmethod
    async def create_sandbox(
        self,
        template: str = "base",
        timeout_ms: int = 300_000,
    ) -> str:
        """Create a new microVM sandbox and return its sandbox ID."""
        pass

    @abstractmethod
    async def run_command(
        self,
        sandbox_id: str,
        command: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> CommandRunResult:
        """Run an arbitrary command inside the sandbox."""
        pass

    @abstractmethod
    async def write_file(
        self,
        sandbox_id: str,
        path: str,
        content: str,
    ) -> None:
        """Write a text file inside the sandbox filesystem."""
        pass

    @abstractmethod
    async def read_file(
        self,
        sandbox_id: str,
        path: str,
    ) -> str:
        """Read a text file from the sandbox filesystem."""
        pass

    @abstractmethod
    async def execute_code_kernel(
        self,
        sandbox_id: str,
        code: str,
        language: str = "python",
        context_id: Optional[str] = None,
    ) -> CodeExecutionResult:
        """Run code inside a stateful kernel context."""
        pass

    @abstractmethod
    async def get_port_preview(
        self,
        sandbox_id: str,
        port: int,
    ) -> PortPreviewResult:
        """Expose an internal port on a public URL."""
        pass

    @abstractmethod
    async def kill_sandbox(self, sandbox_id: str) -> None:
        """Destroy the sandbox microVM."""
        pass


class BaseDesktopDriver(ABC):
    """Interface for managed desktop GUI automation and screenshots."""

    @abstractmethod
    async def create_desktop(
        self,
        resolution: str = "1280x720",
        timeout_ms: int = 600_000,
    ) -> Dict[str, str]:
        """Create a desktop session and return session_id and stream_url."""
        pass

    @abstractmethod
    async def launch_app(
        self,
        session_id: str,
        app_name: str,
    ) -> int:
        """Launch an X11 application by name."""
        pass

    @abstractmethod
    async def click(
        self,
        session_id: str,
        x: int,
        y: int,
        humanize: bool = True,
    ) -> None:
        """Click at coordinate on screen with humanized mouse trajectory."""
        pass

    @abstractmethod
    async def type_text(
        self,
        session_id: str,
        text: str,
    ) -> None:
        """Type text into focused window."""
        pass

    @abstractmethod
    async def capture_screenshot(
        self,
        session_id: str,
        output_path: Optional[str] = None,
    ) -> bytes:
        """Capture screenshot of the desktop."""
        pass

    @abstractmethod
    async def destroy_desktop(self, session_id: str) -> None:
        """Destroy the desktop session."""
        pass
