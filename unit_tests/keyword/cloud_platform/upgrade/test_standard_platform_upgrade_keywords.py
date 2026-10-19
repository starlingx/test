"""Unit tests for StandardPlatformUpgradeKeywords.

These drivers exist because the shared deploy_upgrade/deploy_rollback use the upgrade host order for
both directions, which the platform rejects on a Standard lab rollback ("does not satisfy the right
order of deployment"). The tests cover the two things that are easy to get wrong and cost a hardware
debugging cycle: the rollback host order (workers/storage first, then controllers by NAME, stable
across the active/standby role swap) and that a standby-ready wait precedes each controller swact.
Collaborators are mocked.
"""

import unittest
from unittest.mock import MagicMock, NonCallableMagicMock, patch

from keywords.cloud_platform.upgrade.standard_platform_upgrade_keywords import StandardPlatformUpgradeKeywords


class TestStandardPlatformUpgradeKeywords(unittest.TestCase):
    """Test suite for the standard-lab upgrade/rollback sequence drivers."""

    def setUp(self):
        """Silence the BaseKeyword and module loggers."""
        self.logger_patcher = patch("keywords.base_keyword.get_logger")
        self.logger_patcher.start()
        self.module_logger_patcher = patch("keywords.cloud_platform.upgrade.standard_platform_upgrade_keywords.get_logger")
        self.module_logger_patcher.start()

    def tearDown(self):
        """Stop the logger patchers."""
        self.logger_patcher.stop()
        self.module_logger_patcher.stop()

    def _build_keywords(self):
        """Return an instance with the swact and alarms collaborators mocked.

        BaseKeyword.__getattribute__ wraps every callable attribute in a logging wrapper, so
        collaborators are installed with object.__setattr__ and built from NonCallableMagicMock.
        """
        keywords = StandardPlatformUpgradeKeywords.__new__(StandardPlatformUpgradeKeywords)
        object.__setattr__(keywords, "ssh_connection", NonCallableMagicMock())
        swact = NonCallableMagicMock()
        swact.wait_for_standby_available = MagicMock()
        object.__setattr__(keywords, "swact", swact)
        alarms = NonCallableMagicMock()
        alarms.alarm_list = MagicMock(return_value=[])  # no blocking alarms by default
        object.__setattr__(keywords, "alarms", alarms)
        return keywords

    @staticmethod
    def _named_host(name):
        """Return a mock host object reporting the given hostname."""
        host = NonCallableMagicMock()
        host.get_host_name = MagicMock(return_value=name)
        return host

    def _deploy_with_roles(self, computes, storages, active, standby):
        """Return a mock deploy whose USM role/host-list helpers report the given live roles."""
        deploy = NonCallableMagicMock()
        deploy.usm.computes_host_upgrade_list = MagicMock(return_value=[self._named_host(n) for n in computes])
        deploy.usm.storage_host_upgrade_list = MagicMock(return_value=[self._named_host(n) for n in storages])
        deploy.usm.active_controller_host_upgrade = MagicMock(return_value=self._named_host(active))
        deploy.usm.standby_controller_host_upgrade = MagicMock(return_value=self._named_host(standby) if standby else None)
        return deploy

    def test_resume_uses_the_rollback_order_and_only_remaining_stages(self):
        """Resume known states without re-aborting or applying upgrade host order."""
        for state in ("deploy-activate-rollback-pending", "deploy-activate-rollback-done", "deploy-host-rollback-done", "deploy-host-rollback-failed"):
            with self.subTest(state=state):
                keywords = self._build_keywords()
                deploy = self._deploy_with_roles(computes=["compute-1", "compute-0"], storages=[], active="controller-1", standby="controller-0")
                deploy.get_current_deploy_state.return_value = state
                keywords.resume_rollback_in_order(deploy)
                deploy.usm.software_deploy_abort.assert_not_called()
                if state == "deploy-activate-rollback-pending":
                    deploy.usm.software_deploy_activate_rollback.assert_called_once_with(sudo=False)
                else:
                    deploy.usm.software_deploy_activate_rollback.assert_not_called()
                if state in ("deploy-activate-rollback-pending", "deploy-activate-rollback-done"):
                    self.assertEqual([call.args[0] for call in deploy.deploy_host_guarded.call_args_list], ["compute-0", "compute-1", "controller-0", "controller-1"])
                    self.assertEqual(keywords.swact.wait_for_standby_available.call_count, 2)
                else:
                    deploy.deploy_host_guarded.assert_not_called()
                    keywords.swact.wait_for_standby_available.assert_not_called()
                if state == "deploy-host-rollback-failed":
                    deploy.usm.software_deploy_delete.assert_not_called()
                else:
                    deploy.usm.software_deploy_delete.assert_called_once_with(sudo=False)

    def test_rollback_rolls_controllers_back_in_name_order_after_role_swap(self):
        """Rollback rolls workers first, then controllers by NAME (controller-0 before controller-1)."""
        keywords = self._build_keywords()
        # Live roles at rollback time: controller-1 active (was standby at upgrade), controller-0 standby.
        deploy = self._deploy_with_roles(computes=["compute-1", "compute-0"], storages=[], active="controller-1", standby="controller-0")

        keywords.rollback_platform_in_order(deploy)

        rolled_order = [call.args[0] for call in deploy.deploy_host_guarded.call_args_list]
        self.assertEqual(rolled_order, ["compute-0", "compute-1", "controller-0", "controller-1"])
        for call in deploy.deploy_host_guarded.call_args_list:
            self.assertTrue(call.kwargs.get("rollback"))

    def test_rollback_host_order_orders_controllers_by_name(self):
        """_rollback_host_order: workers+storage (sorted), then controllers sorted by name."""
        keywords = self._build_keywords()
        deploy = self._deploy_with_roles(computes=["compute-1", "compute-0"], storages=["storage-1", "storage-0"], active="controller-0", standby="controller-1")

        order = keywords._rollback_host_order(deploy)

        self.assertEqual(order, ["compute-0", "compute-1", "storage-0", "storage-1", "controller-0", "controller-1"])

    def test_rollback_host_order_controllers_by_name_when_active_is_controller_1(self):
        """Controllers are name-ordered even when the active controller is controller-1."""
        keywords = self._build_keywords()
        deploy = self._deploy_with_roles(computes=["compute-0"], storages=[], active="controller-1", standby="controller-0")

        order = keywords._rollback_host_order(deploy)

        self.assertEqual(order, ["compute-0", "controller-0", "controller-1"])

    def test_rollback_runs_abort_activate_rollback_then_delete(self):
        """The rollback issues abort, activate-rollback and delete around the per-host steps."""
        keywords = self._build_keywords()
        deploy = self._deploy_with_roles(computes=["compute-0"], storages=[], active="controller-0", standby="controller-1")

        keywords.rollback_platform_in_order(deploy)

        deploy.usm.software_deploy_abort.assert_called_once()
        deploy.usm.software_deploy_activate_rollback.assert_called_once()
        deploy.usm.software_deploy_delete.assert_called_once()
        self.assertTrue(deploy.deploy_host_guarded.called)

    def test_upgrade_in_order_waits_for_standby_before_controller(self):
        """upgrade_platform_in_order waits for the standby before each controller's guarded deploy."""
        keywords = self._build_keywords()
        calls = []
        # Record each standby-ready wait and each guarded deploy in call order.
        keywords.swact.wait_for_standby_available = MagicMock(side_effect=lambda *a, **k: calls.append("wait"))
        deploy = NonCallableMagicMock()
        deploy.get_release_id_for_version = MagicMock(return_value="STX-10.0")
        deploy.usm.deploy_host_upgrade_order = MagicMock(return_value=["controller-1", "controller-0", "compute-0", "compute-1"])

        def record_guard(host, rollback=False):
            calls.append(host)

        deploy.deploy_host_guarded = MagicMock(side_effect=record_guard)

        keywords.upgrade_platform_in_order(deploy, "10.0", leave_at_activate_done=True)

        self.assertEqual(
            calls,
            ["wait", "controller-1", "wait", "controller-0", "compute-0", "compute-1"],
        )
        deploy.usm.software_deploy_activate.assert_called_once()
        deploy.usm.software_deploy_complete.assert_not_called()  # left at activate-done

    def test_require_no_blocking_alarms_raises_when_alarm_active(self):
        """require_no_blocking_alarms names the active alarms and raises."""
        from framework.exceptions.keyword_exception import KeywordException

        keywords = self._build_keywords()
        alarm = NonCallableMagicMock()
        alarm.get_alarm_id = MagicMock(return_value="250.001")
        alarm.get_entity_id = MagicMock(return_value="host=controller-0")
        keywords.alarms.alarm_list = MagicMock(return_value=[alarm])

        with self.assertRaises(KeywordException):
            keywords.require_no_blocking_alarms()

    def test_require_no_blocking_alarms_passes_when_clear(self):
        """require_no_blocking_alarms returns when there are no active alarms."""
        keywords = self._build_keywords()
        keywords.alarms.alarm_list = MagicMock(return_value=[])

        keywords.require_no_blocking_alarms()  # must not raise


if __name__ == "__main__":
    unittest.main()
