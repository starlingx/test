import re

from framework.logging.automation_logger import get_logger
from keywords.ceph.object.ceph_status_cluster_output import CephClusterOutput
from keywords.ceph.object.ceph_status_data_output import CephDataOutput
from keywords.ceph.object.ceph_status_io_output import CephIOOutput
from keywords.ceph.object.ceph_status_services_output import CephServicesOutput


class CephStatusOutput:
    """
    This class parses the output of command ceph -s

    Example:
          cluster:
            id:     8abb43ce-6775-4a1a-99c4-12f37101410e
            health: HEALTH_OK

          services:
            mon: 3 daemons, quorum a,b,c (age 3w)
            mgr: b(active, since 24h), standbys: c, a
            mds: 1/1 daemons up, 1 hot standby
            osd: 5 osds: 5 up (since 2w), 5 in (since 2w)

          data:
            volumes: 1/1 healthy
            pools:   4 pools, 112 pgs
            objects: 26 objects, 6.6 MiB
            usage:   401 MiB used, 2.2 TiB / 2.2 TiB avail
            pgs:     112 active+clean

          io:
            client:   1.2 KiB/s rd, 2 op/s rd, 0 op/s wr


    """

    def __init__(self, ceph_s_output: list[str]):
        """
        Create a list of ceph objects for the given output

        Args:
            ceph_s_output (list[str]): a list of strings representing the output of the ceph -s command

        """
        self.ceph_cluster_output: CephClusterOutput = None
        self.ceph_services_output: CephServicesOutput = None
        self.ceph_data_output: CephDataOutput = None
        self.ceph_io_output: CephIOOutput = None

        section_name_list = ["cluster:", "services:", "data:", "io:"]
        section_object = ""
        body_str = []
        for line in ceph_s_output:
            # remove front extra space of a line
            line = line.lstrip()
            # skip empty lines
            if line.strip() == "":
                continue
            # get section name
            elif any(section in line for section in section_name_list):
                # We have completed a section content, now create it.
                if section_object:
                    self.create_section_object(section_object, body_str)
                # We are starting a new section.
                # remove : and \n
                section_object = line.replace(":", "").replace("\n", "")
                body_str = []
            else:
                # This line is part of the current section
                # remove end '\n'
                line = line.rstrip("\n")
                body_str.append(line)

        # Create the last section
        self.create_section_object(section_object, body_str)

    def create_section_object(self, section_object: str, body_str: list[str]):
        """
        Creates the ceph section object

        Args:
            section_object (str): the object to be created
            body_str (list[str]): the body of the section

        """
        if "cluster" in section_object:
            self.ceph_cluster_output = CephClusterOutput(body_str)

        if "services" in section_object:
            self.ceph_services_output = CephServicesOutput(body_str)

        if "data" in section_object:
            self.ceph_data_output = CephDataOutput(body_str)

        if "io" in section_object:
            self.ceph_io_output = CephIOOutput(body_str)

    def get_ceph_cluster_output(self) -> CephClusterOutput:
        """
        Getter for the ceph cluster output

        Returns:
            CephClusterOutput: a CephClusterOutput object

        """
        return self.ceph_cluster_output

    def get_ceph_services_output(self) -> CephServicesOutput:
        """
        Getter for the services output

        Returns:
            CephServicesOutput: a CephServicesOutput object

        """
        return self.ceph_services_output

    def get_ceph_data_output(self) -> CephDataOutput:
        """
        Getter for the data output

        Returns:
            CephDataOutput: a CephDataOutput object

        """
        return self.ceph_data_output

    def get_ceph_io_output(self) -> CephIOOutput:
        """
        Getter for the io output

        Returns:
            CephIOOutput: a CephIOOutput object

        """
        return self.ceph_io_output

    def is_ceph_healthy(self) -> bool:
        """
        Check whether ceph is healthy

        If the 'ceph -s' output has no parseable health status (e.g. "The rook toolbox
        is not running." during recovery), ceph is treated as NOT healthy (returns False)
        instead of raising, so polling callers keep retrying.

        Args: None

        Returns:
            bool:
            If ceph health is ok, return True
            If ceph health is not ok, or the health status could not be determined, return False

        """
        # The cluster section may be missing when 'ceph -s' did not return a parseable
        # status (e.g. "The rook toolbox is not running."). Treat that as not healthy.
        if self.ceph_cluster_output is None or self.ceph_cluster_output.get_ceph_cluster_object() is None:
            get_logger().log_info("Ceph cluster status is not available yet (ceph -s returned no parseable status). Treating ceph as not healthy.")
            return False

        ceph_health_status_msg = self.ceph_cluster_output.get_ceph_cluster_object().get_health()
        if not ceph_health_status_msg:
            get_logger().log_info("Ceph health status is empty (ceph -s returned no health line). Treating ceph as not healthy.")
            return False

        if "HEALTH_OK" in ceph_health_status_msg:
            return True
        elif "HEALTH_WARN" in ceph_health_status_msg or "HEALTH_ERR" in ceph_health_status_msg:
            return False
        else:
            raise ValueError(f"Ceph health status msg should contain HEALTH_OK, HEALTH_WARN or HEALTH_ERR. Got: {ceph_health_status_msg}")

    def get_ceph_osd_count(self) -> int:
        """
        Get osd number

        Args: None

        Returns (int):
            osd_number

        """
        osd_msg = self.ceph_services_output.get_ceph_services_object().get_osd()
        match = re.search(r"\d+", osd_msg)
        osd_number = int(match.group())
        return osd_number

    def get_ceph_mon_count(self) -> int:
        """
        Get mons number

        Args: None

        Returns (int):
            mons_number

        """
        mons_msg = self.ceph_services_output.get_ceph_services_object().get_mon()
        match = re.search(r"\d+", mons_msg)
        mons_number = int(match.group())
        return mons_number
