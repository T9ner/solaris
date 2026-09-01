"""Solari Sandbox Driver.

Provides microVM lifecycle management, isolated command execution,
stateful Python kernels, file system access, and public port previews.
"""

import os
from typing import Any, Dict, List, Optional
from infrastructure.base import (
    BaseSandboxDriver,
    CommandRunResult,
    CodeExecutionResult,
    PortPreviewResult,
)


class SolariSandboxDriver(BaseSandboxDriver):
    """Production driver connecting to Solari MicroVM Sandboxes."""

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.getsolari.com"):
        self.api_key = api_key or os.environ.get("SOLARI_API_KEY", "")
        self.base_url = base_url
        if not self.api_key:
            raise ValueError("SOLARI_API_KEY is required for live SolariSandboxDriver.")
        self._active_sandboxes: Dict[str, Any] = {}

    async def _get_connected_sandbox(self, sandbox_id: str):
        if sandbox_id in self._active_sandboxes:
            return self._active_sandboxes[sandbox_id]
        raise RuntimeError(f"Sandbox {sandbox_id} is not connected or active.")

    async def create_sandbox(
        self,
        template: str = "base",
        timeout_ms: int = 300_000,
    ) -> str:
        from solari_sandbox import SandboxClient

        client = SandboxClient(api_key=self.api_key, base_url=self.base_url)
        sandbox = await client.create(template=template, timeout_ms=timeout_ms)
        await sandbox.connect()
        sandbox_id = getattr(sandbox, "sandboxId", getattr(sandbox, "id", "sbx_live"))
        self._active_sandboxes[sandbox_id] = sandbox
        return sandbox_id

    async def run_command(
        self,
        sandbox_id: str,
        command: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> CommandRunResult:
        sandbox = await self._get_connected_sandbox(sandbox_id)
        args = args or []
        run_kwargs: Dict[str, Any] = {"args": args}
        if cwd:
            run_kwargs["cwd"] = cwd

        out = await sandbox.commands.run(command, **run_kwargs)
        exit_code = getattr(out, "exitCode", getattr(out, "exit_code", 0))
        stdout = getattr(out, "stdout", "")
        stderr = getattr(out, "stderr", "")

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
        sandbox = await self._get_connected_sandbox(sandbox_id)
        await sandbox.files.write(path, content)

    async def read_file(
        self,
        sandbox_id: str,
        path: str,
    ) -> str:
        sandbox = await self._get_connected_sandbox(sandbox_id)
        return await sandbox.files.read_text(path)

    async def execute_code_kernel(
        self,
        sandbox_id: str,
        code: str,
        language: str = "python",
        context_id: Optional[str] = None,
    ) -> CodeExecutionResult:
        sandbox = await self._get_connected_sandbox(sandbox_id)
        ctx = context_id
        if not ctx:
            ctx = await sandbox.create_code_context(language)

        result = await sandbox.run_code(code, context_id=ctx)
        error = getattr(result, "error", None)

        output_items = []
        raw_results = getattr(result, "results", [])
        for item in raw_results:
            output_items.append({
                "type": getattr(item, "type", "result"),
                "text": getattr(item, "text", str(item)),
            })

        return CodeExecutionResult(
            context_id=ctx,
            output_items=output_items,
            final_result=output_items[-1]["text"] if output_items else None,
            error=str(error) if error else None,
        )

    async def get_port_preview(
        self,
        sandbox_id: str,
        port: int,
    ) -> PortPreviewResult:
        sandbox = await self._get_connected_sandbox(sandbox_id)
        res = await sandbox.preview_url(port)
        url = getattr(res, "url", str(res))
        return PortPreviewResult(port=port, url=url, status="active")

    async def kill_sandbox(self, sandbox_id: str) -> None:
        if sandbox_id in self._active_sandboxes:
            sandbox = self._active_sandboxes.pop(sandbox_id)
            await sandbox.kill()
