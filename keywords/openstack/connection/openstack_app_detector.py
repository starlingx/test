"""Detect which OpenStack application is deployed on the system."""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords


# Default OpenStack application name
DEFAULT_OPENSTACK_APP = "stx-openstack"


class OpenStackAppDetector:
    """Detects which OpenStack application is deployed on the platform.

    Queries system application-list to find the deployed OpenStack app.
    Results are cached to avoid repeated CLI calls.
    """

    _cached_app_name: str = ""

    @staticmethod
    def get_openstack_app_name(ssh_connection: SSHConnection) -> str:
        """Discover the OpenStack application name from the platform.

        Queries system application-list and finds the application whose
        name contains 'openstack'.

        Args:
            ssh_connection (SSHConnection): SSH connection to the lab controller.

        Returns:
            str: Application name (e.g. 'stx-openstack').

        Raises:
            RuntimeError: If no OpenStack application is found.
        """
        if OpenStackAppDetector._cached_app_name:
            return OpenStackAppDetector._cached_app_name

        app_list_kw = SystemApplicationListKeywords(ssh_connection)
        app_list_output = app_list_kw.get_system_application_list()
        applications = app_list_output.get_applications()

        for app in applications:
            app_name = app.get_application()
            if "openstack" in app_name:
                get_logger().log_info(f"Detected OpenStack application: {app_name}")
                OpenStackAppDetector._cached_app_name = app_name
                return app_name

        get_logger().log_error("No OpenStack application found in system application-list")
        raise RuntimeError("No OpenStack application found on this system")

    @staticmethod
    def is_app(ssh_connection: SSHConnection, expected_app_name: str = DEFAULT_OPENSTACK_APP) -> bool:
        """Check if the deployed OpenStack app matches the expected name.

        Args:
            ssh_connection (SSHConnection): SSH connection to the lab controller.
            expected_app_name (str): App name to check against.
                Defaults to 'stx-openstack'.

        Returns:
            bool: True if the deployed app matches expected_app_name.
        """
        return OpenStackAppDetector.get_openstack_app_name(ssh_connection) == expected_app_name
