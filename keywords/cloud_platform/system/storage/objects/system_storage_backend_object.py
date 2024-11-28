from keywords.cloud_platform.system.host.objects.storage_capabilities_object import StorageCapabilities


class SystemStorageBackendObject:
    """
    This class represents a Storage Backend as an object.
    This is typically a line in the system storage-backend-list output table.
    """

    def __init__(self, name: str):
        self.name: str = name
        self.uuid: str = None
        self.backend: str = None
        self.state: str = None
        self.task: str = None
        self.services: str = None
        self.capabilities: StorageCapabilities = None

    def get_name(self) -> str:
        """
        Getter for this storage's name
        """
        return self.name

    def set_uuid(self, uuid: str):
        """
        Setter for uuid
        Args:
            uuid:

        Returns:

        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for uuid
        Returns:

        """
        return self.uuid

    def set_backend(self, backend: str):
        """
        Setter for backend
        Args:
            backend:

        Returns:

        """
        self.backend = backend

    def get_backend(self) -> str:
        """
        Getter for backend
        Returns:

        """
        return self.backend

    def set_state(self, state: str):
        """
        Setter for state
        Args:
            state:

        Returns:

        """
        self.state = state

    def get_state(self) -> str:
        """
        Getter for state
        Returns:

        """
        return self.state

    def set_task(self, task: str):
        """
        Setter for task
        Args:
            task:

        Returns:

        """
        self.task = task

    def get_task(self) -> str:
        """
        Getter for task
        Returns:

        """
        return self.task

    def set_services(self, services: str):
        """
        Setter for services
        Args:
            services:

        Returns:

        """
        self.services = services

    def get_services(self) -> str:
        """
        Getter for services
        Returns:

        """
        return self.services

    def add_capabilities(self, capabilities_output: str):
        """
        Setter for storage capabilities
        Adds capabilities to existing object if it is already set.
        Args:
            capabilities_output (): the string of capabilities from the system storage-backend-list command
                                    e.g. "replication: 1", "min_replication: 1"

        Returns: None

        """

        if not self.capabilities:
            self.capabilities = StorageCapabilities()

        tokenized_capability = capabilities_output.split(":")
        if len(tokenized_capability) != 2:
            raise ValueError(f"Unexpected format for add_capabilities {capabilities_output}. Expecting 'key:value' pair.")

        key = tokenized_capability[0].strip()
        value = tokenized_capability[1].strip()

        if key == 'replication':
            self.capabilities.set_replication(int(value))
        elif key == 'min_replication':
            self.capabilities.set_min_replication(int(value))
        else:
            raise ValueError("Cannot set value of StorageCapability for key: {key}")

    def get_capabilities(self) -> StorageCapabilities:
        """
        Getter for capabilities
        Returns:

        """
        return self.capabilities
