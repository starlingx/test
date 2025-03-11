from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.storage.objects.system_storage_backend_output import SystemStorageBackendOutput


class SystemStorageBackendKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'system storage-backend-*' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection) : ssh_connection
        """
        self.ssh_connection = ssh_connection

    def get_system_storage_backend_list(self) -> SystemStorageBackendOutput:
        """
        Gets the system backend list

        Returns: list[str]

        """
        output = self.ssh_connection.send(source_openrc("system storage-backend-list --nowrap"))
        self.validate_success_return_code(self.ssh_connection)
        system_storage_backend_output = SystemStorageBackendOutput(output)

        return system_storage_backend_output

    def system_storage_backend_add(self, backend: str, confirmed: bool = True, deployment_model: str = None):
        """
        Adds the storage backend

        Args:
            backend (str): the backend ceph or ceph-rook
            confirmed (bool): True or False
            deployment_model (str): deployment_model

        """
        extra_args = ""
        if confirmed:
            extra_args += " --confirmed"
        if deployment_model:
            extra_args += f" --deployment {deployment_model}"

        self.ssh_connection.send(source_openrc(f"system storage-backend-add {backend} {extra_args}"))
        self.validate_success_return_code(self.ssh_connection)
