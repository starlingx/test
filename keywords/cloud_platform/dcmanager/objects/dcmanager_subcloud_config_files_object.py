class DcManagerSubcloudConfigFilesObject:
    """
    This class defines the object for subcloud configuration files information.
    """

    def __init__(
        self,
        install_file: str = None,
        bootstrap_file: str = None,
        deploy_file: str = None,
    ):
        """
        Constructor

        Args:
            install_file (str, optional): Path to the install configuration file
            bootstrap_file (str, optional): Path to the bootstrap configuration file
            deploy_file (str, optional): Path to the deploy configuration file
        """
        self.install_file = install_file
        self.bootstrap_file = bootstrap_file
        self.deploy_file = deploy_file

    def get_install_file(self) -> str:
        """Get install configuration file path"""
        return self.install_file

    def get_bootstrap_file(self) -> str:
        """Get bootstrap configuration file path"""
        return self.bootstrap_file

    def get_deploy_file(self) -> str:
        """Get deploy configuration file path"""
        return self.deploy_file
