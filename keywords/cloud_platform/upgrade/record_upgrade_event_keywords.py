from datetime import datetime

from framework.database.objects.test_case_result import TestCaseResult
from framework.database.operations.test_case_result_operation import TestCaseResultOperation
from framework.database.operations.upgrade_event_operation import UpgradeEventOperation
from framework.runner.objects.RunResultsManager import RunResultsManager
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.upgrade.objects.upgrade_event import UpgradeEvent


class RecordUpgradeEventKeywords(BaseKeyword):
    """
    Keywords for recording upgrade events.
    """

    def record_upgrade_event(self, event: UpgradeEvent):
        """
        Record upgrade event.

        Args:
            event (UpgradeEvent): the upgrade event

        """
        test_case_result_id = RunResultsManager.get_test_case_result_id()
        if not test_case_result_id:
            test_case_result = TestCaseResult(-1, "NOT_RUN", datetime.now(), datetime.now())
            test_case_result_id = TestCaseResultOperation().create_test_case_result(test_case_result)

        UpgradeEventOperation().create_upgrade_event(event, test_case_result_id)

        # update the singleton with the test result id so we don't create another one
        if test_case_result_id:
            RunResultsManager.set_test_case_result_id(test_case_result_id)
