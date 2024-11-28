import socket


class RunHostInfoClass:
    """
    Singleton Class that keeps track of the information about the host currently running the tests.
    """

    def __init__(self):
        self._cached_host_ip = None

    def _get_host_ip_from_system(self):
        """
        Gets the host ip
        Returns: the host ip
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        host_ip = s.getsockname()[0]
        s.close()

        return host_ip

    def get_host_ip(self):
        """
        Gets the host ip.
        Returns: the host ip
        """
        if self._cached_host_ip is None:
            self._cached_host_ip = self._get_host_ip_from_system()

        return self._cached_host_ip


RunHostInfo = RunHostInfoClass()
