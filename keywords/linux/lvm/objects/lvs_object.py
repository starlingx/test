"""Module for the LvsObject that represents a logical volume from 'lvs' output."""


class LvsObject:
    """
    This class represents a Logical Volume as an object.

    This is typically a line in the 'lvs' command output.
    """

    def __init__(self, lv_name: str):
        """
        Initialize the LvsObject.

        Args:
            lv_name (str): the logical volume name.
        """
        self.lv_name: str = lv_name
        self.vg_name: str = None
        self.attr: str = None
        self.lsize: str = None
        self.pool: str = None
        self.origin: str = None
        self.data_percent: float = None
        self.meta_percent: float = None

    def get_lv_name(self) -> str:
        """
        Getter for the logical volume name.

        Returns:
            str: the logical volume name.
        """
        return self.lv_name

    def set_vg_name(self, vg_name: str):
        """
        Setter for the volume group name.

        Args:
            vg_name (str): the volume group name.

        Returns: None
        """
        self.vg_name = vg_name

    def get_vg_name(self) -> str:
        """
        Getter for the volume group name.

        Returns:
            str: the volume group name.
        """
        return self.vg_name

    def set_attr(self, attr: str):
        """
        Setter for the LV attributes.

        Args:
            attr (str): the LV attributes (e.g. 'twi-aotz--').

        Returns: None
        """
        self.attr = attr

    def get_attr(self) -> str:
        """
        Getter for the LV attributes.

        Returns:
            str: the LV attributes (e.g. 'twi-aotz--').
        """
        return self.attr

    def get_volume_type(self) -> str:
        """
        Get the volume type of the LV.

        This is the first character of the LV attribute string, as reported by 'lvs'.
        Common values: 't' (thin pool), 'V' (thin volume), '-' (linear/thick volume).

        Returns:
            str: the volume type character, or an empty string if the attribute is not set.
        """
        return self.attr[0] if self.attr else ""

    def is_thin_pool(self) -> bool:
        """
        Whether this logical volume is a thin pool.

        A thin pool has an LV attribute (volume type, first character) of 't'.

        Returns:
            bool: True if the LV is a thin pool, False otherwise.
        """
        return self.get_volume_type() == "t"

    def is_thin_volume(self) -> bool:
        """
        Whether this logical volume is a thin volume (provisioned from a thin pool).

        A thin volume has an LV attribute (volume type, first character) of 'V'.

        Returns:
            bool: True if the LV is a thin volume, False otherwise.
        """
        return self.get_volume_type() == "V"

    def is_linear(self) -> bool:
        """
        Whether this logical volume is a linear (thick) volume.

        A linear volume has an LV attribute (volume type, first character) of '-'.

        Returns:
            bool: True if the LV is a linear/thick volume, False otherwise.
        """
        return self.get_volume_type() == "-"

    def set_lsize(self, lsize: str):
        """
        Setter for the LV size.

        Args:
            lsize (str): the LV size (e.g. '111.00g').

        Returns: None
        """
        self.lsize = lsize

    def get_lsize(self) -> str:
        """
        Getter for the LV size.

        Returns:
            str: the LV size (e.g. '111.00g').
        """
        return self.lsize

    def set_pool(self, pool: str):
        """
        Setter for the pool this LV belongs to.

        Args:
            pool (str): the pool name.

        Returns: None
        """
        self.pool = pool

    def get_pool(self) -> str:
        """
        Getter for the pool this LV belongs to.

        Returns:
            str: the pool name.
        """
        return self.pool

    def set_origin(self, origin: str):
        """
        Setter for the origin of the LV.

        Args:
            origin (str): the origin.

        Returns: None
        """
        self.origin = origin

    def get_origin(self) -> str:
        """
        Getter for the origin of the LV.

        Returns:
            str: the origin.
        """
        return self.origin

    def set_data_percent(self, data_percent: float):
        """
        Setter for the data usage percentage.

        Args:
            data_percent (float): the data usage percentage.

        Returns: None
        """
        self.data_percent = data_percent

    def get_data_percent(self) -> float:
        """
        Getter for the data usage percentage.

        Returns:
            float: the data usage percentage.
        """
        return self.data_percent

    def set_meta_percent(self, meta_percent: float):
        """
        Setter for the metadata usage percentage.

        Args:
            meta_percent (float): the metadata usage percentage.

        Returns: None
        """
        self.meta_percent = meta_percent

    def get_meta_percent(self) -> float:
        """
        Getter for the metadata usage percentage.

        Returns:
            float: the metadata usage percentage.
        """
        return self.meta_percent
