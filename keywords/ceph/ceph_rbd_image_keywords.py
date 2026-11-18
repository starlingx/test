"""Keywords for locating the RADOS data objects that back a Ceph RBD image."""

import re

from framework.exceptions.keyword_exception import KeywordException
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class CephRbdImageKeywords(BaseKeyword):
    """Keywords to find a real data object of an RBD image.

    Used to prove, via plain Ceph CLI (no custom pools/crush rules needed), that
    a real workload's data is actually placed across multiple OSDs as dictated
    by the pool's CRUSH rule.
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to a host with Ceph/RBD CLI access.
        """
        self.ssh_connection = ssh_connection

    def get_existing_data_object(self, pool: str, image_name: str) -> str:
        """Get the name of one existing RADOS data object backing an RBD image.

        Resolves the image's block_name_prefix via 'rbd info' and lists one of
        its data objects via 'rados ls', so the returned object is guaranteed
        to actually exist (unlike assuming a fixed offset), as long as the
        image already has at least one block of data written to it.

        Args:
            pool (str): The pool the image belongs to.
            image_name (str): The RBD image name.

        Returns:
            str: An existing RADOS object name belonging to the image.

        Raises:
            KeywordException: If the block_name_prefix cannot be resolved, or
                the image has no data objects yet.
        """
        info_output = self.ssh_connection.send(f"rbd info {pool}/{image_name}")
        self.validate_success_return_code(self.ssh_connection)
        info_text = "\n".join(info_output) if isinstance(info_output, list) else str(info_output)
        prefix_match = re.search(r"block_name_prefix:\s*(\S+)", info_text)
        if not prefix_match:
            raise KeywordException(f"Could not resolve block_name_prefix for image '{pool}/{image_name}'. Raw output: {info_text}")
        prefix = prefix_match.group(1)

        objects_output = self.ssh_connection.send(f"rados -p {pool} ls | grep {prefix}")
        objects = [line.strip() for line in objects_output if line.strip()] if isinstance(objects_output, list) else [line.strip() for line in str(objects_output).splitlines() if line.strip()]
        if not objects:
            raise KeywordException(f"No data objects found yet for image '{pool}/{image_name}' (prefix '{prefix}'). The image may not have been written to yet.")
        return objects[0]
