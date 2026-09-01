"""Infrastructure package initialization and factory function."""

from typing import Tuple, Optional
from infrastructure.base import BaseBrowserDriver, BaseSandboxDriver, BaseDesktopDriver
from infrastructure.mock_driver import MockBrowserDriver, MockSandboxDriver, MockDesktopDriver
from infrastructure.browser import SolariBrowserDriver
from infrastructure.sandbox import SolariSandboxDriver
from infrastructure.desktop import SolariDesktopDriver


def create_infrastructure_drivers(
    use_mock: bool = True,
    api_key: Optional[str] = None,
) -> Tuple[BaseBrowserDriver, BaseSandboxDriver, BaseDesktopDriver]:
    """Factory creating appropriate infrastructure drivers based on execution mode."""
    if use_mock:
        return MockBrowserDriver(), MockSandboxDriver(), MockDesktopDriver()
    return (
        SolariBrowserDriver(api_key=api_key),
        SolariSandboxDriver(api_key=api_key),
        SolariDesktopDriver(api_key=api_key),
    )
