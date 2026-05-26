"""WRA (Wind River Analytics) Setup Keywords.

Provides reusable methods for deploying WRA on DC systems.
Can be called from test files or other keywords.
"""

import textwrap

from config.system_test.objects.wra_server_config import WraServerConfig
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.show.system_show_keywords import SystemShowKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


WRA_APP_NAME = "wr-analytics"
WRA_NAMESPACE = "monitor"
WRA_TARBALL_DIR = "/home/sysadmin"
METRICBEAT_OVERRIDES_FILENAME = "sys-eng-overrides.yaml"
SECURITY_OVERRIDES_FILENAME = "elastic-services-security-overrides.yaml"
UPLOAD_APPLY_TIMEOUT = 3600
APPLY_POLL_INTERVAL = 60

# Labels for system controller (controllers and workers)
SC_CONTROLLER_LABELS = (
    "kafka-zookeeper=enabled "
    "elastic-data=enabled "
    "kafka-broker=enabled "
    "elastic-master=enabled "
    "elastic-controller=enabled "
    "elastic-client=enabled"
)

# Labels for workers on system controller
SC_WORKER_LABELS = "elastic-master=enabled kafka-zookeeper=enabled"

# Labels for subcloud controller
SUBCLOUD_CONTROLLER_LABELS = "elastic-controller=enabled"

# Metricbeat sys-eng-overrides content
METRICBEAT_OVERRIDES_CONTENT = textwrap.dedent("""\
    daemonset:
      moduleConfig:
        system:
          core:
            core.metrics: [percentages]
            metricsets: [core]
            module: system
            period: 5s
          cpu:
            cpu.metrics: [normalized_percentages]
            metricsets: [cpu]
            module: system
            period: 5s
          diskio:
            cpu.metrics: [normalized_percentages]
            metricsets: [diskio]
            module: system
            period: 5s
          filesystem:
            metricsets: [filesystem]
            module: system
            period: 5s
            processors:
              - drop_event.when:
                  regexp: {system.filesystem.mount_point: ^/(sys|cgroup|proc|dev|host|lib)($|/)}
          memory:
            cpu.metrics: [normalized_percentages]
            metricsets: [memory]
            module: system
            period: 5s
          load:
            metricsets: [load]
            module: system
            period: 5s
          network:
            metricsets: [network]
            module: system
            period: 5s
            processors:
              - drop_event.when:
                  or:
                    - regexp: {system.network.name: ^(docker0|cali.*)$}
                    - and:
                        - equals: {system.network.in.packets: 0}
                        - equals: {system.network.out.packets: 0}
          process:
            metricsets: [process]
            module: system
            period: 5s
            process.include_top_n.enabled: false
            processes: [.*]
            processors:
              - drop_event.when:
                  range:
                    system.process.cpu.total.pct.lte: 0
""")


