class SystemPTPObject:
    """
    Represents a SystemPTPObject with associated attributes.

    Attributes:
        uuid (str): Unique identifier for the PTP object.
        mode (str): Mode of the PTP object.
        transport (str): Transport type of the PTP object.
        mechanism (str): mechanism of the PTP object
        isystem_uuid (str): System UUID associated with the PTP object.
    """

    def __init__(
            self,
            uuid: str,
            mode: str,
            transport: str,
            mechanism: str,
            isystem_uuid: str,
    ):
        """
        Initializes a SystemPTPObject instance.

        Args:
            uuid (str): Unique identifier for the PTP object.
            mode (str): Mode of the PTP object.
            transport (str): Transport type of the PTP object.
            mechanism (str): Mechanism of the PTP object.
            isystem_uuid (str): System UUID associated with the PTP object.
        """

        self.uuid = uuid
        self.mode = mode
        self.transport = transport
        self.mechanism = mechanism
        self.isystem_uuid = isystem_uuid
        self.created_at: str = ''
        self.updated_at: str = ''

    def get_uuid(self) -> str:
        """
        Gets the UUID of the PTP object.

        Returns:
            str: The UUID of the PTP object.
        """
        return self.uuid

    def get_mode(self) -> str:
        """
        Gets the mode of the PTP object.

        Returns:
            str: The mode of the PTP object.
        """
        return self.mode

    def get_transport(self) -> str:
        """
        Gets the transport type of the PTP object.

        Returns:
            str: The transport type of the PTP object.
        """
        return self.transport

    def get_mechanism(self) -> str:
        """
        Get the mechanism associated with the object.

        Returns:
            str: The mechanism of the PTP object.
        """
        return self.mechanism

    def get_isystem_uuid(self) -> str:
        """
        Gets the system UUID associated with the PTP object.

        Returns:
            str: The system UUID associated with the PTP object.
        """
        return self.isystem_uuid

    def set_created_at(self, created_at: str):
        """
        Sets the creation timestamp of the PTP object.

        Args:
            created_at (str): The creation timestamp to set.
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Gets the creation timestamp of the PTP object.

        Returns:
            str: The creation timestamp of the PTP object.
        """
        return self.created_at

    def set_updated_at(self, updated_at: str):
        """
        Sets the last updated timestamp of the PTP object.

        Args:
            updated_at (str): The last updated timestamp to set.
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Gets the last updated timestamp of the PTP object.

        Returns:
            str: The last updated timestamp of the PTP object.
        """
        return self.updated_at
