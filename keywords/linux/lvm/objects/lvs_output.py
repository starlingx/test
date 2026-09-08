"""Module for parsing 'lvs' command output into LvsObject instances."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.linux.lvm.objects.lvs_object import LvsObject


class LvsOutput:
    """
    This class parses the output of the 'lvs' command into a list of LvsObject.

    The parser expects the stable, whitespace-separated output produced by:
        lvs --noheadings --separator '|' -o lv_name,vg_name,lv_attr,lv_size,pool_lv,origin,data_percent,metadata_percent

    Using an explicit separator and column list avoids the alignment issues of
    the default 'lvs' table (variable padding, right-aligned numeric columns).
    """

    # The order of fields requested via the 'lvs -o' option below.
    _FIELDS = ["lv_name", "vg_name", "lv_attr", "lv_size", "pool_lv", "origin", "data_percent", "metadata_percent"]

    def __init__(self, lvs_output: str | list, separator: str = "|"):
        """
        Initialize the LvsOutput by parsing the 'lvs' command output.

        Args:
            lvs_output (str | list): String or list of strings output of the 'lvs' command.
            separator (str): the field separator passed to 'lvs --separator'.
        """
        self.logical_volumes: list[LvsObject] = []

        lines = lvs_output if isinstance(lvs_output, list) else lvs_output.splitlines()

        for line in lines:
            line = line.strip()
            # Skip empty lines and shell prompt echoes.
            if not line or separator not in line:
                continue

            values = [value.strip() for value in line.split(separator)]
            if len(values) < len(self._FIELDS):
                continue

            row = dict(zip(self._FIELDS, values))

            lvs_object = LvsObject(row["lv_name"])
            lvs_object.set_vg_name(row["vg_name"])
            lvs_object.set_attr(row["lv_attr"])
            lvs_object.set_lsize(row["lv_size"])
            lvs_object.set_pool(row["pool_lv"])
            lvs_object.set_origin(row["origin"])
            lvs_object.set_data_percent(self._to_float(row["data_percent"]))
            lvs_object.set_meta_percent(self._to_float(row["metadata_percent"]))

            self.logical_volumes.append(lvs_object)

    @staticmethod
    def _to_float(value: str) -> float:
        """
        Convert a percentage string to float, defaulting to 0.0 when empty.

        Args:
            value (str): the string value (e.g. '80.33' or '').

        Returns:
            float: the parsed value, or 0.0 if the string is empty/invalid.
        """
        if not value:
            return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0

    def get_logical_volumes(self) -> list[LvsObject]:
        """
        Return the list of logical volumes parsed from the 'lvs' output.

        Returns:
            list[LvsObject]: list of logical volume objects.
        """
        return self.logical_volumes

    def get_logical_volume(self, lv_name: str) -> LvsObject:
        """
        Get the logical volume with the given name.

        Args:
            lv_name (str): the name of the logical volume.

        Raises:
            KeywordException: if no logical volume with the given name exists.

        Returns:
            LvsObject: the logical volume object.
        """
        volumes = list(filter(lambda item: item.get_lv_name() == lv_name, self.logical_volumes))
        if len(volumes) == 0:
            raise KeywordException(f"No logical volume with name {lv_name} was found.")
        return volumes[0]

    def is_logical_volume_present(self, lv_name: str) -> bool:
        """
        Verify whether a logical volume with the given name exists.

        Args:
            lv_name (str): the name of the logical volume.

        Returns:
            bool: True if the logical volume exists, False otherwise.
        """
        return any(item.get_lv_name() == lv_name for item in self.logical_volumes)
