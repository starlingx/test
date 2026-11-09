"""Baseline application archive identity."""


class BaselineApplicationPackage:
    """Keep an archive path and its exact application version together."""

    def __init__(self, artifact: str, version: str):
        """Capture the baseline package.

        Args:
            artifact (str): Absolute archive path.
            version (str): Exact application version.
        """
        self.artifact = artifact
        self.version = version

    def get_artifact(self) -> str:
        """Return the archive path.

        Returns:
            str: Absolute archive path.
        """
        return self.artifact

    def get_version(self) -> str:
        """Return the application version.

        Returns:
            str: Exact application version.
        """
        return self.version
