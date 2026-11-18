"""Kubectl PV RBD volume object for the Ceph RBD attributes of a CSI PersistentVolume."""


class KubectlPvRbdVolumeObject:
    """Represents the Ceph RBD pool and image backing a CSI PersistentVolume."""

    def __init__(self, pool: str, image_name: str):
        """Constructor.

        Args:
            pool (str): Name of the Ceph pool holding the RBD image.
            image_name (str): Name of the RBD image.
        """
        self._pool = pool
        self._image_name = image_name

    def get_pool(self) -> str:
        """Get the Ceph pool name.

        Returns:
            str: The pool the RBD image belongs to.
        """
        return self._pool

    def get_image_name(self) -> str:
        """Get the RBD image name.

        Returns:
            str: The RBD image name.
        """
        return self._image_name
