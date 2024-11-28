class SystemHostLabelObject:
    """
    Class to hold attributes of a system label host as returned by system label host list command
    """

    def __init__(
        self,
    ):
        self.uuid = None
        self.host_uuid = None
        self.host_name = None
        self.label_key = None
        self.label_value = None

    def set_uuid(self, uuid: str) -> None:
        """
        Setter for uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for uuid
        Returns: the uuid of the label

        """
        return self.uuid

    def set_host_uuid(self, host_uuid: str) -> None:
        """
        Setter for host_uuid
        """
        self.host_uuid = host_uuid

    def get_host_uuid(self) -> str:
        """
        Getter for host_uuid
        Returns: the host_uuid

        """
        return self.host_uuid

    def set_host_name(self, host_name: str) -> None:
        """
        Setter for host name
        """
        self.host_name = host_name

    def get_host_name(self) -> str:
        """
        Getter for host name
        Returns: the name of the host

        """
        return self.host_name

    def set_label_key(self, label_key: str) -> None:
        """
        Setter for label_key
        """
        self.label_key = label_key

    def get_label_key(self) -> str:
        """
        Getter for label key
        Returns:

        """
        return self.label_key

    def set_label_value(self, label_value: str) -> None:
        """
        Setter for label_value
        """
        self.label_value = label_value

    def get_label_value(self) -> str:
        """
        Getter for label value
        Returns:

        """
        return self.label_value
