class PlatformConfOutput:
    """Parses the output of 'cat /etc/platform/platform.conf' into key-value pairs."""

    def __init__(self, raw_output: str) -> None:
        """Constructor.

        Args:
            raw_output (str): Raw string from 'cat /etc/platform/platform.conf'.
                Lines are key=value pairs; comment lines starting with '#' are ignored.
        """
        self._values: dict = {}
        for line in raw_output.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key, _, value = stripped.partition("=")
                self._values[key.strip()] = value.strip()

    def get_subfunction(self) -> str:
        """Return the subfunction value from platform.conf.

        The subfunction describes the roles assigned to the host, e.g.
        'controller,worker,lowlatency'.

        Returns:
            str: Subfunction string, or empty string if the key is not present.
        """
        return self._values.get("subfunction", "")

    def get_value(self, key: str) -> str:
        """Return an arbitrary key from platform.conf.

        Args:
            key (str): The configuration key to retrieve.

        Returns:
            str: The value associated with the key, or empty string if not present.
        """
        return self._values.get(key, "")
