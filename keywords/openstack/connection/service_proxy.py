"""Logging proxy for OpenStack SDK service calls."""

from framework.logging.automation_logger import get_logger


class ServiceProxy:
    """Proxy that logs method calls on an OpenStack SDK service (compute, network, etc.)."""

    def __init__(self, service: object, service_name: str) -> None:
        """Initialize service proxy.

        Args:
            service (object): The real SDK service object.
            service_name (str): Name for logging (e.g. 'compute', 'image').
        """
        self._service = service
        self._service_name = service_name

    def __getattr__(self, name: str) -> object:
        """Intercept attribute access to log SDK method calls.

        Args:
            name (str): Attribute name being accessed.

        Returns:
            object: Wrapped callable that logs before/after, or the raw attribute.
        """
        attr = getattr(self._service, name)
        if not callable(attr):
            return attr

        def logged_call(*args, **kwargs):
            """Log and delegate the SDK call."""
            call_args = ", ".join([repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()])
            get_logger().log_info(f"OpenStack SDK: {self._service_name}.{name}({call_args})")
            result = attr(*args, **kwargs)
            return result

        return logged_call
