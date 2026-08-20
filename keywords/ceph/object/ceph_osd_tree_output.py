import re

from framework.exceptions.keyword_exception import KeywordException
from keywords.ceph.object.ceph_osd_tree_object import CephOsdTreeObject


class CephOsdTreeOutput:
    """Parses the output of the 'ceph osd tree' command.

    Example:
        ID   CLASS  WEIGHT   TYPE NAME          STATUS  REWEIGHT  PRI-AFF
         -1         2.18359  root default
         -5         1.09180      host storage-0
          0    hdd  0.54590          osd.0          up   1.00000  1.00000
          2    hdd  0.54590          osd.2          up   1.00000  1.00000
         -3         1.09180      host storage-1
          1    hdd  0.54590          osd.1        down   1.00000  1.00000

    Only 'osd.<id>' rows are captured as objects. The host each OSD belongs to
    is tracked from the preceding 'host <name>' row.
    """

    def __init__(self, ceph_osd_tree_output: list[str]):
        """Constructor.

        Args:
            ceph_osd_tree_output (list[str]): The raw lines returned by 'ceph osd tree'.
        """
        self.ceph_osds: list[CephOsdTreeObject] = []

        current_host = None
        for line in ceph_osd_tree_output:
            tokens = line.split()
            if not tokens:
                continue

            # Track the current host context from 'host <name>' rows.
            # Match lines like: "-5  1.09180  host storage-0"
            # The TYPE column contains "host" followed by the hostname.
            if len(tokens) >= 4 and tokens[-2] == "host":
                current_host = tokens[-1]
                continue

            # OSD rows have a token matching 'osd.<id>'.
            osd_name = next((token for token in tokens if re.fullmatch(r"osd\.\d+", token)), None)
            if osd_name is None:
                continue

            osd_object = CephOsdTreeObject()
            osd_object.set_osd_id(int(osd_name.split(".")[1]))
            osd_object.set_name(osd_name)
            osd_object.set_host(current_host)

            # The status token ('up' or 'down') follows the name token.
            name_index = tokens.index(osd_name)
            if name_index + 1 < len(tokens):
                osd_object.set_status(tokens[name_index + 1])

            self.ceph_osds.append(osd_object)

    def get_ceph_osds(self) -> list[CephOsdTreeObject]:
        """Get all parsed OSD objects.

        Returns:
            list[CephOsdTreeObject]: Every OSD row in the tree.
        """
        return self.ceph_osds

    def get_osd_by_id(self, osd_id: int) -> CephOsdTreeObject:
        """Get the OSD object with the given id.

        Args:
            osd_id (int): The OSD id to look up.

        Returns:
            CephOsdTreeObject: The matching OSD object.

        Raises:
            KeywordException: If no OSD with the given id exists.
        """
        for osd in self.ceph_osds:
            if osd.get_osd_id() == osd_id:
                return osd
        raise KeywordException(f"No OSD with id {osd_id} was found in the ceph osd tree.")

    def get_osds_for_host(self, host: str) -> list[CephOsdTreeObject]:
        """Get all OSD objects belonging to a host.

        Args:
            host (str): The host name (e.g. 'storage-0').

        Returns:
            list[CephOsdTreeObject]: OSD objects on that host.
        """
        return [osd for osd in self.ceph_osds if osd.get_host() == host]

    def is_osd_up(self, osd_id: int) -> bool:
        """Check whether the OSD with the given id is up.

        Args:
            osd_id (int): The OSD id to check.

        Returns:
            bool: True if the OSD is up, False otherwise.
        """
        return self.get_osd_by_id(osd_id).is_up()

    def are_all_osds_up_for_host(self, host: str) -> bool:
        """Check whether every OSD on a host is up.

        Args:
            host (str): The host name.

        Returns:
            bool: True if all OSDs on the host are up, False otherwise.
        """
        host_osds = self.get_osds_for_host(host)
        return len(host_osds) > 0 and all(osd.is_up() for osd in host_osds)

    def are_all_osds_down_for_host(self, host: str) -> bool:
        """Check whether every OSD on a host is down.

        Args:
            host (str): The host name.

        Returns:
            bool: True if all OSDs on the host are down, False otherwise.
        """
        host_osds = self.get_osds_for_host(host)
        return len(host_osds) > 0 and all(not osd.is_up() for osd in host_osds)
