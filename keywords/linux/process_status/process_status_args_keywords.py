from keywords.base_keyword import BaseKeyword


class ProcessStatusArgsKeywords(BaseKeyword):
    """
    Class for "ps -o args" keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_process_arguments_as_string(self, process_name) -> str:
        """
        This function will return the command line arguments associated with the specified process.

        Args:
            process_name: The name of the process for which we want to get the command line arguments.

        Returns: A string containing the process name with all command line arguments.

        """
        output = self.ssh_connection.send(f'ps -C {process_name} -o args= | cat')
        self.validate_success_return_code(self.ssh_connection)

        # output is a list with one value
        output_string = output[0]
        return output_string
