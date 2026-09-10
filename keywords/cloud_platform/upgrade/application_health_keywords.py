from config.configuration_manager import ConfigurationManager
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


class ApplicationHealthKeywords(BaseKeyword):
    """
    This class contains keywords for checking the health of a platform application.

    The checks are the ones a platform upgrade needs and that the plain status getters do not
    cover: waiting for 'applied' with a budget long enough for a post-activate re-apply, reading
    the status without failing when it is not 'applied', counting pods in a namespace, and
    counting the alarms that indicate a real application or deploy problem as opposed to the ones
    a deploy raises by design.
    """

    # The unhealthy-pod read is retried through KubectlGetPodsKeywords.get_pods_with_retry. These
    # are the window it uses: immediately after 'software deploy activate' the platform re-applies
    # its own applications and the query can fail transiently, but a cluster that cannot list pods
    # for a minute is a real problem worth reporting rather than waiting out.
    POD_READ_TIMEOUT = 60
    POD_READ_POLL_INTERVAL = 10

    def __init__(self, ssh_connection: SSHConnection):
        """
        Instance of the class.

        Args:
            ssh_connection(SSHConnection): An instance of an SSH connection.

        """
        self.ssh_connection = ssh_connection
        self.app_show = SystemApplicationShowKeywords(ssh_connection)
        self.app_apply = SystemApplicationApplyKeywords(ssh_connection)
        self.pods = KubectlGetPodsKeywords(ssh_connection)
        self.alarms = AlarmListKeywords(ssh_connection)

    def is_app_applied(self, app_name: str) -> bool:
        """
        Return True when the application currently reports the 'applied' status.

        Delegates to SystemApplicationApplyKeywords.is_already_applied, which is the canonical
        single-read applied check; kept here so a teardown holding an ApplicationHealthKeywords does
        not have to construct a second keyword for one question.

        Args:
            app_name(str): the platform application name.

        Returns:
            bool: True when the application reports status 'applied'.

        """
        return self.app_apply.is_already_applied(app_name)

    def get_app_version(self, app_name: str) -> str:
        """
        Return the version the platform reports for an application.

        A single call, because reaching this through the show output requires chaining three getters
        and a test case that asserts the version at baseline, after upgrade and after rollback would
        otherwise repeat that chain three times.

        Args:
            app_name(str): the platform application name.

        Returns:
            str: the application version, for example "26.10-71".

        """
        show = self.app_show.get_system_application_show(app_name)
        return show.get_system_application_object().get_version()

    def wait_for_app_applied(self, app_name: str, timeout: int = None) -> None:
        """
        Wait for an application to reach 'applied', allowing for a post-activate auto-update.

        Delegates to SystemApplicationApplyKeywords.wait_for_applied, which is where the
        application-apply waiting logic lives; kept here so the per-app upgrade test bodies read as
        health.wait_for_app_applied alongside the other health checks they perform.

        Args:
            app_name(str): the platform application name.
            timeout(int): seconds to wait; defaults to the USM config's application applied
                timeout.

        """
        self.app_apply.wait_for_applied(app_name, timeout=timeout)

    def get_pod_count(self, namespace: str) -> int:
        """
        Count all pods in a namespace.

        Args:
            namespace(str): the namespace to count pods in.

        Returns:
            int: the number of pods in the namespace.

        """
        return len(self.pods.get_pods(namespace=namespace).get_pods())

    def get_unhealthy_pod_count(self, namespace: str) -> int:
        """
        Count the pods in a namespace that are not healthy.

        get_unhealthy_pods() takes no namespace argument, so its objects are filtered by
        namespace here.

        The read itself is retried by the k8s layer. It is a single kubectl query whose return code
        is asserted with no retry, and immediately after 'software deploy activate' the platform is
        re-applying its own applications: pods are being created and deleted, and the query has been
        observed to return non-zero in that window and then succeed unchanged moments later.
        Retrying distinguishes "the cluster was busy" from "this application is unhealthy", which is
        the question being asked.

        Args:
            namespace(str): the namespace to count unhealthy pods in.

        Returns:
            int: the number of unhealthy pods in the namespace.

        Raises:
            KeywordException: when the pod list cannot be read within the retry window.

        """
        unhealthy = self.pods.get_pods_with_retry(
            self.pods.get_unhealthy_pods,
            timeout=self.POD_READ_TIMEOUT,
            poll_interval=self.POD_READ_POLL_INTERVAL,
        ).get_pods()
        return len([pod for pod in unhealthy if pod.get_namespace() == namespace])

    def get_app_or_deploy_alarm_count(self) -> int:
        """
        Count active application and deploy alarms that are not expected during a deploy.

        The prefixes are the ones seen in upgrade and rollback defect scenarios:
          750. application apply and remove failures, for example 750.003 Application Remove Failure
          900. software and deploy, for example 900.021 host deploy or rollback failed
          250. configuration out of date, 250.001, which blocks deploy prechecks

        Alarms that are expected while a deploy is open are excluded, otherwise this count
        false-fails on a healthy upgrade: a post-upgrade check runs before 'deploy complete' and
        'deploy delete', so the deploy-in-progress alarms are still raised. The exclusion list
        comes from the USM config rather than being hardcoded here, so it stays consistent with
        the rest of the framework. 250.001 is also excluded because it is normal immediately
        after a host unlock, which is how is_host_unlocked already treats it.

        Returns:
            int: the number of alarms that indicate a real application or deploy problem.

        """
        prefixes = ("250.", "750.", "900.")
        ignored = list(ConfigurationManager.get_usm_config().get_cleanup_ignore_alarms())
        ignored.append("250.001")
        remaining = self.alarms.get_alarm_list().get_alarms_excluding(ignored)
        return len([alarm for alarm in remaining if str(alarm.get_alarm_id()).startswith(prefixes)])
