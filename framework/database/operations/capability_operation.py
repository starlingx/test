from framework.database.connection.database_operation_manager import DatabaseOperationManager
from framework.database.objects.capability import Capability
from framework.logging.automation_logger import get_logger
from psycopg2.extras import RealDictCursor


class CapabilityOperation:
    """
    Class for capability operations
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def get_capability_by_marker(self, capability_marker: str) -> Capability:
        """
        Getter for capability given a capability name
        Args:
            capability_marker (): the marker

        Returns: The capability

        """

        get_capability_query = f"SELECT * FROM capability where capability_marker='{capability_marker}'"
        results = self.database_operation_manager.execute_query(get_capability_query, cursor_factory=RealDictCursor)

        if results:
            if len(results) > 1:
                get_logger().log_info(f"WARNING: We have found more than one result matching the Capability Name: {capability_marker}")
            result = results[0]
            capability = Capability(result['capability_id'], result['capability_name'], result['capability_marker'])

            return capability
        else:
            get_logger().log_error(f"ERROR: no capability with the name {capability_marker}")
            return -1
