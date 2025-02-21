from keywords.base_keyword import BaseKeyword


class PhcCtlKeywords(BaseKeyword):
    """
    Directly control PHC device clock using given SSH connection.

    Attributes:
        ssh_connection: An instance of an SSH connection.
    """

    def __init__(self, ssh_connection):
        """
        Initializes the PhcCtlKeywords with an SSH connection.

        Args:
            ssh_connection: An instance of an SSH connection.
        """
        self.ssh_connection = ssh_connection

    def phc_ctl_get(self, device: str) -> str:
        """
        Get the current time of the PHC clock device

        Args:
            device : may be either CLOCK_REALTIME, any /dev/ptpX device, or any ethernet device which supports ethtool's get_ts_info ioctl.

        Example:
            phc_ctl[643764.828]: clock time is 1739856255.215802036 or Tue Feb 18 05:24:15 2025

        Returns:
        """
        output = self.ssh_connection.send_as_sudo(f"phc_ctl {device} get")
        self.validate_success_return_code(self.ssh_connection)
        output_str = ''.join(output).replace('\n', '')
        if output_str and len(output_str.split()) > 4:
            return output_str.split()[4]
        else:
            raise "output_str.split() is expected to be a List with four elements."

    def phc_ctl_cmp(self, device: str) -> str:
        """
        Compare the PHC clock device to CLOCK_REALTIME

        Args:
            device : may be either CLOCK_REALTIME, any /dev/ptpX device, or any ethernet device which supports ethtool's get_ts_info ioctl.

        Example:
            phc_ctl[645639.878]: offset from CLOCK_REALTIME is -37000000008ns

        Returns:
        """
        output = self.ssh_connection.send_as_sudo(f"phc_ctl {device} cmp")
        self.validate_success_return_code(self.ssh_connection)
        output_str = ''.join(output)
        if output_str and len(output_str.split()) > 5:
            return output_str.split()[5]
        else:
            raise "output_str.split() is expected to be a List with five elements."

    def phc_ctl_adj(self, device: str, seconds: str) -> str:
        """
        Adjust the PHC clock by an amount of seconds provided

        Args:
            device : may be either CLOCK_REALTIME, any /dev/ptpX device, or any ethernet device which supports ethtool's get_ts_info ioctl.
            seconds :

        Example:
            phc_ctl[646368.470]: adjusted clock by 0.000001 seconds

        Returns:
        """
        output = self.ssh_connection.send_as_sudo(f"phc_ctl {device} adj {seconds}")
        self.validate_success_return_code(self.ssh_connection)
        output_str = ''.join(output).replace('\n', '')
        if output_str and len(output_str.split()) > 5:
            return output_str.split()[4]
        else:
            raise "output_str.split() is expected to be a List with five elements."

    def phc_ctl_set(self, device: str, seconds: str = None) -> str:
        """
        Set the PHC clock time to the value specified in seconds. Defaults to reading CLOCK_REALTIME if no value is provided.

        Args:
            device : may be either CLOCK_REALTIME, any /dev/ptpX device, or any ethernet device which supports ethtool's get_ts_info ioctl.
            seconds :

        Example :
            phc_ctl[647759.416]: set clock time to 1739860212.789318498 or Tue Feb 18 06:30:12 2025

        Returns:
        """
        if seconds:
            cmd = f"phc_ctl {device} set {seconds}"
        else:
            cmd = f"phc_ctl {device} set"

        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        output_str = ''.join(output).replace('\n', '')
        if output_str and len(output_str.split()) > 5:
            return output_str.split()[5]
        else:
            raise "output_str.split() is expected to be a List with five elements."
