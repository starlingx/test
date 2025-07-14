class DcManagerSubcloudDeployObject:
    """
    This class defines the object for subcloud deployment parameters.
    """

    def __init__(
        self,
        subcloud: str,
        bootstrap_address: str = None,
        bootstrap_values: str = None,
        deploy_config: str = None,
        install_values: str = None,
        bmc_password: str = None,
        group: str = None,
        release: str = None,
    ):
        """
        Constructor

        Args:
            subcloud (str): Name or ID of the subcloud
            bootstrap_address (str, optional): IP address for initial subcloud controller
            bootstrap_values (str, optional): YAML file containing subcloud configuration settings
            deploy_config (str, optional): YAML file containing subcloud variables to be passed to the deploy playbook
            install_values (str, optional): YAML file containing subcloud variables required for remote install playbook
            bmc_password (str, optional): BMC password of the subcloud to be configured
            group (str, optional): Name or id of the group the subcloud will be a part of
            release (str, optional): Software release to be installed in the subcloud
        """
        self.subcloud = subcloud
        self.bootstrap_address = bootstrap_address
        self.bootstrap_values = bootstrap_values
        self.deploy_config = deploy_config
        self.install_values = install_values
        self.bmc_password = bmc_password
        self.group = group
        self.release = release

    def get_subcloud(self) -> str:
        """Get subcloud name or ID"""
        return self.subcloud

    def get_bootstrap_address(self) -> str:
        """Get bootstrap address"""
        return self.bootstrap_address

    def get_bootstrap_values(self) -> str:
        """Get bootstrap values file path"""
        return self.bootstrap_values

    def get_deploy_config(self) -> str:
        """Get deploy config file path"""
        return self.deploy_config

    def get_install_values(self) -> str:
        """Get install values file path"""
        return self.install_values

    def get_bmc_password(self) -> str:
        """Get BMC password"""
        return self.bmc_password

    def get_group(self) -> str:
        """Get group name or ID"""
        return self.group

    def get_release(self) -> str:
        """Get release version"""
        return self.release
