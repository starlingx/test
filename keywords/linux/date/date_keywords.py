from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class DateKeywords(BaseKeyword):
    """
    Date Keywords class
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def get_timezone(self):
        """
        Returns the timezone using a linux system command
        """
        date = self.ssh_connection.send("date +%Z")
        self.validate_success_return_code(self.ssh_connection)

        # can only be one line in the response + remove any trailing \n
        return date[0].strip()

    def get_current_date(self):
        """
        Returns the current date in the format YYYY-MM-DD using a linux system command
        """
        current_date = self.ssh_connection.send('date "+%Y-%m-%d"')
        self.validate_success_return_code(self.ssh_connection)

        # can only be one line in the response + remove any trailing \n
        return current_date[0].strip()

    def get_current_time(self) -> str:
        """
        Get the current system time.
        
        Returns:
            str: Current time in HH:MM:SS format
        """
        current_time = self.ssh_connection.send("date +%T")
        self.validate_success_return_code(self.ssh_connection)
        return current_time[0].strip()

    def get_current_datetime(self) -> str:
        """
        Get the current system date and time.
        
        Returns:
            str: Current datetime in YYYY-MM-DDTHH:MM:SS format (ISO 8601)
        """
        current_datetime = self.ssh_connection.send("date '+%Y-%m-%dT%H:%M:%S'")
        self.validate_success_return_code(self.ssh_connection)
        return current_datetime[0].strip()
