import json5
from keywords.cloud_platform.system.controllerfs.objects.filesystem_capabilities import FileSystemCapability


class SystemHostFSObject:
    """
    Represents a host filesystem as an object.

    This class typically corresponds to a line in the system host-fs-(show/list) output table.

    Attributes:
        uuid (str): Unique identifier for the filesystem.
        name (str): Name of the filesystem.
        size (int): Size of the filesystem.
        logical_volume (str): Logical volume associated with the filesystem.
        state (str): State of the filesystem.
        capabilities (FileSystemCapability): Capabilities of the filesystem.
    """

    def __init__(
            self,
            uuid: str,
            name: str,
            size: int,
            logical_volume: str,
            state: str,
    ):
        """
        Initializes a SystemHostFSObject instance.

        Args:
            uuid (str): Unique identifier for the filesystem.
            name (str): Name of the filesystem.
            size (int): Size of the filesystem.
            logical_volume (str): Logical volume associated with the filesystem.
            state (str): State of the filesystem.
        """
        self.uuid = uuid
        self.name = name
        self.size = size
        self.logical_volume = logical_volume
        self.state = state
        self.capabilities: FileSystemCapability = None
        self.created_at = None
        self.updated_at = None

    def get_uuid(self) -> str:
        """
        Gets the UUID of the host filesystem.

        Returns:
            str: The UUID of the host filesystem.
        """
        return self.uuid

    def get_name(self) -> str:
        """
        Gets the name of the host filesystem.

        Returns:
            str: The name of the host filesystem.
        """
        return self.name

    def get_size(self) -> int:
        """
        Gets the size of the host filesystem.

        Returns:
            int: The size of the host filesystem.
        """
        return self.size

    def get_logical_volume(self) -> str:
        """
        Gets the logical volume associated with the host filesystem.

        Returns:
            str: The logical volume of the host filesystem.
        """
        return self.logical_volume

    def get_state(self) -> str:
        """
        Gets the state of the host filesystem.

        Returns:
            str: The state of the host filesystem.
        """
        return self.state

    def set_capabilities(self, capabilities: str):
        """
        Sets the capabilities of the host filesystem.

        Args:
            capabilities (str): JSON string representing the capabilities of the filesystem.
        """
        if 'None' in capabilities:
            capabilities = capabilities.replace("None", '"None"')
        json_output = json5.loads(capabilities)

        fs_capabilities = FileSystemCapability()
        if 'functions' in json_output:
            fs_capabilities.set_functions(json_output['functions'])

        self.capabilities = fs_capabilities

    def get_capabilities(self) -> FileSystemCapability:
        """
        Gets the capabilities of the host filesystem.

        Returns:
            FileSystemCapability: The capabilities of the host filesystem.
        """
        return self.capabilities

    def set_created_at(self, created_at:str):
        """
        Gets the creation timestamp of the host filesystem.

        Args:
            created_at: The creation timestamp of the host filesystem.
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Gets the creation timestamp of the host filesystem.

        Returns:
            str: The creation timestamp of the host filesystem.
        """
        return self.created_at

    def set_updated_at(self, updated_at:str):
        """
        Gets the creation timestamp of the host filesystem.

        Args:
            updated_at: The creation timestamp of the host filesystem.
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Gets the last updated timestamp of the host filesystem.

        Returns:
            Optional[str]: The last updated timestamp of the host filesystem.
        """
        return self.updated_at
