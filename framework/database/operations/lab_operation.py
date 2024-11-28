from framework.database.connection.database_operation_manager import DatabaseOperationManager
from framework.logging.automation_logger import get_logger


class LabOperation:
    """
    Lab Operation class
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def does_lab_exist(self, lab_name: str) -> bool:
        """
        Returns true if a lab with the given name exists
        Args:
            lab_name (): the name of the lab

        Returns: True if it exists, False otherwise

        """
        get_lab_id_query = f"SELECT lab_info_id FROM lab_info where lab_name='{lab_name}'"
        result = self.database_operation_manager.execute_query(get_lab_id_query)

        return len(result) > 0

    def insert_lab(self, lab_name: str):
        """
        Insert lab into database
        Args:
            lab_name (): the lab name

        Returns:

        """
        if not self.does_lab_exist(lab_name):  # Only add the lab if it doesn't exist.

            create_lab_query = f"INSERT INTO lab_info (lab_name) VALUES ('{lab_name}') RETURNING lab_info_id"
            result = self.database_operation_manager.execute_query(create_lab_query)
            return result[0][0]
        else:
            get_logger().log_error(f"WARNING: This lab is already in the database! Lab Name: {lab_name}")
            return -1

    def get_lab_id(self, lab_name):
        """
        This function will transform the lab_name passed in into the equivalent lab id.
        Args:
            lab_name (str): is the name of the lab.
        Returns: The id associated with the lab.
        """
        # Get the lab id from the database.
        get_lab_id_query = f"SELECT lab_info_id FROM lab_info where lab_name='{lab_name}'"

        result = self.database_operation_manager.execute_query(get_lab_id_query)
        if result:
            if len(result) > 1:
                get_logger().log_info(f"WARNING: We have found more than one result matching the Lab Name: {lab_name}")
            return result[0][0]  # First Row, First Entry
        else:
            get_logger().log_error(f"ERROR: No lab with the name {lab_name} exists.")
            return -1
