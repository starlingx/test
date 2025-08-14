class DcManagerSubcloudDeployShowObject:
    """This class represents a subcloud deploy configuration as object.

    This is typically the output of the 'dcmanager subcloud deploy show' command output table as shown below.

    +------------------+-------+
    | Field            | Value |
    +------------------+-------+
    | deploy_playbook  | None  |
    | deploy_overrides | None  |
    | deploy_chart     | None  |
    | prestage_images  | None  |
    | software_version | 25.09 |
    +------------------+-------+

    """

    def __init__(self):
        """Constructor for the DcManagerSubcloudDeployShowObject class."""
        self.deploy_playbook: str
        self.deploy_overrides: str
        self.deploy_chart: str
        self.prestage_images: str
        self.software_version: str

    def get_deploy_playbook(self) -> str:
        """Getter for the Deploy Playbook.

        Returns:
            str: The deploy playbook value.
        """
        return self.deploy_playbook

    def set_deploy_playbook(self, deploy_playbook: str):
        """Setter for the Deploy Playbook.

        Args:
            deploy_playbook (str): The deploy playbook value.
        """
        self.deploy_playbook = deploy_playbook

    def get_deploy_overrides(self) -> str:
        """Getter for the Deploy Overrides.

        Returns:
            str: The deploy overrides value.
        """
        return self.deploy_overrides

    def set_deploy_overrides(self, deploy_overrides: str):
        """Setter for the Deploy Overrides.

        Args:
            deploy_overrides (str): The deploy overrides value.
        """
        self.deploy_overrides = deploy_overrides

    def get_deploy_chart(self) -> str:
        """Getter for the Deploy Chart.

        Returns:
            str: The deploy chart value.
        """
        return self.deploy_chart

    def set_deploy_chart(self, deploy_chart: str):
        """Setter for the Deploy Chart.

        Args:
            deploy_chart (str): The deploy chart value.
        """
        self.deploy_chart = deploy_chart

    def get_prestage_images(self) -> str:
        """Getter for the Prestage Images.

        Returns:
            str: The prestage images value.
        """
        return self.prestage_images

    def set_prestage_images(self, prestage_images: str):
        """Setter for the Prestage Images.

        Args:
            prestage_images (str): The prestage images value.
        """
        self.prestage_images = prestage_images

    def get_software_version(self) -> str:
        """Getter for the Software Version.

        Returns:
            str: The software version value.
        """
        return self.software_version

    def set_software_version(self, software_version: str):
        """Setter for the Software Version.

        Args:
            software_version (str): The software version value.
        """
        self.software_version = software_version