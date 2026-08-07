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

    def create_standalone_run(
        self,
        run_name: str,
        product: str,
        run_type_id: int,
        build_info_id: int,
        platform_build_info_id: int,
    ) -> int:
        """
        Creates a standalone run (without requiring a test plan).

        Args:
            run_name: Descriptive name for the run.
            product: Product name (e.g. 'WRCP').
            run_type_id: Run type ID.
            build_info_id: Build info ID for the software build.
            platform_build_info_id: Platform build info ID.

        Returns:
            int: The run_id.

        Raises:
            ValueError: If unable to insert the run.
        """
        insert_query = (
            "INSERT INTO run ("
            "run_name, run_type_id, product, build_info_id, platform_build_info_id"
            ") VALUES ("
            f"'{run_name}', {run_type_id}, '{product}', "
            f"{build_info_id}, {platform_build_info_id}"
            ") RETURNING run_id"
        )

        results = self.database_operation_manager.execute_query(insert_query)

        if results:
            return results[0][0]

        raise ValueError("Unable to insert standalone run.")
