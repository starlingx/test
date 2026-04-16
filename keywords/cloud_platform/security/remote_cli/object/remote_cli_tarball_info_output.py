from keywords.cloud_platform.security.remote_cli.object.remote_cli_tarball_info_object import RemoteCliTarballInfoObject


class RemoteCliTarballInfoOutput:
    """Parses build server and tarball path information from /etc/build.info.

    Populates a RemoteCliTarballInfoObject following the ACE framework output pattern.
    """

    def __init__(self, build_info: dict):
        """Constructor.

        Args:
            build_info (dict): Parsed key-value pairs from /etc/build.info.
        """
        self.remote_cli_tarball_info_object = RemoteCliTarballInfoObject()

        build_host = build_info.get("BUILD_HOST", "")
        build_by = build_info.get("BUILD_BY", "")
        job = build_info.get("JOB", "")
        build_id = build_info.get("BUILD_ID", "")
        tarball_path = f"/localdisk/loadbuild/{build_by}/{job}/{build_id}/export/windshare/wrs-remote-clients-*.tgz"

        self.remote_cli_tarball_info_object.set_build_host(build_host)
        self.remote_cli_tarball_info_object.set_tarball_path(tarball_path)

    def get_remote_cli_tarball_info_object(self) -> RemoteCliTarballInfoObject:
        """Get the parsed tarball info object.

        Returns:
            RemoteCliTarballInfoObject: Object containing build host and tarball path.
        """
        return self.remote_cli_tarball_info_object
