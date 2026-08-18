from framework.database.operations.upgrade_event_operation import UpgradeEventOperation
from framework.logging.automation_logger import get_logger
from framework.runner.objects.run_context_manager import RunContextManager
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.upgrade.objects.upgrade_event import UpgradeEvent


class RecordUpgradeEventKeywords(BaseKeyword):
    """
    Keywords for recording upgrade events.
    """

    def record_upgrade_event(self, event: UpgradeEvent) -> None:
        """
        Record upgrade event.

        Upgrade events are keyed on the session, which the caller of the run supplies. A run
        that was not given a session has nothing to attach the event to, so the event is
        dropped rather than recorded against a placeholder.

        Args:
            event (UpgradeEvent): the upgrade event

        """
        session_id = RunContextManager.get_session_id()
        if not session_id:
            get_logger().log_error(f"This run has no session id, so the upgrade event {event.get_event_name()} was not recorded.")
            return

        UpgradeEventOperation().create_upgrade_event(event, session_id)
