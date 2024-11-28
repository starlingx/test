from framework.database.connection.database_operation_manager import DatabaseOperationManager
from framework.database.objects.test_plan import TestPlan
from framework.logging.automation_logger import get_logger
from psycopg2.extras import RealDictCursor


class TestPlanOperation:
    """
    Class for Test Plan Operations
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def get_test_plan(self, test_plan_id) -> TestPlan:
        """
        Gets the test plan with the given id
        Args:
            test_plan_id (): the test plan id

        Returns: a test plan object

        """

        query = f"SELECT * FROM test_plan WHERE test_plan_id={test_plan_id}"

        results = self.database_operation_manager.execute_query(query, cursor_factory=RealDictCursor)

        if results:
            if len(results) > 1:
                get_logger().log_info(f"WARNING: We have found more than one result matching the test plan id: {test_plan_id}")
            result = results[0]
            test_plan = TestPlan(result['test_plan_name'], result['description'], result['run_type_id'])
            test_plan.set_test_plan_id(result['test_plan_id'])
            test_plan.set_locked(result['locked'])

            return test_plan

        raise ValueError(f"There is no entry for test_plan_id={test_plan_id}")
