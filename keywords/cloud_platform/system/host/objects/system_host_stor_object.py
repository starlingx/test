class SystemHostStorageObject:
    """
    This class represents a Storage as an object.
    This is typically a line in the system host-stor-list output table.
    """

    def __init__(self):
        self.uuid = None
        self.function = None
        self.osdid = -1
        self.state = None
        self.idisk_uuid = None
        self.journal_path = None
        self.journal_node = None
        self.journal_size_gib = -1.0
        self.tier_name = None

    def set_uuid(self, uuid: str):
        """
        Setter for the storage's uuid
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for this storage's uuid
        """
        return self.uuid

    def set_function(self, function: str):
        """
        Setter for the storage's function
        """
        self.function = function

    def get_function(self) -> str:
        """
        Getter for this storage's function
        """
        return self.function

    def set_osdid(self, osdid: int):
        """
        Setter for the storage's osdid
        """
        self.osdid = osdid

    def get_osdid(self) -> int:
        """
        Getter for this storage's osdid
        """
        return self.osdid

    def set_state(self, state: str):
        """
        Setter for the storage's state
        """
        self.state = state

    def get_state(self) -> str:
        """
        Getter for this storage's state
        """
        return self.state

    def set_idisk_uuid(self, idisk_uuid: str):
        """
        Setter for the storage's idisk_uuid
        """
        self.idisk_uuid = idisk_uuid

    def get_idisk_uuid(self) -> str:
        """
        Getter for this storage's idisk_uuid
        """
        return self.idisk_uuid

    def set_journal_path(self, journal_path: str):
        """
        Setter for the storage's journal_path
        """
        self.journal_path = journal_path

    def get_journal_path(self) -> str:
        """
        Getter for this storage's journal_path
        """
        return self.journal_path

    def set_journal_node(self, journal_node: str):
        """
        Setter for the storage's journal_node
        """
        self.journal_node = journal_node

    def get_journal_node(self) -> str:
        """
        Getter for this storage's journal_node
        """
        return self.journal_node

    def set_journal_size_gib(self, journal_size_gib: float):
        """
        Setter for the storage's journal_size_gib
        """
        self.journal_size_gib = journal_size_gib

    def get_journal_size_gib(self) -> float:
        """
        Getter for this storage's journal_size_gib
        """
        return self.journal_size_gib

    def set_tier_name(self, tier_name: str):
        """
        Setter for the storage's tier_name
        """
        self.tier_name = tier_name

    def get_tier_name(self) -> str:
        """
        Getter for this storage's tier_name
        """
        return self.tier_name
