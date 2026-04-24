"""Keywords for virtctl client operations."""

import re

from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.base_keyword import BaseKeyword
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class VirtctlKeywords(BaseKeyword):
    """Keywords for virtctl client operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize VirtctlKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host.
        """
        self._ssh_connection: SSHConnection = ssh_connection

    def virtctl_pause(self, vm_name: str) -> str:
        """Pause a virtual machine.

        Args:
            vm_name (str): Name of the VM to pause.

        Returns:
            str: Command output.
        """
        output = self._ssh_connection.send(f"virtctl pause vm {vm_name}", fail_ok=False)
        self.validate_success_return_code(self._ssh_connection)
        return output

    def login_to_vm(
        self,
        vm_name: str,
        username: str,
        password: str,
        namespace: str = "default",
    ) -> None:
        """Login to a cirros VM via virtctl console and verify it is accessible.

        Opens a new SSH connection, attaches to the VM console, and logs in.

        Example command flow::

            virtctl console vm-cirros
            <login prompt> -> username
            <password prompt> -> password
            $

        Args:
            vm_name (str): Name of the VM to connect to.
            username (str): VM login username.
            password (str): VM login password.
            namespace (str): Namespace of the VM. Defaults to 'default'.

        Raises:
            KeywordException: If the console login fails.
        """
        get_logger().log_info(f"Opening virtctl console to VM {vm_name}")

        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        prompts = [
            PromptResponse(f"{vm_name}", None),
            PromptResponse("login:", username),
            PromptResponse("assword:", password),
            PromptResponse("$", None),
        ]

        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts)
        self.validate_success_return_code(self._ssh_connection)
        get_logger().log_info(f"Successfully logged into VM {vm_name}")

    def verify_vm_console_accessible(
        self,
        vm_name: str,
        namespace: str = "default",
    ) -> None:
        """Verify a VM is accessible via virtctl console without full login.

        Connects to the VM console and checks for the 'Successfully connected' message.
        Useful when the VM may already be logged in from a previous session (e.g., after
        live migration) and the login prompt is not expected.

        Args:
            vm_name (str): Name of the VM to connect to.
            namespace (str): Namespace of the VM. Defaults to 'default'.

        Raises:
            KeywordException: If the console connection fails.
        """
        get_logger().log_info(f"Verifying VM {vm_name} console is accessible")

        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        prompts = [
            PromptResponse("Successfully connected", None),
        ]

        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts)
        self.validate_success_return_code(self._ssh_connection)
        get_logger().log_info(f"VM {vm_name} console is accessible")

    def check_vm_cpu_count(self, vm_name: str, expected_cpus: int, username: str = "cirros", password: str = "gocubsgo", namespace: str = "default") -> None:
        """
        Verify the VM has the expected number of CPUs via virtctl console.

        Connects to the VM console, sends a newline to get the login prompt,
        logs in with username/password, runs 'lscpu' to get the CPU count,
        then exits and disconnects. Follows the same pattern as
        login_to_vm_and_check_status_cirros in CGCSAuto.

        Args:
            vm_name (str): Name of the VM to check.
            expected_cpus (int): Expected number of CPUs.
            username (str): VM login username. Defaults to 'cirros'.
            password (str): VM login password. Defaults to 'gocubsgo'.
            namespace (str): Namespace of the VM. Defaults to 'default'.

        Raises:
            KeywordException: If the CPU count doesn't match or console fails.
        """
        get_logger().log_info(f"Checking CPU count for VM {vm_name}, expecting {expected_cpus}")

        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        prompts = [
            PromptResponse(f"{vm_name}", ""),
            PromptResponse("login:", username),
            PromptResponse("assword:", password),
            PromptResponse("$", "lscpu | grep 'CPU(s):'"),
            PromptResponse("$", "exit"),
            PromptResponse("login:", None),
        ]

        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts)
        self.validate_success_return_code(self._ssh_connection)

        lscpu_output = prompts[4].get_complete_output()
        get_logger().log_info(f"lscpu output: {lscpu_output}")

        match = re.findall(r"CPU\(s\):\s+(\d+)", lscpu_output)
        if match:
            cpu_count = int(match[0])
            validate_equals(cpu_count, expected_cpus, f"VM {vm_name} should have {expected_cpus} CPUs")
            get_logger().log_info(f"VM {vm_name} has {cpu_count} CPUs as expected")
        else:
            get_logger().log_error(f"Could not parse lscpu output: {lscpu_output}")
            validate_equals(0, expected_cpus, f"VM {vm_name} lscpu output could not be parsed")

    def image_upload(
        self,
        image_path: str,
        pvc_name: str,
        pvc_size: str,
        uploadproxy_url: str,
        insecure: bool = True,
        access_mode: str = "ReadWriteMany",
        namespace: str = "default",
        storage_class: str = None,
        command_timeout: int = 600,
        no_create: bool = False,
    ) -> str:
        """
        Upload image to CDI using virtctl image-upload.

        Runs ``virtctl image-upload dv`` to upload a QCOW2 or raw image into a
        DataVolume backed by a PVC. Handles the case where the DataVolume already
        exists and is populated.

        Args:
            image_path (str): Path to the image file on the remote host.
            pvc_name (str): Name of the DataVolume to upload into.
            pvc_size (str): Size of the DataVolume (e.g., "5Gi").
            uploadproxy_url (str): CDI uploadproxy URL.
            insecure (bool): Skip TLS verification. Defaults to True.
            access_mode (str): Access mode for PVC. Defaults to "ReadWriteMany".
            namespace (str): Kubernetes namespace. Defaults to "default".
            storage_class (str): Storage class name. Defaults to None.
            command_timeout (int): Timeout in seconds for the upload command. Defaults to 600.
            no_create (bool): If True, adds --no-create flag to skip DV creation. Defaults to False.

        Returns:
            str: Command output.

        Raises:
            AssertionError: If image upload fails.
        """
        get_logger().log_info(f"Uploading image {image_path} to DataVolume {pvc_name}")
        insecure_flag = "--insecure" if insecure else ""
        storage_class_flag = f"--storage-class={storage_class}" if storage_class else ""
        no_create_flag = "--no-create" if no_create else ""
        cmd = f"bash -lc 'virtctl image-upload dv {pvc_name} {insecure_flag} " f"--access-mode {access_mode} --size {pvc_size} " f"--image-path {image_path} --uploadproxy-url {uploadproxy_url} " f"{storage_class_flag} {no_create_flag} --namespace {namespace}'"
        self._ssh_connection.send(export_k8s_config(cmd), command_timeout=command_timeout)
        self.validate_success_return_code(self._ssh_connection)
        get_logger().log_info(f"Image uploaded successfully to DataVolume {pvc_name}")
