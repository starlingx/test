"""Module for parsing 'system host-lvg-show' output into a SystemHostLvgObject."""

import ast

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_lvg_object import SystemHostLvgObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemHostLvgShowOutput:
    """This class parses the output of 'system host-lvg-show' command into an object of type SystemHostLvgObject."""

    def __init__(self, system_output: str):
        """
        Initialize the SystemHostLvgShowOutput by parsing the command output.

        Args:
            system_output (str): Output of the 'system host-lvg-show' command.

        Raises:
            KeywordException: If the output is not valid.
        """
        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_host_lvg = SystemHostLvgObject()
            self.system_host_lvg.set_uuid(output_values["uuid"])
            self.system_host_lvg.set_lvg_name(output_values["lvm_vg_name"])
            self.system_host_lvg.set_state(output_values["vg_state"])
            self.system_host_lvg.set_ihost_uuid(output_values["ihost_uuid"])
            self.system_host_lvg.set_access(output_values["lvm_vg_access"])
            # lvm_function/lvm_type/lvm_pool_size are only populated for certain VGs (e.g. the
            # lvm-csi path) and may be absent on older builds or non-lvm-csi VGs. Read them
            # optionally so those cases still parse; the getters return None when absent.
            self.system_host_lvg.set_lvm_function(output_values.get("lvm_function"))
            self.system_host_lvg.set_lvm_type(output_values.get("lvm_type"))
            self.system_host_lvg.set_lvm_pool_size(output_values.get("lvm_pool_size"))
            self.system_host_lvg.set_lvm_max_lv(output_values["lvm_max_lv"])
            self.system_host_lvg.set_current_lvs(output_values["lvm_cur_lv"])
            self.system_host_lvg.set_lvm_max_pv(output_values["lvm_max_pv"])
            self.system_host_lvg.set_current_pvs(output_values["lvm_cur_pv"])
            self.system_host_lvg.set_total_size(output_values["lvm_vg_size_gib"])
            self.system_host_lvg.set_avail_size(output_values["lvm_vg_avail_size_gib"])
            self.system_host_lvg.set_lvm_vg_total_pe(output_values["lvm_vg_total_pe"])
            self.system_host_lvg.set_lvm_vg_free_pe(output_values["lvm_vg_free_pe"])
            self.system_host_lvg.set_created_at(output_values["created_at"])
            self.system_host_lvg.set_updated_at(output_values["updated_at"])
            self.system_host_lvg.set_parameters(self._parse_parameters(output_values.get("parameters")))
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    @staticmethod
    def _parse_parameters(raw_parameters: str) -> dict:
        """
        Parse the 'parameters' field of 'system host-lvg-show' into a dict.

        The CLI reports this column as a Python-dict-like string (e.g. "{'thin_cur_lv': 1}").
        An empty/None value maps to an empty dict. An unparseable non-empty value is surfaced
        as an error rather than being silently swallowed, since downstream logic depends on it.

        Args:
            raw_parameters (str): The raw 'parameters' value from the CLI output.

        Returns:
            dict: The parsed parameters mapping.

        Raises:
            KeywordException: If the value is present but cannot be parsed into a dict.
        """
        if isinstance(raw_parameters, dict):
            return raw_parameters
        if raw_parameters is None or str(raw_parameters).strip() in ("", "None"):
            return {}
        try:
            parsed = ast.literal_eval(str(raw_parameters))
        except (ValueError, SyntaxError) as parse_error:
            raise KeywordException(f"Could not parse host-lvg 'parameters' value {raw_parameters!r}: {parse_error}")
        if not isinstance(parsed, dict):
            raise KeywordException(f"host-lvg 'parameters' did not parse to a dict: {raw_parameters!r}")
        return parsed

    def get_system_host_lvg(self) -> SystemHostLvgObject:
        """
        Return the parsed system host-lvg object.

        Returns:
            SystemHostLvgObject: The parsed system host-lvg object.
        """
        return self.system_host_lvg

    @staticmethod
    def is_valid_output(value: dict) -> bool:
        """
        Check if the output contains all the expected fields.

        Args:
            value (dict): The dictionary of output values.

        Returns:
            bool: True if the output contains all required fields, False otherwise.
        """
        # lvm_function, lvm_type, lvm_pool_size and parameters are intentionally NOT required:
        # they are only populated for certain VGs (e.g. the lvm-csi path) and may be absent on
        # older builds or non-lvm-csi VGs. They are read optionally in __init__ so those outputs
        # still parse and the corresponding getters return None/{} when absent.
        required_fields = ["lvm_vg_name", "vg_state", "uuid", "ihost_uuid", "lvm_vg_access", "lvm_max_lv", "lvm_cur_lv", "lvm_max_pv", "lvm_cur_pv", "lvm_vg_size_gib", "lvm_vg_avail_size_gib", "lvm_vg_total_pe", "lvm_vg_free_pe", "created_at", "updated_at"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                valid = False
                break
        return valid
