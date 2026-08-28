from typing import Optional


class Kpi:
    """
    Class for a KPI catalog entry.

    Describes a KPI in the kpi catalog table. A KPI is uniquely identified by
    the combination of product, category, name, node role, and detail.
    """

    def __init__(
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
    ):
        """
        Constructor for Kpi.

        Args:
            product (str): Product name (e.g. 'WRCP').
            kpi_category (str): Category (e.g. 'PLATFORM', 'MTC').
            kpi_name (str): KPI name (e.g. 'shutdown-phase').
            kpi_node_role (str): Node role (e.g. 'controller-0').
            kpi_detail (str): Detail/stat (e.g. 'duration', 'avg', 'max').
            kpi_group (str): Group (e.g. 'lock_unlock', 'cyclictest').
            kpi_unit (Optional[str]): Unit of measurement (e.g. 's', 'ns', '%').
            kpi_owner_team (Optional[str]): Owning team name.
            kpi_description (Optional[str]): Description of the KPI.
        """
        self.product = product
        self.kpi_category = kpi_category
        self.kpi_name = kpi_name
        self.kpi_node_role = kpi_node_role
        self.kpi_detail = kpi_detail
        self.kpi_group = kpi_group
        self.kpi_unit = kpi_unit
        self.kpi_owner_team = kpi_owner_team
        self.kpi_description = kpi_description

    def get_product(self) -> str:
        """Getter for product.

        Returns:
            str: The product name.
        """
        return self.product

    def get_kpi_category(self) -> str:
        """Getter for KPI category.

        Returns:
            str: The KPI category.
        """
        return self.kpi_category

    def get_kpi_name(self) -> str:
        """Getter for KPI name.

        Returns:
            str: The KPI name.
        """
        return self.kpi_name

    def get_kpi_node_role(self) -> str:
        """Getter for KPI node role.

        Returns:
            str: The node role.
        """
        return self.kpi_node_role

    def get_kpi_detail(self) -> str:
        """Getter for KPI detail.

        Returns:
            str: The KPI detail/stat.
        """
        return self.kpi_detail

    def get_kpi_group(self) -> str:
        """Getter for KPI group.

        Returns:
            str: The KPI group.
        """
        return self.kpi_group

    def get_kpi_unit(self) -> Optional[str]:
        """Getter for KPI unit.

        Returns:
            Optional[str]: The unit of measurement.
        """
        return self.kpi_unit

    def get_kpi_owner_team(self) -> Optional[str]:
        """Getter for KPI owner team.

        Returns:
            Optional[str]: The owning team name.
        """
        return self.kpi_owner_team

    def get_kpi_description(self) -> Optional[str]:
        """Getter for KPI description.

        Returns:
            Optional[str]: The KPI description.
        """
        return self.kpi_description
