from keywords.base_keyword import BaseKeyword


class SystemCTLIsActiveKeywords(BaseKeyword):
    """
    Class for "systemctl is-active" keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def is_active(self, service_name) -> str:
        """
        Checks if the service is active using  "systemctl is-active <service_name>"
        Args:
            service_name: The name of the service

        Returns: 'active' or 'inactive'

        """
        output = self.ssh_connection.send(f'systemctl is-active {service_name}')
        self.validate_success_return_code(self.ssh_connection)

        # output is a List of 1 string. "active/n"
        output_string = ""
        if output and len(output) > 0:
            output_string = output[0].strip()
        else:
            raise "Output is expected to be a List with one element."

        return output_string
