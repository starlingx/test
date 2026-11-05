from unittest.mock import MagicMock, patch

from keywords.bmc.ipmitool.is_ipmitool_keywords import IsIPMIToolKeywords


class FakeSshConnection:
    """SSH double; a plain class because BaseKeyword wraps callable attributes such as MagicMock."""

    def __init__(self, output: list[str]):
        """Constructor.

        Args:
            output (list[str]): Lines returned by the sudo command.
        """
        self.output = output

    def send_as_sudo(self, command: str) -> list[str]:
        """Return the canned output.

        Args:
            command (str): Command sent.

        Returns:
            list[str]: Canned output lines.
        """
        return self.output


@patch("keywords.base_keyword.get_logger", MagicMock())
def test_available_when_usage_banner_follows_warnings():
    """Detect ipmitool when it prints warnings before the usage banner."""
    output = ["Get Device ID command failed: 0xd5 Command not supported in present state\n", "Received a response with unexpected ID 0 vs. 1\n", "No command provided!\n", "Commands:\n"]
    assert IsIPMIToolKeywords(FakeSshConnection(output)).is_ipmi_tool_available() is True


@patch("keywords.base_keyword.get_logger", MagicMock())
def test_available_when_usage_banner_is_first():
    """Detect ipmitool when the usage banner is the first line."""
    assert IsIPMIToolKeywords(FakeSshConnection(["No command provided!\n", "Commands:\n"])).is_ipmi_tool_available() is True


@patch("keywords.base_keyword.get_logger", MagicMock())
def test_unavailable_without_local_ipmi_device():
    """Report ipmitool as unavailable when the IPMI device cannot be opened."""
    output = ["Could not open device at /dev/ipmi0 or /dev/ipmi/0 or /dev/ipmidev/0: No such file or directory\n"]
    assert IsIPMIToolKeywords(FakeSshConnection(output)).is_ipmi_tool_available() is False
