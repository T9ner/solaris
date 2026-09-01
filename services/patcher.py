"""Domain service for sandbox code reproduction, auto-patching, and test execution."""

from typing import Dict, Optional, Tuple
from infrastructure.base import BaseSandboxDriver, CommandRunResult, PortPreviewResult


class SandboxPatcherService:
    """Automates code reproduction and patch verification inside Solari MicroVM Sandboxes."""

    def __init__(self, sandbox_driver: BaseSandboxDriver):
        self.sandbox_driver = sandbox_driver

    async def setup_workspace(
        self,
        sandbox_id: str,
        repo_files: Dict[str, str],
    ) -> None:
        """Write repository files into sandbox microVM filesystem."""
        for path, content in repo_files.items():
            await self.sandbox_driver.write_file(sandbox_id, path, content)

    async def apply_patch(
        self,
        sandbox_id: str,
        file_path: str,
        patch_content: str,
    ) -> None:
        """Apply a code patch to a specific file inside the sandbox."""
        await self.sandbox_driver.write_file(sandbox_id, file_path, patch_content)

    async def run_test_suite(
        self,
        sandbox_id: str,
        test_command: str = "pytest",
        args: Optional[list] = None,
    ) -> CommandRunResult:
        """Execute automated tests inside the microVM sandbox."""
        args = args or ["-v"]
        return await self.sandbox_driver.run_command(sandbox_id, test_command, args=args)

    async def launch_preview_server(
        self,
        sandbox_id: str,
        port: int = 3000,
        start_command: str = "python3 -m http.server 3000",
    ) -> PortPreviewResult:
        """Start a web server inside the VM and expose its public preview URL."""
        # Run server in background via shell
        await self.sandbox_driver.run_command(
            sandbox_id,
            "sh",
            args=["-c", f"nohup {start_command} >/dev/null 2>&1 &"],
        )
        return await self.sandbox_driver.get_port_preview(sandbox_id, port)