class SetupWraKeywords:
    """Keywords for deploying WRA on DC systems.

    This class provides reusable methods for WRA deployment that can be
    called from test files or other keywords.

    Args:
        sc_ssh: SSH connection to the system controller.
        subcloud_ssh: SSH connection to the subcloud.
        system_controller_ip: IP address of the system controller.
        ssh_user: SSH username for the system controller.
        ssh_password: SSH password for the system controller.
    """

    def __init__(
        self,
        sc_ssh: SSHConnection,
        subcloud_ssh: SSHConnection,
        system_controller_ip: str,
        ssh_user: str,
        ssh_password: str,
    ):
        self.sc_ssh = sc_ssh
        self.subcloud_ssh = subcloud_ssh
        self.system_controller_ip = system_controller_ip
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password

    def __str__(self) -> str:
        return f"SetupWraKeywords(sc={self.system_controller_ip})"

    def deploy_wra_dc(self) -> None:
        """Deploy WRA on a DC system (system controller + subcloud).

        Downloads the WRA tarball from the build server, deploys on the system
        controller with metricbeat overrides, then deploys on the subcloud with
        both metricbeat and security overrides.

        Raises:
            AssertionError: If WRA deployment fails on either system.
        """
        wra_config = self._load_wra_server_config()

        self._deploy_on_system_controller(wra_config)
        self._deploy_on_subcloud(wra_config)

        get_logger().log_info(
            "WRA DC deployment completed successfully on both system controller and subcloud"
        )

    def _deploy_on_system_controller(self, wra_config: WraServerConfig) -> None:
        """Deploy WRA on the system controller.

        Args:
            wra_config: WRA server configuration object.
        """
        get_logger().log_info("Download WRA tarball to system controller")
        sc_tarball_path = self._download_wra_tarball(self.sc_ssh, wra_config)

        get_logger().log_info("Remove existing WRA if present on system controller")
        if SystemApplicationListKeywords(self.sc_ssh).is_app_present(WRA_APP_NAME):
            get_logger().log_info(f"{WRA_APP_NAME} already present on system controller, removing")
            SystemApplicationRemoveKeywords(self.sc_ssh).cleanup_app_if_present(
                WRA_APP_NAME, force_removal=True, force_deletion=True, timeout_in_seconds=600
            )

        get_logger().log_info("Assign WRA labels on system controller hosts")
        hosts = SystemHostListKeywords(self.sc_ssh).get_system_host_list()
        for host in hosts.get_hosts():
            hostname = host.get_host_name()
            personality = host.get_personality()
            if "controller" in personality:
                self._assign_labels(self.sc_ssh, hostname, SC_CONTROLLER_LABELS)
            elif "worker" in personality:
                self._assign_labels(self.sc_ssh, hostname, SC_WORKER_LABELS)

        get_logger().log_info("Upload WRA on system controller")
        upload_input = SystemApplicationUploadInput()
        upload_input.set_app_name(WRA_APP_NAME)
        upload_input.set_tar_file_path(sc_tarball_path)
        SystemApplicationUploadKeywords(self.sc_ssh).system_application_upload(upload_input)

        get_logger().log_info("Create and apply metricbeat overrides on system controller")
        sc_overrides_path = self._create_metricbeat_overrides(self.sc_ssh)
        SystemHelmOverrideKeywords(self.sc_ssh).update_helm_override(
            sc_overrides_path, WRA_APP_NAME, "metricbeat", WRA_NAMESPACE
        )

        get_logger().log_info("Apply WRA on system controller")
        SystemApplicationApplyKeywords(self.sc_ssh).system_application_apply(
            WRA_APP_NAME, timeout=UPLOAD_APPLY_TIMEOUT, polling_sleep_time=APPLY_POLL_INTERVAL
        )

        get_logger().log_info("Verify WRA pods healthy on system controller")
        self._wait_for_wra_pods_healthy(self.sc_ssh)

        # Validate app status is applied
        SystemApplicationListKeywords(self.sc_ssh).validate_app_status(
            WRA_APP_NAME, "applied", timeout=60
        )

    def _deploy_on_subcloud(self, wra_config: WraServerConfig) -> None:
        """Deploy WRA on the subcloud.

        Args:
            wra_config: WRA server configuration object.
        """
        get_logger().log_info("Download WRA tarball to subcloud")
        subcloud_tarball_path = self._download_wra_tarball(self.subcloud_ssh, wra_config)

        get_logger().log_info("Remove existing WRA if present on subcloud")
        if SystemApplicationListKeywords(self.subcloud_ssh).is_app_present(WRA_APP_NAME):
            get_logger().log_info(f"{WRA_APP_NAME} already present on subcloud, removing")
            SystemApplicationRemoveKeywords(self.subcloud_ssh).cleanup_app_if_present(
                WRA_APP_NAME, force_removal=True, force_deletion=True, timeout_in_seconds=600
            )

        get_logger().log_info("Assign WRA labels on subcloud")
        subcloud_active_controller = SystemHostListKeywords(
            self.subcloud_ssh
        ).get_active_controller().get_host_name()
        self._assign_labels(self.subcloud_ssh, subcloud_active_controller, SUBCLOUD_CONTROLLER_LABELS)

        get_logger().log_info("Upload WRA on subcloud")
        upload_input = SystemApplicationUploadInput()
        upload_input.set_app_name(WRA_APP_NAME)
        upload_input.set_tar_file_path(subcloud_tarball_path)
        SystemApplicationUploadKeywords(self.subcloud_ssh).system_application_upload(upload_input)

        get_logger().log_info("Create and apply metricbeat overrides on subcloud")
        subcloud_overrides_path = self._create_metricbeat_overrides(self.subcloud_ssh)
        SystemHelmOverrideKeywords(self.subcloud_ssh).update_helm_override(
            subcloud_overrides_path, WRA_APP_NAME, "metricbeat", WRA_NAMESPACE
        )

        get_logger().log_info("Copy security overrides from system controller to subcloud")
        sw_version = self._get_software_version(self.sc_ssh)
        security_overrides_sc_path = (
            f"/opt/platform/config/{sw_version}/analytics/{SECURITY_OVERRIDES_FILENAME}"
        )

        get_logger().log_info("Copying security overrides from system controller to subcloud")
        FileKeywords(self.subcloud_ssh).rsync_from_remote_server(
            remote_server=self.system_controller_ip,
            remote_user=self.ssh_user,
            remote_password=self.ssh_password,
            remote_path=security_overrides_sc_path,
            local_dest_path=f"{WRA_TARBALL_DIR}/",
        )

        get_logger().log_info("Apply security overrides on subcloud")
        security_overrides_subcloud_path = f"{WRA_TARBALL_DIR}/{SECURITY_OVERRIDES_FILENAME}"
        SystemHelmOverrideKeywords(self.subcloud_ssh).update_helm_override(
            security_overrides_subcloud_path, WRA_APP_NAME, "elastic-services", WRA_NAMESPACE
        )

        get_logger().log_info("Apply WRA on subcloud")
        SystemApplicationApplyKeywords(self.subcloud_ssh).system_application_apply(
            WRA_APP_NAME, timeout=UPLOAD_APPLY_TIMEOUT, polling_sleep_time=APPLY_POLL_INTERVAL
        )

        get_logger().log_info("Verify WRA pods healthy on subcloud")
        self._wait_for_wra_pods_healthy(self.subcloud_ssh)

        # Validate app status is applied on subcloud
        SystemApplicationListKeywords(self.subcloud_ssh).validate_app_status(
            WRA_APP_NAME, "applied", timeout=60
        )

    def _load_wra_server_config(self) -> WraServerConfig:
        """Load the WRA server configuration from the config file.

        Returns:
            WraServerConfig: WRA server configuration object.
        """
        config_path = get_stx_resource_path("config/system_test/files/default_wra_server.json5")
        get_logger().log_info(f"Loading WRA server config from: {config_path}")
        return WraServerConfig(config_path)

    def _download_wra_tarball(self, ssh_connection: SSHConnection, wra_config: WraServerConfig) -> str:
        """Download the WRA tarball from the build server to the lab.

        Args:
            ssh_connection: SSH connection to the target host.
            wra_config: WRA server configuration object.

        Returns:
            str: Path to the downloaded tarball on the lab.
        """
        server = wra_config.get_server()
        user = wra_config.get_user()
        password = wra_config.get_password()
        base_path = wra_config.get_base_path()
        tarball_pattern = wra_config.get_tarball_pattern()
        destination = wra_config.get_destination_path()

        remote_path = f"{base_path}/{tarball_pattern}"
        get_logger().log_info(f"Downloading WRA tarball from {server}:{remote_path}")

        FileKeywords(ssh_connection).rsync_from_remote_server(
            remote_server=server,
            remote_user=user,
            remote_password=password,
            remote_path=remote_path,
            local_dest_path=f"{destination}/",
        )

        find_cmd = f"ls -t {destination}/wr-analytics-[0-9]*.tgz 2>/dev/null | head -1"
        output = ssh_connection.send(find_cmd)

        if isinstance(output, list):
            tarball_path = output[0].strip() if output else ""
        else:
            tarball_path = output.strip()

        get_logger().log_info(f"WRA tarball downloaded to: {tarball_path}")
        return tarball_path

    def _create_metricbeat_overrides(self, ssh_connection: SSHConnection) -> str:
        """Create the sys-eng-overrides.yaml file on the lab.

        Args:
            ssh_connection: SSH connection to the target host.

        Returns:
            str: Path to the created overrides file.
        """
        overrides_path = f"{WRA_TARBALL_DIR}/{METRICBEAT_OVERRIDES_FILENAME}"
        get_logger().log_info(f"Creating metricbeat overrides at: {overrides_path}")

        FileKeywords(ssh_connection).create_file_with_heredoc(
            overrides_path, METRICBEAT_OVERRIDES_CONTENT, delimiter="OVERRIDES_EOF"
        )

        return overrides_path

    def _assign_labels(self, ssh_connection: SSHConnection, hostname: str, labels: str) -> None:
        """Assign WRA labels to a host using --overwrite to avoid conflicts.

        Args:
            ssh_connection: SSH connection to the controller.
            hostname: Host to assign labels to.
            labels: Space-separated label assignments.
        """
        cmd = source_openrc(f"system host-label-assign --overwrite {hostname} {labels}")
        get_logger().log_info(f"Assigning labels to {hostname}: {labels}")
        ssh_connection.send(cmd)


    def _get_software_version(self, ssh_connection: SSHConnection) -> str:
        """Get the software version from the system.

        Args:
            ssh_connection: SSH connection to the controller.

        Returns:
            str: Software version string (e.g., '26.03').
        """
        system_show_output = SystemShowKeywords(ssh_connection).system_show()
        version = system_show_output.get_system_show_object().get_software_version()
        get_logger().log_info(f"Software version: {version}")
        return version

    def _wait_for_wra_pods_healthy(self, ssh_connection: SSHConnection, timeout: int = 600) -> None:
        """Wait for all WRA pods in the monitor namespace to be Running or Completed.

        Args:
            ssh_connection: SSH connection to the controller.
            timeout: Timeout in seconds.
        """
        get_logger().log_info(
            f"Waiting for WRA pods in '{WRA_NAMESPACE}' namespace to be healthy (timeout={timeout}s)"
        )
        KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(
            expected_status=["Running", "Completed"],
            namespace=WRA_NAMESPACE,
            timeout=timeout,
        )
        get_logger().log_info("All WRA pods are healthy")
