import time

from config.host.objects.host_configuration import HostConfiguration
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.base_keyword import BaseKeyword


class ProxmoxKeywords(BaseKeyword):
    """
    Class for Proxmox PTP VM Keywords
    """

    def __init__(self, proxmox_vm_config: HostConfiguration):
        """Initializes the ProxmoxKeywords.

        Args:
            proxmox_vm_config (HostConfiguration): Proxmox VM configuration
        """
        self.proxmox_vm_config = proxmox_vm_config
        self.proxmox_vm_connection = None

    def get_proxmox_vm_ssh_connection(self) -> SSHConnection:
        """
        Gets the PTP VM SSH connection using configuration from proxmox_ptp_vm_config

        Returns:
            SSHConnection: the SSH connection to the PTP VM
        """
        if self.proxmox_vm_connection is None:
            if not self.proxmox_vm_config:
                raise ValueError("No proxmox_ptp_vm_config found in PTP NIC configuration")

            self.proxmox_vm_connection = SSHConnectionManager.create_ssh_connection(
                self.proxmox_vm_config.get_host(),
                self.proxmox_vm_config.get_credentials().get_user_name(),
                self.proxmox_vm_config.get_credentials().get_password(),
            )

            get_logger().log_info(f"Connected to proxmox VM at {self.proxmox_vm_config.get_host()}")

        return self.proxmox_vm_connection

    def start_ptp_service(self) -> str:
        """
        Starts the PTP service by running runptp.sh script in background
        Creates the runptp.sh script if it doesn't exist

        Returns:
            str: the command output
        """
        ssh_connection = self.get_proxmox_vm_ssh_connection()

        get_logger().log_info("Starting PTP service with runptp.sh")

        # Check if runptp.sh exists
        check_cmd = "test -f ./runptp.sh && echo 'exists' || echo 'not found'"
        check_output = ssh_connection.send(check_cmd)

        if "not found" in str(check_output):
            get_logger().log_info("runptp.sh not found, creating it")

            # Create runptp.sh with the required content
            create_script_cmd = """cat > runptp.sh << 'EOF'
                #!/bin/bash
                ptp4l -2 -S -m -A -f /etc/ptp4l.conf
                EOF"""
            ssh_connection.send(create_script_cmd)

            # Make it executable
            chmod_cmd = "chmod +x runptp.sh"
            ssh_connection.send(chmod_cmd)

            get_logger().log_info("runptp.sh created and made executable")
        else:
            get_logger().log_info("runptp.sh already exists")

        # Start the runptp.sh script in background
        cmd = "nohup ./runptp.sh > /dev/null 2>&1"
        output = ssh_connection.send_as_sudo(cmd)

        time.sleep(10)  # Wait longer for service to stabilize
        service_running = self._verify_ptp_service_running()
        if service_running:
            get_logger().log_info("PTP service auto-recovery completed successfully")
        else:
            raise Exception("Failed to start PTP service")

        get_logger().log_info("PTP service started")
        return output

    def _verify_ptp_service_running(self) -> bool:
        """
        Verifies that the PTP service (runptp.sh) is running

        Returns:
            bool: True if the service is running, False otherwise
        """
        ssh_connection = self.get_proxmox_vm_ssh_connection()

        get_logger().log_info("Checking if PTP service is running")

        cmd = "ps aux | grep runptp"
        output = ssh_connection.send(cmd)

        # Handle both string and list outputs
        if isinstance(output, list):
            output_lines = output
        else:
            output_lines = output.split("\n")

        # Check if runptp processes are found (excluding the grep command itself)
        running_processes = [line for line in output_lines if "runptp" in line and "grep" not in line]

        is_running = len(running_processes) > 0

        if is_running:
            get_logger().log_info(f"PTP service is running. Found {len(running_processes)} processes:")
            for process in running_processes:
                get_logger().log_info(f"  {process.strip()}")
        else:
            get_logger().log_warning("PTP service is not running")

        return is_running

    def verify_ptp_service_with_auto_recovery(self):
        """
        Verifies PTP service is running and automatically starts it if not running
        Includes automated recovery mechanism for PTP service management
        """
        get_logger().log_info("Verifying PTP service status with auto-recovery")

        # Check if service is running, start if needed
        service_running = self._verify_ptp_service_running()

        if not service_running:
            get_logger().log_warning("PTP service is not running - initiating auto-recovery")
            self.start_ptp_service()

    def stop_ptp_service(self) -> str:
        """
        Stops the PTP service by killing runptp.sh processes

        Returns:
            str: the command output
        """
        ssh_connection = self.get_proxmox_vm_ssh_connection()

        get_logger().log_info("Stopping PTP service")

        # Kill all runptp processes
        cmd = "pkill -f runptp.sh"
        output = ssh_connection.send_as_sudo(cmd)

        get_logger().log_info("PTP service stopped")
        return output
