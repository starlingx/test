class RemoteInstaller:
    """
    Class to handle remote configuration object
    """

    def __init__(self, remote_dict: []):
        self.enabled_flag = remote_dict["enabled"]
        self.file_server = remote_dict["file_server"]
        self.app_version = remote_dict["app_version"]
        self.app_build = remote_dict["app_build"]
        self.file_location = remote_dict.get("file_location", "/home/sysadmin/")
        self.tar_file_path = remote_dict.get("tar_file_path", "")
        self.download_file_name = remote_dict.get("download_file_name", "wr-openstack.tgz")

    def get_enabled_flag(self) -> str:
        """
        Getter for remote enabled flag.

        Returns: the enabled_flag

        """
        return self.enabled_flag

    def get_file_server(self) -> str:
        """
        Getter for file server.

        Returns: the file_server

        """
        return self.file_server

    def get_app_version(self):
        """
        Getter for application version.

        Returns: the app_version

        """
        return self.app_version

    def get_app_build(self) -> str:
        """
        Getter for application build.

        Returns: the app_build

        """
        return self.app_build

    def get_file_location(self) -> str:
        """
        Getter for file location.

        Returns: the file_location

        """
        return self.file_location

    def get_tar_file_path(self) -> str:
        """
        Getter for tar file path.

        Returns: the tar_file_path

        """
        return self.tar_file_path

    def get_download_file_name(self) -> str:
        """
        Getter for download file name.

        Returns: the download_file_name

        """
        return self.download_file_name

    def get_file_path(self) -> str:
        """
        This function will return a single string representation of the installer location remote object.

        Returns: str

        """
        return f"{self.file_server}/load/wrcp_rel/{self.app_version}/{self.app_build}/helm-charts/"
