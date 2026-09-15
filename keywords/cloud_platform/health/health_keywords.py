from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.health_query.system_health_query_keywords import SystemHealthQueryKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.storage.system_storage_backend_keywords import SystemStorageBackendKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

# The ceph storage backend pulls in platform-integ-apps. When it is configured,
# platform-integ-apps is expected to be present and applied.
CEPH_STORAGE_BACKEND = "ceph"
PLATFORM_INTEG_APPS_NAME = "platform-integ-apps"


class HealthKeywords(BaseKeyword):
    """Class for health Keywords for Cloud Platform"""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh object

        """
        self.ssh_connection = ssh_connection

    def validate_healty_cluster(self):
        """Function to validate the health of the cluster

        This function checks the health of the cluster which consists of
            1. validate all hosts are healty
            2. validate all apps are healty and applied
            3. validate all pods are healty
            4. validate no alarms are present
            5. validate system health-query reports all checks OK
        """
        # Validate all hosts are healthy first so pods are only evaluated after their hosts are ready
        self.validate_hosts_health()
        # Validate all apps are healthy and applied
        self.validate_apps_health_and_applied()
        # Validate all pods are healthy
        self.validate_pods_health()
        # Validate no alarms are present
        self.validate_no_alarms()
        # Validate system health-query is fully OK last (e.g. host configurations are current). An
        # alarm can clear before health-query reports current configurations, so check this too.
        self.validate_system_health()

    def validate_system_health(self, timeout: int = 180, polling_sleep_time: int = 15):
        """Wait for 'system health-query' to report all checks OK.

        Polls 'system health-query' until every check passes. This catches conditions the alarm list
        does not reflect - notably "All hosts have current configurations" can still be Fail (host
        out-of-date config) after the corresponding alarm has already cleared. No dwell is used; a
        single fully-OK result is sufficient.

        Args:
            timeout (int): Maximum time in seconds to wait for all checks to pass. Defaults to 180.
            polling_sleep_time (int): Seconds between polls. Defaults to 15.
        """
        health_query_keywords = SystemHealthQueryKeywords(self.ssh_connection)

        def is_system_health_all_ok() -> bool:
            health_status = health_query_keywords.get_health_status()
            if health_status.is_all_healthy():
                return True
            failed = ", ".join(f"{check.get_check_name()} ({check.get_status()})" for check in health_status.get_failed_checks())
            get_logger().log_info(f"System health-query not fully OK yet. Failing checks: {failed}.")
            return False

        validate_equals_with_retry(
            function_to_execute=is_system_health_all_ok,
            expected_value=True,
            validation_description="System health-query reports all checks OK",
            timeout=timeout,
            polling_sleep_time=polling_sleep_time,
        )

    def validate_pods_health(self, namespace: str | None = None) -> bool:
        """Function to validate the health of all pods in the cluster

        Args:
           namespace (str | None): Namespace to check the pods in. If None, the default namespace will be used.

        Returns:
            bool: True if pod is in expected status else False.
        """
        healthy_status = ["Running", "Succeeded", "Completed"]
        return KubectlGetPodsKeywords(self.ssh_connection).wait_for_pods_to_reach_status(expected_status=healthy_status, namespace=namespace, timeout=300)

    def validate_no_alarms(self):
        """Function to validate no alarms are present in the cluster"""
        AlarmListKeywords(self.ssh_connection).wait_for_all_alarms_cleared()

    def validate_apps_health_and_applied(self):
        """Function to validate all apps are healthy and applied.

        Validates that every application currently listed is in a healthy status. On systems with a
        ceph storage backend configured, also waits for platform-integ-apps to be present and
        'applied'. This closes a post-deploy race where the health check could pass before
        platform-integ-apps has been uploaded and applied (it is applied asynchronously after the
        rest of the platform settles).
        """
        healthy_status = ["applied", "uploaded"]
        app_list_keywords = SystemApplicationListKeywords(self.ssh_connection)
        app_list_keywords.validate_all_apps_status(healthy_status)

        if self._is_platform_integ_apps_expected():
            get_logger().log_info(f"Storage backend configured; waiting for {PLATFORM_INTEG_APPS_NAME} to reach 'applied'")

            # platform-integ-apps is applied asynchronously after the platform settles and may not be
            # present yet, so wait for it to appear and reach 'applied' rather than reading it once.
            def get_platform_integ_apps_status() -> str:
                if not app_list_keywords.is_app_present(PLATFORM_INTEG_APPS_NAME):
                    return "not-present"
                return app_list_keywords.get_system_application_list().get_application(PLATFORM_INTEG_APPS_NAME).get_status()

            validate_equals_with_retry(
                function_to_execute=get_platform_integ_apps_status,
                expected_value="applied",
                validation_description=f"Application {PLATFORM_INTEG_APPS_NAME} is applied",
                timeout=1800,
                polling_sleep_time=15,
                failure_values=["apply-failed", "upload-failed"],
            )
        else:
            get_logger().log_info(f"No storage backend requiring {PLATFORM_INTEG_APPS_NAME} is configured; skipping its check")

    def _is_platform_integ_apps_expected(self) -> bool:
        """Determine whether platform-integ-apps should be present on this system.

        platform-integ-apps is pulled in by the ceph storage backend. On systems with no ceph backend
        (e.g. no storage), the application legitimately never appears and must not be waited on.

        Returns:
            bool: True if the ceph storage backend is configured; False otherwise.
        """
        storage_backends = SystemStorageBackendKeywords(self.ssh_connection).get_system_storage_backend_list()
        return storage_backends.is_backend_configured(CEPH_STORAGE_BACKEND)

    def validate_hosts_health(self, timeout: int = 1800, polling_sleep_time: int = 30):
        """Function to validate all hosts are deployed and healthy.

        Waits for every host to reach availability 'available', administrative 'unlocked', and
        operational 'enabled'. On a fresh deploy a second controller may still be coming up, so this
        polls rather than checking once. This must run before the pod health check so pods are only
        evaluated after their hosts are ready.

        Args:
            timeout (int): Maximum time in seconds to wait for each host attribute. Defaults to 1800.
            polling_sleep_time (int): Seconds between polls. Defaults to 30.
        """
        host_names = [host.get_host_name() for host in SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_hosts()]

        for host_name in host_names:
            validate_equals_with_retry(
                function_to_execute=lambda hn=host_name: SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(hn).get_availability(),
                expected_value="available",
                validation_description=f"Host {host_name} availability is available",
                timeout=timeout,
                polling_sleep_time=polling_sleep_time,
            )
            validate_equals_with_retry(
                function_to_execute=lambda hn=host_name: SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(hn).get_administrative(),
                expected_value="unlocked",
                validation_description=f"Host {host_name} administrative is unlocked",
                timeout=timeout,
                polling_sleep_time=polling_sleep_time,
            )
            validate_equals_with_retry(
                function_to_execute=lambda hn=host_name: SystemHostListKeywords(self.ssh_connection).get_system_host_list().get_host(hn).get_operational(),
                expected_value="enabled",
                validation_description=f"Host {host_name} operational is enabled",
                timeout=timeout,
                polling_sleep_time=polling_sleep_time,
            )
