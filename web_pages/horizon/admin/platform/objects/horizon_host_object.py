from typing import List


class HorizonHostObject:
    """
    This class represents the information about a host as displayed in Horizon.
    """

    def __init__(self, row_values_list: List[str]):
        """
        Constructor
        Args:
            row_values_list: is a list of the row values in the host inventory table.
        """

        if len(row_values_list) != 8:
            raise ValueError("Expecting 8 values to build a HorizonHostObject.")

        self.host_name = row_values_list[0]
        self.personality = row_values_list[1]
        self.admin_state = row_values_list[2]
        self.operational_state = row_values_list[3]
        self.availability_state = row_values_list[4]
        self.uptime = row_values_list[5]
        self.status = row_values_list[6]
        # row_values_list[7] is the Actions button, which needs to be handled separately

    def get_host_name(self) -> str:
        """
        Getter for the host_name
        Returns:

        """
        return self.host_name

    def get_personality(self) -> str:
        """
        Getter for the personality
        Returns:

        """
        return self.personality

    def get_admin_state(self) -> str:
        """
        Getter for the admin_state
        Returns:

        """
        return self.admin_state

    def get_operational_state(self) -> str:
        """
        Getter for the operational_state
        Returns:

        """
        return self.operational_state

    def get_availability_state(self) -> str:
        """
        Getter for the availability_state
        Returns:

        """
        return self.availability_state

    def get_uptime(self) -> str:
        """
        Getter for the uptime
        Returns:

        """
        return self.uptime

    def get_status(self) -> str:
        """
        Getter for the status
        Returns:

        """
        return self.status
