from keywords.base_keyword import BaseKeyword
from keywords.linux.dpkg.object.dpkg_status_output import DpkgStatusOutput


class DpkgStatusKeywords(BaseKeyword):
    """
    Class for "dpkg -s" keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_dpkg_status_application(self, application_name) -> [DpkgStatusOutput]:
        """
        Gets the application information using "dpkg -s"
        Args:
            application_name: The name of the application for which we want to get the information.

        Returns: A dpkgStatusOutput object.

        """
        output = self.ssh_connection.send(f'dpkg -s {application_name}')
        self.validate_success_return_code(self.ssh_connection)
        dpkg_status_output = DpkgStatusOutput(output)

        return dpkg_status_output
