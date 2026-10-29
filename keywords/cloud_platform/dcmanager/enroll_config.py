"""Holder for the resolved enroll config file paths of one subcloud enrollment."""


class EnrollConfig:
    """The resolved enroll config file paths for one enrollment."""

    def __init__(self, bootstrap_values: str, install_values: str, deploy_config_file: str):
        """Constructor.

        Args:
            bootstrap_values (str): Path to the bootstrap-values file.
            install_values (str): Path to the install-values file.
            deploy_config_file (str): Path to the deploy-config file.
        """
        self.bootstrap_values = bootstrap_values
        self.install_values = install_values
        self.deploy_config_file = deploy_config_file
