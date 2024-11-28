from framework.database.connection.database_operation_manager import DatabaseOperationManager
from framework.database.objects.capability import Capability
from framework.logging.automation_logger import get_logger
from psycopg2.extras import RealDictCursor


class TestCapabilityOperation:
    """
    This class allows you to perform test capability database operations
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def get_id(self, capability_id: int, test_info_id: int) -> int:
        """
        This function will transform the capability id and test_info_id passed in into the
        equivalent capability test id.
        Args:
            capability_id (int): is the id of the capability
            test_info_id (int): is the id of the test

        Returns: The id associated with the capability.
        """
        # Get the test id from the database.
        get_capability_test_id_query = "SELECT capability_test_id FROM capability_test where " f"capability_id='{capability_id}' and test_info_id='{test_info_id}'"

        result = self.database_operation_manager.execute_query(get_capability_test_id_query)
        if result:
            if len(result) > 1:
                get_logger().log_error(f"WARNING: We have found more than one result matching the Capability Name:" f" {capability_id} and {test_info_id}")
            return result[0][0]  # First Row, First Entry
        else:
            return -1

    def create_new_mapping(self, capability_id: int, test_info_id: int) -> int:
        """
        This function will add a new entry to the database for a capability with the name specified.
        Args:
            capability_id (int): The id of the capability
            test_info_id (str): the id of the test

        Returns: The id of the newly created mapping
        """

        create_capability_mapping_query = "INSERT INTO capability_test " "(capability_id, test_info_id) " f"VALUES ({capability_id}, {test_info_id}) " "RETURNING capability_test_id"
        result = self.database_operation_manager.execute_query(create_capability_mapping_query, cursor_factory=RealDictCursor)
        return result[0]['capability_test_id']

    def get_capabilities_for_test(self, test_info_id) -> [Capability]:
        """
        Gets the capabilities in the db for this test
        Args:
            test_info_id: the id of the test

        Returns: a list of marker names

        """

        get_capabilities_query = f"Select * FROM capability_test " "join capability using (capability_id) " f"where test_info_id={test_info_id}"

        results = self.database_operation_manager.execute_query(get_capabilities_query, cursor_factory=RealDictCursor)

        capabilities_list = []

        if results:
            for result in results:
                capability = Capability(result['capability_id'], result['capability_name'], result['capability_marker'])
                capabilities_list.append(capability)
        return capabilities_list

    def delete_capability_test(self, capability_id: int, test_info_id: int):
        """
        Deletes a required capability mapping
        Args:
            capability_id: the capability id
            test_info_id: the test info id

        Returns:

        """

        mapping_id = self.get_id(capability_id, test_info_id)
        if mapping_id == -1:
            get_logger().log_error(f"Unable to find a mapping with " f"required capability id = {capability_id} or test_id = {test_info_id}")
            return -1

        delete_capabilities_query = f"Delete FROM capability_test where capability_test_id={mapping_id}"

        self.database_operation_manager.execute_query(delete_capabilities_query, expect_results=False)
