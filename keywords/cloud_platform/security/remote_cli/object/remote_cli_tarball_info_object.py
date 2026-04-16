class RemoteCliTarballInfoObject:
    """Represents the resolved build server and tarball path information.

    Follows the ACE framework object pattern.
    """

    def __init__(self):
        """Constructor."""
        self.build_host = None
        self.tarball_path = None

    def set_build_host(self, build_host: str):
        """
        Setter for the build_host.
        """
        self.build_host = build_host

    def get_build_host(self) -> str:
        """
        Getter for the build_host.
        """
        return self.build_host

    def set_tarball_path(self, tarball_path: str):
        """
        Setter for the tarball_path.
        """
        self.tarball_path = tarball_path

    def get_tarball_path(self) -> str:
        """
        Getter for the tarball_path.
        """
        return self.tarball_path
