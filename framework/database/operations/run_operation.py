from framework.database.connection.database_operation_manager import DatabaseOperationManager
from psycopg2.extras import RealDictCursor


class RunOperation:
    """
    This class allows you to perform Run Database Operations
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def create_run(self, run_name: str, run_type_id: int, release: str) -> int:
        """
        Creates a run
        Args:
            run_name (): the name of the run
            run_type_id (): the run_type_id
            release (): the release

        Returns:

        """
        insert_query = "INSERT INTO run " "(run_name, run_type_id, release) " f"VALUES ('{run_name}',{run_type_id},'{release}') RETURNING run_id"

        results = self.database_operation_manager.execute_query(insert_query, cursor_factory=RealDictCursor)

        if results:
            return results[0]['run_id']  # can only ever be 1 result

        raise ValueError("Unable to insert the run and get a run id.")
