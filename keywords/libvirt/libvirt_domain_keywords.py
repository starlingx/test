import re

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.libvirt.object.libvirt_disk_iotune_object import LibvirtDiskIotuneObject


class LibvirtDomainKeywords(BaseKeyword):
    """Keywords for inspecting libvirt VM domains via 'virsh dumpxml'.

    Used by tests that need to verify hypervisor-level enforcement of disk I/O
    throttles (QoS specs and flavor extra specs). There is no OpenStack API
    that exposes what libvirt is actually applying, so host-level inspection
    is required.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the compute host
                where the VM is running.
        """
        self.ssh_connection = ssh_connection

    def get_disk_iotune(self, instance_name: str) -> LibvirtDiskIotuneObject:
        """Get the disk I/O throttle values from a VM's libvirt XML.

        Parses the <iotune> block from the first <disk> element in the
        virsh dumpxml output for the given instance.

        Args:
            instance_name (str): The libvirt instance name (e.g. 'instance-00000042').

        Returns:
            LibvirtDiskIotuneObject: Parsed I/O throttle values.
        """
        output = self.ssh_connection.send_as_sudo_non_interactive(f"virsh dumpxml {instance_name}")
        self.validate_success_return_code(self.ssh_connection)

        xml_text = "".join(output) if isinstance(output, list) else str(output)

        iotune = LibvirtDiskIotuneObject()

        fields = [
            ("read_bytes_sec", iotune.set_read_bytes_sec),
            ("write_bytes_sec", iotune.set_write_bytes_sec),
            ("total_bytes_sec", iotune.set_total_bytes_sec),
            ("read_iops_sec", iotune.set_read_iops_sec),
            ("write_iops_sec", iotune.set_write_iops_sec),
            ("total_iops_sec", iotune.set_total_iops_sec),
        ]

        for field_name, setter in fields:
            match = re.search(rf"<{field_name}>(\d+)</{field_name}>", xml_text)
            if match:
                setter(int(match.group(1)))

        get_logger().log_info(f"Disk iotune for '{instance_name}': {iotune}")
        return iotune
