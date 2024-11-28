from typing import Optional

import json5
from keywords.cloud_platform.system.controllerfs.objects.filesystem_state import FileSystemState
from keywords.cloud_platform.system.controllerfs.objects.filesystem_capabilities import FileSystemCapability

class SystemControllerFSObject:
    """
    This class represents a controllerfs as an object.
    This is typically a line in the system controllerfs-list output table.
    """

    def __init__(
            self,
            uuid: str,
            name: str,
            size: int,
            logical_volume: str,
            replicated: bool,
            created_at: Optional[str] = None,
            updated_at: Optional[str] = None
    ):
        self.uuid = uuid
        self.name = name
        self.size = size
        self.logical_volume = logical_volume
        self.replicated = replicated
        self.state: FileSystemState = None
        self.capabilities : FileSystemCapability = None
        self.created_at : created_at
        self.updated_at : updated_at

    def get_uuid(self) -> str:
        """
        Getter for controller-fs's UUID
        """
        return self.uuid

    def get_name(self) -> str:
        """
        Getter for this controller-fs's name
        """
        return self.name

    def get_size(self) -> int:
        """
        Getter for this controller-fs's size
        """
        return self.size

    def get_logical_volume(self) -> str:
        """
        Getter for this controller-fs's logical volume class
        """
        return self.logical_volume

    def get_replicated(self) -> bool:
        """
        Getter for this controller-fs's replicated
        """
        return self.replicated

    def set_state(self, state):
        """
        Setter for this controller-fs's state
        """
        if state.__contains__('None'):
            state = state.replace("None", '"None"')
        json_output = json5.loads(state)

        fs_state = FileSystemState()
        if 'status' in json_output :
            fs_state.set_status(json_output['status'])

        self.state = fs_state

    def get_state(self) -> FileSystemState :
        """
        Getter for capabilities
        Returns:

        """
        return self.state

    def set_capabilities(self, capabilities):
        """
        Setter for this controller-fs's capabilities
        """
        if capabilities.__contains__('None'):
            capabilities = capabilities.replace("None", '"None"')
        json_output = json5.loads(capabilities)

        fs_capabilities = FileSystemCapability()
        if 'functions' in json_output:
            fs_capabilities.set_functions(json_output['functions'])

        self.capabilities = fs_capabilities

    def get_capabilities(self) -> FileSystemCapability:
        """
        Getter for capabilities
        Returns:

        """
        return self.capabilities

    def get_created_at(self) -> str:
        """
        Getter for this controller-fs's created_at
        """
        return self.created_at

    def get_updated_at(self) -> str:
        """
        Getter for this controller-fs's updated_at
        """
        return self.updated_at
