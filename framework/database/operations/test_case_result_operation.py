from framework.database.connection.database_operation_manager import DatabaseOperationManager
from framework.database.objects.test_case_result import TestCaseResult


class TestCaseResultOperation:
    """
    TestCase Result Operation
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def create_test_case_result(self, test_case_result: TestCaseResult):
        """
        Creates a test case result in the database

        Args:
            test_case_result (TestCaseResult): the test case result

        """
        # fmt: off
        create_test_case_result = (
            "INSERT INTO test_case_result (test_info_id, execution_result, start_time, end_time, test_run_execution_id, log_hostname, log_location) "
            f"VALUES ({test_case_result.test_info_id}, '{test_case_result.execution_result}', '{test_case_result.start_time}', "
            f"'{test_case_result.end_time}', {test_case_result.test_run_execution_id}, '{test_case_result.log_hostname}', '{test_case_result.log_location}')"
        )

        self.database_operation_manager.execute_query(create_test_case_result, expect_results=False)

    def update_test_case_result(self, test_case_result: TestCaseResult):
        """
        Updates a test case result in the database

        Args:
            test_case_result (TestCaseResult): the testcase result

        """
        # fmt: off
        create_test_case_result = (
            "UPDATE test_case_result "
            f"SET execution_result='{test_case_result.get_execution_result()}', "
            f"log_hostname='{test_case_result.log_hostname}', "
            f"log_location='{test_case_result.log_location}', "
            f"start_time='{test_case_result.start_time}', "
            f"end_time='{test_case_result.end_time}' "
            f"WHERE test_case_result_id={test_case_result.get_test_case_result_id()}"
        )

        self.database_operation_manager.execute_query(create_test_case_result, expect_results=False)
