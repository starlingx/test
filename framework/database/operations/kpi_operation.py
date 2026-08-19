from typing import Optional

from framework.database.connection.database_operation_manager import DatabaseOperationManager


class KpiOperation:
    """
    Database operations for the kpi catalog table.
    """

    def __init__(self):
        self.database_operation_manager = DatabaseOperationManager()

    def get_or_create_kpi(
        self,
        product: str,
        kpi_category: str,
        kpi_name: str,
        kpi_node_role: str,
        kpi_detail: str,
        kpi_group: str,
        kpi_unit: Optional[str] = None,
        kpi_owner_team: Optional[str] = None,
        kpi_description: Optional[str] = None,
    ) -> int:
        """
        Get an existing KPI by its unique attributes, or create it if it doesn't exist.

        Args:
            product: Product name (e.g. 'WRCP').
            kpi_category: Category (e.g. 'MTC', 'DC').
            kpi_name: KPI name (e.g. 'cyclictest_latency').
            kpi_node_role: Node role (e.g. 'controller-0').
            kpi_detail: Detail/stat (e.g. 'avg', 'max', 'p99_9999').
            kpi_group: Group (e.g. 'cyclictest', 'swact').
            kpi_unit: Unit of measurement (e.g. 'ns', 's', '%').
            kpi_owner_team: Owning team name.
            kpi_description: Description of the KPI.

        Returns:
            int: The kpi_id.

        Raises:
            ValueError: If unable to find or create the KPI.
        """
        # Try to find existing KPI
        select_query = (
            "SELECT kpi_id FROM kpi "
            f"WHERE product = '{product}' "
            f"AND kpi_category = '{kpi_category}' "
            f"AND kpi_name = '{kpi_name}' "
            f"AND kpi_node_role = '{kpi_node_role}' "
            f"AND kpi_detail = '{kpi_detail}' "
            "LIMIT 1"
        )

        results = self.database_operation_manager.execute_query(select_query)

        if results:
            return results[0][0]

        # KPI not found — create it
        kpi_unit_val = f"'{kpi_unit}'" if kpi_unit is not None else "NULL"
        kpi_owner_val = f"'{kpi_owner_team}'" if kpi_owner_team is not None else "NULL"
        kpi_desc_val = f"'{kpi_description}'" if kpi_description is not None else "NULL"

        insert_query = (
            "INSERT INTO kpi ("
            "product, kpi_category, kpi_name, "
            "kpi_node_role, kpi_detail, kpi_group, kpi_unit, "
            "kpi_owner_team, kpi_description"
            ") VALUES ("
            f"'{product}', '{kpi_category}', '{kpi_name}', "
            f"'{kpi_node_role}', '{kpi_detail}', '{kpi_group}', {kpi_unit_val}, "
            f"{kpi_owner_val}, {kpi_desc_val}"
            ") RETURNING kpi_id"
        )

        results = self.database_operation_manager.execute_query(insert_query)

        if results:
            return results[0][0]

        raise ValueError("Unable to get or create KPI.")
