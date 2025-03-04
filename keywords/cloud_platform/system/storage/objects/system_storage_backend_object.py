import re

from keywords.cloud_platform.system.host.objects.storage_capabilities_object import (
    StorageCapabilities,
)


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

        Returns:
            str: name
        """
        return self.name

    def set_uuid(self, uuid: str):
        """
        Setter for uuid

        Args:
            uuid(str) : uuid

        Returns: None
        """
        self.uuid = uuid

    def get_uuid(self) -> str:
        """
        Getter for uuid

        Returns:
            str: uuid
        """
        return self.uuid

    def set_backend(self, backend: str):
        """
        Setter for backend

        Args:
            backend(str) : backend

        Returns: None
        """
        self.backend = backend

    def get_backend(self) -> str:
        """
        Getter for backend

        Returns:
            str: backend
        """
        return self.backend

    def set_state(self, state: str):
        """
        Setter for state

        Args:
            state(str) : state

        Returns: None
        """
        self.state = state

    def get_state(self) -> str:
        """
        Getter for state

        Returns:
            str: state
        """
        return self.state

    def set_task(self, task: str):
        """
        Setter for task

        Args:
            task(str) : task

        Returns: None
        """
        self.task = task

    def get_task(self) -> str:
        """
        Getter for task

        Returns:
            str: task
        """
        return self.task

    def set_services(self, services: str):
        """
        Setter for services

        Args:
            services(str) : services

        Returns: None
        """
        self.services = services

    def get_services(self) -> str:
        """
        Getter for services

        Returns:
            str: service
        """
        return self.services

    def add_capabilities(self, capabilities_output: str):
        """
        Setter for storage capabilities or adds capabilities to existing object if it is already set.

        Args:
            capabilities_output(str): capabilities_output

        Raises:
            ValueError: If the capabilities output items is not an even number
        Raises:
            ValueError: If the key name not either replication or min_replication
        Returns: None
        """
        if not self.capabilities:
            self.capabilities = StorageCapabilities()

        # str "capabilities_output" is like "replication: 2min_replication: 1"
        # Add space after a number if followed by a non-number
        capabilities_output = re.sub(r"([0-9]+)([a-zA-Z]+)", r"\1 \2", capabilities_output)

        # Add space before "replication" unless preceded by "_" to avoid change for "min_replication"
        capabilities_output = re.sub(r"(?<!_)replication", r" replication", capabilities_output)

        # Add space before "min_replication"
        capabilities_output = re.sub(r"min_", r" min_", capabilities_output)

        # Add space before "deployment_model"
        capabilities_output = re.sub(r"deploy", r" deploy", capabilities_output)

        # remove all colon
        capabilities_output = capabilities_output.replace(":", "")

        tokenized_capability = capabilities_output.split()
        if len(tokenized_capability) % 2 != 0:
            raise ValueError(f"Unexpected format for add_capabilities {capabilities_output}. Expecting 'key:value' pair.")

        for i in range(0, len(tokenized_capability), 2):
            key = tokenized_capability[i]
            value = tokenized_capability[i + 1]
            if key == "replication":
                self.capabilities.set_replication(int(value))
            elif key == "min_replication":
                self.capabilities.set_min_replication(int(value))
            elif key == "deployment_model":
                self.capabilities.set_deployment_model(value)
            else:
                raise ValueError("Cannot set value of StorageCapability for key: {key}")

    def get_capabilities(self) -> StorageCapabilities:
        """
        Getter for capabilities
        """
        return self.capabilities
