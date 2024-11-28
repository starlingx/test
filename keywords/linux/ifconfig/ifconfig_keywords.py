from keywords.base_keyword import BaseKeyword
from keywords.linux.ifconfig.object.ifconfig_output import IfConfigOutput


class IfConfigKeywords(BaseKeyword):
    """
    Class for "ifconfig" command keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_ifconfig(self, application_name) -> [IfConfigOutput]:
        """
        Gets the output of 'ifconfig' command as a IfConfigOutput object.
        Args: None.

        Returns: IfConfigOutput

        """
        output = self.ssh_connection.send('ifconfig -a')
        self.validate_success_return_code(self.ssh_connection)
        ifconfig_output = IfConfigOutput(output)

        return ifconfig_output
