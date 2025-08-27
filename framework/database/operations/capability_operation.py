from psycopg2.extras import RealDictCursor

from framework.database.connection.database_operation_manager import DatabaseOperationManager
from framework.database.objects.capability import Capability
from framework.logging.automation_logger import get_logger


class CapabilityOperation:
    """
    Class for capability operations
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def insert_capability(self, capability_name: str, capability_marker: str) -> Capability:
        """
        Inserts into the database a new capability with capability_name and capability_marker passed in.

        Args:
            capability_name (str): the name of the new capability
            capability_marker (str): the marker associated with the new capability

        Returns:
            Capability: A Capability object with the capability_id generated from the database.
        """
        insert_query = f"INSERT INTO capability (capability_name, capability_marker) " f"VALUES ('{capability_name}', '{capability_marker}') " f"returning capability_id"

        results = self.database_operation_manager.execute_query(insert_query, cursor_factory=RealDictCursor)
        if results:  # can only ever be 1 result
            capability = Capability(results[0]["capability_id"], capability_name, capability_marker)
            return capability

        raise ValueError("Unable to insert the capability and get a capability_id.")

    def get_capability_by_marker(self, capability_marker: str) -> Capability:
        """
        Getter for capability given a capability name

        Args:
            capability_marker (str): The marker used to identify the capability.

        Returns:
            Capability: The capability object if found, -1 if no capability is found.
        """
        get_capability_query = f"SELECT * FROM capability where capability_marker='{capability_marker}'"
        results = self.database_operation_manager.execute_query(get_capability_query, cursor_factory=RealDictCursor)

        if results:
            if len(results) > 1:
                get_logger().log_info(f"WARNING: We have found more than one result matching the Capability Name: {capability_marker}")
            result = results[0]
            capability = Capability(result["capability_id"], result["capability_name"], result["capability_marker"])

            return capability
        else:
            get_logger().log_warning(f"There is no capability with the name {capability_marker}")
            return -1
