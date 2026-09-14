"""Unit tests for ApplicationHealthKeywords.

Cover the application health checks without a lab: that the applied status is read without
failing when it is not applied, that the applied wait uses the configured budget rather than the
300s default, that pod counts are scoped to a namespace, and that the alarm count excludes the
alarms a deploy raises by design while still counting the ones that indicate a real problem.
"""
import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_output import AlarmListOutput
from keywords.cloud_platform.upgrade.application_health_keywords import ApplicationHealthKeywords


class TestApplicationHealthKeywords(unittest.TestCase):
    """Test suite for the application health checks used by platform upgrade tests."""

    APP_APPLIED_TIMEOUT = 2400
    IGNORED_ALARMS = ["900.020", "900.022", "900.023"]

    def setUp(self):
        """Silence the BaseKeyword logger."""
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.logger_patcher.start()

    def tearDown(self):
        """Stop the logger patcher."""
        self.logger_patcher.stop()

    def _build_keywords(self, status="applied", pods=(), unhealthy=(), alarm_ids=(), version="26.03-69"):
        """Return an instance whose collaborators are mocked.

        BaseKeyword.__getattribute__ wraps every callable attribute in a logging wrapper, so
        collaborators are installed with object.__setattr__ and built from NonCallableMagicMock to
        keep that wrapper from replacing them.

        Args:
            status (str): status reported by 'system application-show'.
            version (str): version reported by 'system application-show'.
            pods (tuple): namespaces of the pods returned for a namespace query.
            unhealthy (tuple): namespaces of the unhealthy pods returned.
            alarm_ids (tuple): alarm IDs reported by 'fm alarm-list'.

        Returns:
            ApplicationHealthKeywords: the instance under test.
        """
        keywords = ApplicationHealthKeywords.__new__(ApplicationHealthKeywords)

        app_object = NonCallableMagicMock()
        app_object.get_status = MagicMock(return_value=status)
        app_object.get_version = MagicMock(return_value=version)
        show_output = NonCallableMagicMock()
        show_output.get_system_application_object = MagicMock(return_value=app_object)
        app_show = NonCallableMagicMock()
        app_show.get_system_application_show = MagicMock(return_value=show_output)

        pods_kw = NonCallableMagicMock()
        pods_kw.get_pods = MagicMock(return_value=self._pods_output(pods))
        pods_kw.get_unhealthy_pods = MagicMock(return_value=self._pods_output(unhealthy))
        # get_unhealthy_pod_count delegates the retry to the k8s layer; here it passes straight
        # through to the reader so the count and namespace scoping are what is under test. The
        # retry itself is covered by the KubectlGetPodsKeywords tests.
        pods_kw.get_pods_with_retry = MagicMock(
            side_effect=lambda reader, timeout=None, poll_interval=None: reader()
        )

        alarms = NonCallableMagicMock()
        alarms.get_alarm_list = MagicMock(return_value=self._alarm_list_output(alarm_ids))

        object.__setattr__(keywords, "ssh_connection", NonCallableMagicMock())
        object.__setattr__(keywords, "app_show", app_show)
        object.__setattr__(keywords, "app_apply", NonCallableMagicMock())
        object.__setattr__(keywords, "pods", pods_kw)
        object.__setattr__(keywords, "alarms", alarms)
        return keywords

    @staticmethod
    def _pods_output(namespaces):
        """Return a mocked pods output whose pods report the given namespaces.

        Args:
            namespaces (tuple): one namespace per pod.

        Returns:
            NonCallableMagicMock: stands in for KubectlGetPodsOutput.
        """
        pod_objects = []
        for namespace in namespaces:
            pod = NonCallableMagicMock()
            pod.get_namespace = MagicMock(return_value=namespace)
            pod_objects.append(pod)
        output = NonCallableMagicMock()
        output.get_pods = MagicMock(return_value=pod_objects)
        return output

    @staticmethod
    def _alarms(alarm_ids):
        """Return mocked alarm objects reporting the given IDs.

        Args:
            alarm_ids (tuple): alarm IDs.

        Returns:
            list: mocked AlarmListObject instances.
        """
        alarms = []
        for alarm_id in alarm_ids:
            alarm = NonCallableMagicMock()
            alarm.get_alarm_id = MagicMock(return_value=alarm_id)
            alarms.append(alarm)
        return alarms

    @classmethod
    def _alarm_list_output(cls, alarm_ids):
        """Return an alarm list output that performs the real exclusion filtering.

        A mock that simply returns a canned list would let the production code stop excluding
        anything and still pass, since the filtering it delegates would never run. Using the real
        AlarmListOutput.get_alarms_excluding keeps the exclusion under test at the call site.

        Args:
            alarm_ids (tuple): alarm IDs reported by 'fm alarm-list'.

        Returns:
            NonCallableMagicMock: stands in for AlarmListOutput, filtering as the real one does.
        """
        alarms = cls._alarms(alarm_ids)
        output = NonCallableMagicMock()
        output.alarms = alarms
        output.get_alarms = MagicMock(return_value=alarms)
        output.get_alarms_excluding = MagicMock(
            side_effect=lambda excluded=None: AlarmListOutput.get_alarms_excluding(output, excluded)
        )
        return output

    def _patch_usm_config(self):
        """Patch the USM config the keywords read, returning the patcher's mock.

        Returns:
            tuple: (patcher, usm_config mock)
        """
        patcher = patch("keywords.cloud_platform.upgrade.application_health_keywords.ConfigurationManager")
        manager = patcher.start()
        usm_config = NonCallableMagicMock()
        usm_config.get_app_applied_timeout_sec = MagicMock(return_value=self.APP_APPLIED_TIMEOUT)
        usm_config.get_cleanup_ignore_alarms = MagicMock(return_value=list(self.IGNORED_ALARMS))
        manager.get_usm_config = MagicMock(return_value=usm_config)
        self.addCleanup(patcher.stop)
        return usm_config

    def test_is_app_applied_delegates_to_the_apply_keyword(self):
        """is_app_applied forwards to SystemApplicationApplyKeywords.is_already_applied.

        That is the canonical single-read applied check; this keyword only re-exposes it so a
        teardown holding the health keyword need not build a second one. Asserting the delegation
        keeps the duplicate from creeping back.
        """
        keywords = self._build_keywords()
        keywords.app_apply.is_already_applied = MagicMock(return_value=True)

        self.assertTrue(keywords.is_app_applied("portieris"))
        keywords.app_apply.is_already_applied.assert_called_once_with("portieris")

    def test_wait_for_app_applied_delegates_to_the_apply_keyword(self):
        """wait_for_app_applied forwards to SystemApplicationApplyKeywords.wait_for_applied.

        The applied-wait logic lives on the apply keyword; the health keyword re-exposes it only so
        the per-app upgrade test bodies read as health.wait_for_app_applied. The timeout is passed
        through unchanged.
        """
        keywords = self._build_keywords()
        keywords.app_apply.wait_for_applied = MagicMock()

        keywords.wait_for_app_applied("portieris", timeout=60)

        keywords.app_apply.wait_for_applied.assert_called_once_with("portieris", timeout=60)

    def test_pod_count_counts_pods_in_namespace(self):
        """The pod count is the number of pods the namespace query returns."""
        keywords = self._build_keywords(pods=("portieris", "portieris", "portieris"))

        self.assertEqual(keywords.get_pod_count("portieris"), 3)

    def test_unhealthy_pod_count_is_scoped_to_the_namespace(self):
        """Unhealthy pods in other namespaces are not counted."""
        keywords = self._build_keywords(unhealthy=("portieris", "kube-system", "portieris"))

        self.assertEqual(keywords.get_unhealthy_pod_count("portieris"), 2)

    def test_alarm_count_ignores_expected_deploy_alarms(self):
        """Alarms a deploy raises by design are excluded, so a healthy upgrade counts zero."""
        self._patch_usm_config()
        keywords = self._build_keywords(alarm_ids=("900.020", "900.022", "900.023", "250.001"))

        self.assertEqual(keywords.get_app_or_deploy_alarm_count(), 0)

    def test_alarm_count_counts_real_application_and_deploy_alarms(self):
        """Application-failure and deploy-failure alarms are counted."""
        self._patch_usm_config()
        keywords = self._build_keywords(alarm_ids=("750.003", "900.021", "900.020"))

        self.assertEqual(keywords.get_app_or_deploy_alarm_count(), 2)

    def test_alarm_count_ignores_unrelated_alarms(self):
        """Alarms outside the application and deploy prefixes are not counted."""
        self._patch_usm_config()
        keywords = self._build_keywords(alarm_ids=("100.104", "200.001", "800.001"))

        self.assertEqual(keywords.get_app_or_deploy_alarm_count(), 0)

    def test_app_version_reads_the_reported_version(self):
        """The application version is read in one call, so a test case need not chain getters.

        Without this a test case has to write
        app_show.get_system_application_show(name).get_system_application_object().get_version(),
        three times over, which is not something a non-technical reader can follow.
        """
        keywords = self._build_keywords(version="26.10-71")

        self.assertEqual(keywords.get_app_version("cert-manager"), "26.10-71")

    def test_unhealthy_pod_count_delegates_the_read_to_the_retrying_k8s_keyword(self):
        """The count is taken from get_pods_with_retry, so the transient-failure retry applies.

        The retry behaviour itself is covered by the KubectlGetPodsKeywords tests. This asserts
        only that the count goes through that retrying read rather than a bare get_unhealthy_pods,
        so the retry cannot be bypassed here without a test noticing.
        """
        keywords = self._build_keywords(unhealthy=("portieris",))

        count = keywords.get_unhealthy_pod_count("portieris")

        self.assertEqual(count, 1)
        keywords.pods.get_pods_with_retry.assert_called_once()
        self.assertIs(keywords.pods.get_pods_with_retry.call_args[0][0], keywords.pods.get_unhealthy_pods)

    def test_healthy_namespace_still_reads_zero(self):
        """A successful read of no unhealthy pods returns zero."""
        keywords = self._build_keywords(unhealthy=())

        self.assertEqual(keywords.get_unhealthy_pod_count("portieris"), 0)


if __name__ == "__main__":
    unittest.main()
