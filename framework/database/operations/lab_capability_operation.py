from framework.database.connection.database_operation_manager import DatabaseOperationManager
from framework.database.objects.capability import Capability
from framework.database.objects.lab_capability import LabCapability
from psycopg2.extras import RealDictCursor


class LabCapabilityOperation:
    """
    Class for Lab capability operations
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def insert_lab_capability(self, lab_capability: LabCapability):
        """
        Inserts the given lab capability
        Args:
            lab_capability (): the lab capability

        Returns:

        """

        insert_query = f"INSERT INTO capability_lab (lab_info_id, capability_id) " f"VALUES ({lab_capability.get_lab_info_id()},{lab_capability.get_capability_id()})"
        self.database_operation_manager.execute_query(insert_query, expect_results=False)

    def delete_all_lab_capabilities(self, lab_info_id):
        """
        Deletes all lab capabilities for the given lab_info_id
        Args:
            lab_info_id (): the lab info id

        Returns:

        """

        delete_query = f"DELETE FROM capability_lab WHERE lab_info_id={lab_info_id}"

        self.database_operation_manager.execute_query(delete_query, expect_results=False)

    def get_lab_capabilities(self, lab_info_id: int) -> [Capability]:
        """
        Returns a list of capabilities for a given lab
        Args:
            lab_info_id (): the lab info id

        Returns:

        """
        query = "SELECT * from capability_lab " "JOIN capability using (capability_id) " f"WHERE lab_info_id={lab_info_id}"
        capabilities = []
        results = self.database_operation_manager.execute_query(query, RealDictCursor)
        for result in results:
            capability = Capability(result['capability_id'], result['capability_name'], result['capability_marker'])
            capabilities.append(capability)

        return capabilities
