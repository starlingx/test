from psycopg2.extras import RealDictCursor

from framework.database.connection.database_operation_manager import DatabaseOperationManager
from framework.database.objects.upgrade_event import UpgradeEvent


class UpgradeEventOperation:
    """
    Upgrade Event Operation class
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def create_upgrade_event(self, upgrade_event: UpgradeEvent):
        """
        Creates an upgrade event in the database

        Args:
            upgrade_event (UpgradeEvent): The upgrade event to create
        """
        # fmt: off
        create_upgrade_event_query = (
            "INSERT INTO upgrade_event (test_case_result_id, event_name, retry, operation, entity, "
            "is_upgrade, is_patch, timestamp, is_rollback, duration, from_version, to_version, "
            "snapshot, subcloud, build_id) "
            f"VALUES ({upgrade_event.test_case_result_id}, '{upgrade_event.event_name}', "
            f"{upgrade_event.retry}, '{upgrade_event.operation}', '{upgrade_event.entity}', "
            f"{upgrade_event.is_upgrade}, {upgrade_event.is_patch}, '{upgrade_event.timestamp}', "
            f"{upgrade_event.is_rollback}, {upgrade_event.duration}, '{upgrade_event.from_version}', "
            f"'{upgrade_event.to_version}', {upgrade_event.snapshot}, '{upgrade_event.subcloud}', "
            f"'{upgrade_event.build_id}') RETURNING upgrade_event_id"
        )

        result = self.database_operation_manager.execute_query(create_upgrade_event_query)
        if result:
            upgrade_event.set_upgrade_event_id(result[0][0])

    def get_upgrade_events_by_test_case_result_id(self, test_case_result_id: int) -> list:
        """
        Gets upgrade events by test case result ID

        Args:
            test_case_result_id (int): The test case result ID

        Returns:
            list: List of UpgradeEvent objects
        """
        get_upgrade_events_query = "SELECT * FROM upgrade_event " f"WHERE test_case_result_id={test_case_result_id}"

        results = self.database_operation_manager.execute_query(get_upgrade_events_query, RealDictCursor)

        upgrade_events = []
        if results:
            for result in results:
                upgrade_event = UpgradeEvent(result["test_case_result_id"], result["event_name"], result["retry"], result["operation"], result["entity"], result["is_upgrade"], result["is_patch"])
                upgrade_event.set_upgrade_event_id(result["upgrade_event_id"])
                upgrade_event.timestamp = result["timestamp"]
                upgrade_event.is_rollback = result["is_rollback"]
                upgrade_event.duration = result["duration"]
                upgrade_event.from_version = result["from_version"]
                upgrade_event.to_version = result["to_version"]
                upgrade_event.snapshot = result["snapshot"]
                upgrade_event.subcloud = result["subcloud"]
                upgrade_event.build_id = result["build_id"]
                upgrade_events.append(upgrade_event)

        return upgrade_events

    def update_upgrade_event(self, upgrade_event: UpgradeEvent):
        """
        Updates an upgrade event in the database

        Args:
            upgrade_event (UpgradeEvent): The upgrade event to update
        """
        # fmt: off
        update_upgrade_event_query = (
            "UPDATE upgrade_event "
            f"SET event_name='{upgrade_event.event_name}', "
            f"retry={upgrade_event.retry}, "
            f"operation='{upgrade_event.operation}', "
            f"entity='{upgrade_event.entity}', "
            f"is_upgrade={upgrade_event.is_upgrade}, "
            f"is_patch={upgrade_event.is_patch}, "
            f"is_rollback={upgrade_event.is_rollback}, "
            f"duration={upgrade_event.duration}, "
            f"from_version='{upgrade_event.from_version}', "
            f"to_version='{upgrade_event.to_version}', "
            f"snapshot={upgrade_event.snapshot}, "
            f"subcloud='{upgrade_event.subcloud}', "
            f"build_id='{upgrade_event.build_id}' "
            f"WHERE upgrade_event_id={upgrade_event.get_upgrade_event_id()}"
        )

        self.database_operation_manager.execute_query(update_upgrade_event_query, expect_results=False)
