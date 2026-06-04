"""ACE wrapper for OpenStack SDK connection with logging proxies."""

from keywords.openstack.connection.openstack_connection import OpenStackConnection
from keywords.openstack.connection.service_proxy import ServiceProxy


class ACEOpenStackConnection:
    """Wrapper around OpenStackConnection that logs all SDK service calls.

    Provides typed service accessors instead of exposing the raw SDK connection.
    Keywords should call service methods through these accessors.
    """

    def __init__(self, openstack_connection: OpenStackConnection) -> None:
        """Initialize ACE OpenStack connection wrapper.

        Args:
            openstack_connection (OpenStackConnection): The real connection.
        """
        self._openstack_connection = openstack_connection
        self._proxies = {}

    def _get_service_proxy(self, service_name: str) -> ServiceProxy:
        """Get or create a logging proxy for the named SDK service.

        Args:
            service_name (str): SDK service attribute name (e.g. 'compute', 'image').

        Returns:
            ServiceProxy: Logging proxy for the service.
        """
        if service_name not in self._proxies:
            real_conn = self._openstack_connection.get_connection()
            service = getattr(real_conn, service_name)
            self._proxies[service_name] = ServiceProxy(service, service_name)
        return self._proxies[service_name]

    def get_compute(self) -> ServiceProxy:
        """Get the compute (Nova) service proxy.

        Returns:
            ServiceProxy: Logging proxy for compute operations.
        """
        return self._get_service_proxy("compute")

    def get_image(self) -> ServiceProxy:
        """Get the image (Glance) service proxy.

        Returns:
            ServiceProxy: Logging proxy for image operations.
        """
        return self._get_service_proxy("image")

    def get_network(self) -> ServiceProxy:
        """Get the network (Neutron) service proxy.

        Returns:
            ServiceProxy: Logging proxy for network operations.
        """
        return self._get_service_proxy("network")

    def get_identity(self) -> ServiceProxy:
        """Get the identity (Keystone) service proxy.

        Returns:
            ServiceProxy: Logging proxy for identity operations.
        """
        return self._get_service_proxy("identity")

    def get_block_storage(self) -> ServiceProxy:
        """Get the block storage (Cinder) service proxy.

        Returns:
            ServiceProxy: Logging proxy for block storage operations.
        """
        return self._get_service_proxy("block_storage")

    def get_auth_details(self) -> dict:
        """Delegate auth details to the real connection.

        Returns:
            dict: Authentication details.
        """
        return self._openstack_connection.get_auth_details()
