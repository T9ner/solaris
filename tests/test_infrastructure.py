"""Contract tests for infrastructure drivers (Mock and Factory)."""

import asyncio
from infrastructure.mock_driver import MockBrowserDriver, MockSandboxDriver, MockDesktopDriver


def test_mock_browser_driver_navigation():
    async def run():
        browser = MockBrowserDriver()
        res = await browser.navigate_and_extract("https://example.com/pricing", recording=True)
        assert res.status_code == 200
        assert res.replay_available is True
        assert res.session_id.startswith("mock_sess_")

        replay = await browser.download_replay(res.session_id)
        assert len(replay) > 0

    asyncio.run(run())


def test_mock_sandbox_driver_lifecycle():
    async def run():
        sandbox = MockSandboxDriver()
        sbx_id = await sandbox.create_sandbox(template="base")
        assert sbx_id.startswith("sbx_sim_")

        await sandbox.write_file(sbx_id, "/tmp/test.txt", "hello solari")
        content = await sandbox.read_file(sbx_id, "/tmp/test.txt")
        assert content == "hello solari"

        cmd = await sandbox.run_command(sbx_id, "pytest", args=["-v"])
        assert cmd.exit_code == 0
        assert "PASSED" in cmd.stdout

        preview = await sandbox.get_port_preview(sbx_id, 3000)
        assert preview.port == 3000
        assert "preview.getsolari.com" in preview.url

        await sandbox.kill_sandbox(sbx_id)
        assert sandbox.sandboxes[sbx_id]["alive"] is False

    asyncio.run(run())


def test_mock_desktop_driver_lifecycle():
    async def run():
        desktop = MockDesktopDriver()
        info = await desktop.create_desktop(resolution="1280x720")
        session_id = info["session_id"]

        pid = await desktop.launch_app(session_id, "libreoffice")
        assert pid > 0

        await desktop.click(session_id, 200, 300)
        await desktop.type_text(session_id, "audit brief")

        shot = await desktop.capture_screenshot(session_id)
        assert len(shot) > 0
        assert shot.startswith(b'\x89PNG')

        await desktop.destroy_desktop(session_id)
        assert session_id not in desktop.desktops

    asyncio.run(run())
