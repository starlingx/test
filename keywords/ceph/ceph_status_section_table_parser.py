import re

from framework.exceptions.keyword_exception import KeywordException


class CephStatusSectionTableParser:
    """
    Class for ceph -s section table parsing

    Example:
        ["health: HEALTH_WARN",
         "2 MDSs report slow metadata IOs",
         "Reduced data availability: 48 pgs inactive",
         "Degraded data redundancy: 66/196 objects degraded (33.673%), 11 pgs degraded, 48 pgs undersized"]

         OR

        ["mon: 3 daemons, quorum a,b,c (age 2w)",
         "mgr: b(active, since 46s), standbys: c, a",
         "mds: 1/1 daemons up, 1 hot standby",
         "osd: 5 osds: 5 up (since 2w), 5 in (since 2w)"]
    """

    def __init__(self, ceph_status_section_output: list[str]):
        """
        Constructor

        Args:
            ceph_status_section_output (list[str]): a list of strings representing one section output of 'ceph -s' command
        """
        self.ceph_status_section_output = ceph_status_section_output

    def get_output_values_dict(self) -> {}:
        """
        Getter for output values dict

        Returns:
            {}: the output values dict

        """
        output_values_dict = {}
        for row in self.ceph_status_section_output:
            # Only health section has extra lines
            if "health" in output_values_dict:
                output_values_dict["health"] += "; " + row
                continue
            # splits the string at the first colon followed by any amount of whitespace.
            values = re.split(r":\s*", row, maxsplit=1)
            if len(values) == 2:
                key, value = values
                output_values_dict[key] = value
            else:
                # just a newline -- continue
                if not values or len(values) == 1:
                    continue
                else:
                    raise KeywordException(f"Line with values: {row} was not in the expected format")

        return output_values_dict
