from framework.database.connection.database_operation_manager import DatabaseOperationManager
from framework.database.objects.testcase import TestCase
from framework.logging.automation_logger import get_logger
from psycopg2.extras import RealDictCursor


class TestInfoOperation:
    """
    This class allows you to perform test_info database operations
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def get_info_test_id(self, test_name, test_suite):
        """
        This function will transform the test_name passed in into the equivalent test id.
        The method will return None if test id does not exist
        Args:
            test_name (str): is the name of the test.
            test_suite (str): is the suite of the test.
        Returns: The id associated with the test.
        """
        # Get the test id from the database.
        get_test_id_query = f"SELECT test_info_id FROM test_info where test_name='{test_name}' and test_suite='{test_suite}'"

        result = self.database_operation_manager.execute_query(get_test_id_query, cursor_factory=RealDictCursor)
        if result:
            if len(result) > 1:
                get_logger().log_info(f"WARNING: We have found more than one result matching the Test Name: {test_name}")
            return result[0]['test_info_id']

        return None

    def get_test_info(self, test_info_id: str) -> TestCase:
        """
        Gets the TestInfo associated with the test_info_id specified.
        Args:
            test_info_id: The id of the TestInfo of interest.
        Returns: TestInfo
        """

        test_case_info_query = f"select * from test_info where test_info_id={test_info_id}"

        results = self.database_operation_manager.execute_query(test_case_info_query, RealDictCursor)

        if results:
            # This query returns at maximum one result.
            result = results[0]
            test_info = TestCase(result['test_name'], result['test_suite'], result['priority'], result['test_path'], result['pytest_node_id'])

            test_info.set_test_info_id(result['test_info_id'])
            test_info.set_test_case_group_id(result['test_case_group_id'])
            test_info.set_is_active(result['is_active'])

            return test_info
        else:
            raise ValueError(f"There is no entry for test_info_id={test_info_id}")

    def insert_test(self, testcase: TestCase):
        """
        Inserts the given testcase
        Args:
            testcase (): the testcase to insert

        Returns: the test info id

        """

        insert_query = (
            f"INSERT INTO test_info (test_name, test_suite, priority, test_path, pytest_node_id, test_case_group_id, is_active) "
            f"VALUES('{testcase.get_test_name()}', '{testcase.get_test_suite()}', '{testcase.get_priority()}', "
            f"'{testcase.get_test_path()}', '{testcase.get_pytest_node_id()}', {testcase.get_test_case_group_id()}, "
            f"{testcase.is_testcase_active()}) RETURNING test_info_id"
        )

        result = self.database_operation_manager.execute_query(insert_query, cursor_factory=RealDictCursor)

        if result:
            return result[0]['test_info_id']
        else:
            raise ValueError(f"Unable to insert testcase with name {testcase.get_test_name()}")

    def update_priority(self, test_info_id: int, priority: str):
        """
        Updates the priority of the test
        Args:
            test_info_id: the test id
            priority:  the priority

        Returns:

        """

        update_priority_query = f"update test_info set priority='{priority}' where test_info_id={test_info_id}"
        self.database_operation_manager.execute_query(update_priority_query, expect_results=False)

    def update_test_path(self, test_info_id: int, test_path: str):
        """
        Updates the test_path of this test case.
        Args:
            test_info_id: The test id
            test_path: The test_path
        """

        update_test_path_query = f"update test_info set test_path='{test_path}' where test_info_id={test_info_id}"
        self.database_operation_manager.execute_query(update_test_path_query, expect_results=False)

    def update_pytest_node_id(self, test_info_id: int, pytest_node_id: str):
        """
        Updates the pytest_node_id of this test case.
        Args:
            test_info_id: The test_info_id
            pytest_node_id: The pytest_node_id
        """

        update_pytest_node_id_query = f"update test_info set pytest_node_id='{pytest_node_id}' where test_info_id={test_info_id}"
        self.database_operation_manager.execute_query(update_pytest_node_id_query, expect_results=False)
