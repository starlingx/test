"""WRA Server Configuration Object."""

import json5


class WraServerConfig:
    """Configuration for the WRA (Wind River Analytics) tarball server.

    Args:
        config: Path to the WRA server configuration JSON5 file.
    """

    def __init__(self, config: str):
        """Initialize WRA server configuration.

        Args:
            config (str): Path to configuration file.
        """
        with open(config, "r") as json_data:
            wra_dict = json5.load(json_data)

        self.server = wra_dict.get("server", "")
        self.user = wra_dict.get("user", "")
        self.password = wra_dict.get("password", "")
        self.base_path = wra_dict.get("base_path", "")
        self.tarball_pattern = wra_dict.get("tarball_pattern", "")
        self.destination_path = wra_dict.get("destination_path", "/home/sysadmin")
        self.connection_timeout = wra_dict.get("connection_timeout", 30)
        self.download_timeout = wra_dict.get("download_timeout", 600)

    def __str__(self) -> str:
        """Return string representation of the WRA server config.

        Returns:
            str: Human-readable representation.
        """
        return (
            f"WraServerConfig(server={self.server}, "
            f"base_path={self.base_path}, "
            f"tarball_pattern={self.tarball_pattern})"
        )

    def get_server(self) -> str:
        """Get the WRA build server hostname.

        Returns:
            str: Server hostname.
        """
        return self.server

    def get_user(self) -> str:
        """Get the SSH username for the build server.

        Returns:
            str: Username.
        """
        return self.user

    def get_password(self) -> str:
        """Get the SSH password for the build server.

        Returns:
            str: Password.
        """
        return self.password

    def get_base_path(self) -> str:
        """Get the base path on the build server where WRA tarballs are stored.

        Returns:
            str: Base path.
        """
        return self.base_path

    def get_tarball_pattern(self) -> str:
        """Get the glob pattern for matching WRA tarball files.

        Returns:
            str: Tarball filename pattern.
        """
        return self.tarball_pattern

    def get_destination_path(self) -> str:
        """Get the local destination path for downloaded tarballs.

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
