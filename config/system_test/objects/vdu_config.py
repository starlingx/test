"""VDU Server Configuration Object."""

import json5


class VduConfig:
    """Configuration for the VDU (Virtual Deployment Unit) test data server.

    Args:
        config: Path to the VDU configuration JSON5 file.
    """

    def __init__(self, config: str):
        """Initialize VDU configuration.

        Args:
            config (str): Path to configuration file.
        """
        with open(config, "r") as json_data:
            vdu_dict = json5.load(json_data)

        self.server = vdu_dict.get("server", "")
        self.user = vdu_dict.get("user", "")
        self.password = vdu_dict.get("password", "")
        self.base_path = vdu_dict.get("base_path", "")
        self.destination_path = vdu_dict.get("destination_path", "/home/sysadmin")
        self.connection_timeout = vdu_dict.get("connection_timeout", 30)
        self.download_timeout = vdu_dict.get("download_timeout", 600)
        self.fail_ok = vdu_dict.get("fail_ok", True)

    def __str__(self) -> str:
        """Return string representation of the VDU config.

        Returns:
            str: Human-readable representation.
        """
        return (
            f"VduConfig(server={self.server}, "
            f"base_path={self.base_path}, "
            f"fail_ok={self.fail_ok})"
        )

    def get_server(self) -> str:
        """Get the VDU data server hostname.

        Returns:
            str: Server hostname.
        """
        return self.server

    def get_user(self) -> str:
        """Get the SSH username for the server.

        Returns:
            str: Username.
        """
        return self.user

    def get_password(self) -> str:
        """Get the SSH password for the server.

        Returns:
            str: Password.
        """
        return self.password

    def get_base_path(self) -> str:
        """Get the base path on the server where VDU files are stored.

        Returns:
            str: Base path.
        """
        return self.base_path

    def get_destination_path(self) -> str:
        """Get the local destination path for downloaded files.

        Returns:
            str: Destination path on the lab.
        """
        return self.destination_path

    def get_connection_timeout(self) -> int:
        """Get the connection timeout in seconds.

        Returns:
            int: Connection timeout.
        """
        return self.connection_timeout

    def get_download_timeout(self) -> int:
        """Get the download timeout in seconds.

        Returns:
            int: Download timeout.
        """
        return self.download_timeout

    def get_fail_ok(self) -> bool:
        """Get whether it's acceptable for the install script to fail.

        Returns:
            bool: True if partial failures are acceptable.
        """
        return self.fail_ok
