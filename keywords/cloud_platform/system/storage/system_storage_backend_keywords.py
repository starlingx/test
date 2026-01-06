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

    def system_storage_backend_modify(self, backend: str, services: str = None, deployment_model: str = None, replication: int = 0, min_replication: int = 0):
        """
        Modify the storage backend

        Args:
            backend (str): the backend name ceph or ceph-rook
            services (str): New services value
            deployment_model (str): new deployment_model
            replication (int): new replication value
            min_replication (int): min_replication value

        """
        extra_args = ""
        if deployment_model:
            extra_args += f"--deployment {deployment_model} "
        if services:
            extra_args += f"--services {services} "
        if replication > 0:
            extra_args += f"replication={replication} "
        if min_replication > 0:
            extra_args += f"min_replication={min_replication} "

        self.ssh_connection.send(source_openrc(f"system storage-backend-modify {backend}-store {extra_args}"))
        self.validate_success_return_code(self.ssh_connection)

    def system_storage_backend_modify_with_error(self, backend: str, services: str = None, deployment_model: str = None, replication: int = 0, min_replication: int = 0) -> str:
        """
        Run the "system storage-backend-modify" command with invalid arguments

        Args:
            backend (str): the backend name ceph or ceph-rook
            services (str): New services value
            deployment_model (str): new deployment_model
            replication (int): new replication value
            min_replication (int): min_replication value
        Returns:
             str: a str of error msg
        """
        extra_args = ""
        if deployment_model:
            extra_args += f"--deployment {deployment_model} "
        if services:
            extra_args += f"--services {services} "
        if replication > 0:
            extra_args += f"replication={replication} "
        if min_replication > 0:
            extra_args += f"min_replication={min_replication} "

        msg = self.ssh_connection.send(source_openrc(f"system storage-backend-modify {backend}-store {extra_args}"))
        return msg[0]

    def system_storage_backend_delete(self, backend: str):
        """
        Delete the storage backend

        Args:
            backend (str): the backend name ceph or ceph-rook

        """
        self.ssh_connection.send(source_openrc(f"system storage-backend-delete {backend}-store --force"))
        self.validate_success_return_code(self.ssh_connection)

    def system_storage_backend_delete_with_error(self, backend: str) -> str:
        """
        Run the "system storage-backend-delete" command while rook-ceph app is applied

        Args:
            backend (str): the backend name ceph or ceph-rook
        Returns:
             str: a str of error msg
        """
        msg = self.ssh_connection.send(source_openrc(f"system storage-backend-delete {backend}-store --force"))
        return msg[0]

    def system_storage_backend_delete_without_force(self, backend: str) -> str:
        """
        storage-backend-delete cmd negative testing, Delete the storage backend cmd missed argument --force

        Args:
            backend (str): the backend name ceph or ceph-rook
        Returns:
             str: a list of error msg
        """
        msg = self.ssh_connection.send(source_openrc(f"system storage-backend-delete {backend}-store"))
        return msg[0]
