from time import sleep

import psycopg2.extras
from framework.database.connection.database_connection_manager import DatabaseConnectionManager
from framework.logging.automation_logger import get_logger


class DatabaseOperationManager:
    """
    This class allows you to perform database operations
    """

    def __init__(self):
        self.database_connection_manager = DatabaseConnectionManager()

    def execute_query(self, query, cursor_factory=None, expect_results=True):
        """
        This function will open up a connection to the database and execute the
        specified query.
        Args:
            query: The query that we want to execute.
            cursor_factory: set to RealDictCursor to allow for selecting name columns
            expect_results: set to false if nothing is returned by the query ex. updates
        Returns: The result of the query if any.
        """

        # Loop until we get something or the error is not an DNS error
        while True:
            try:
                with self.database_connection_manager.open_conn_and_get_cur(cursor_factory=cursor_factory) as cursor:
                    cursor.execute(query)
                    if expect_results:
                        rows = cursor.fetchall()
                        return rows
                    else:
                        return None
            except Exception as e:
                get_logger().log_error(f"Failed to execute query: {query}")
                get_logger().log_error(e)
                if not str(e).__contains__('Name or service not known'):
                    # if not an operational error we just log and move on
                    return None
                else:
                    get_logger().log_error('DNS error: sleeping for 60 secs and will try again')
                    sleep(60)

    def execute_values(self, query, data):
        try:
            with self.database_connection_manager.open_conn_and_get_cur() as cursor:
                psycopg2.extras.execute_values(cursor, query, data, template=None)
        except Exception as e:
            get_logger().log_error(f"Failed to execute query: {query}")
            get_logger().log_error(e)
