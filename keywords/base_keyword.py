from typing import Any

from framework.logging.automation_logger import get_logger
from framework.rest.rest_response import RestResponse
from framework.ssh.ssh_connection import SSHConnection


class BaseKeyword:
    """Base class for keyword implementations.

    This class provides shared functionality for custom keywords,
    including validation helpers and utility methods that can be
    reused by subclasses.
    """

    def pretty_print(self, value: Any) -> str:
        """
        This function will return a log-readable version of value to add to a logging statement.

        Args:
            value (Any): An kind of parameter that we want to log.

        Returns:
            str: A formatted string representation of the value.
        """
        if value is None:
            return "None"

        if isinstance(value, str):
            return value

        if isinstance(value, (int, float, bool)):
            return str(value)

        # If we are dealing with a list, pretty_print each item individually.
        if isinstance(value, list):
            pretty_list_items = [self.pretty_print(list_item) for list_item in value]
            pretty_print_list = ", ".join(pretty_list_items)
            return f"[{pretty_print_list}]"

        if isinstance(value, tuple):
            pretty_tuple_items = [self.pretty_print(list_item) for list_item in value]
            pretty_print_list = ", ".join(pretty_tuple_items)
            return f"({pretty_print_list})"

        # If we are dealing with a dictionary, pretty_print each item individually.
        if isinstance(value, dict):
            pretty_print_dict = ""
            for key in value.keys():
                pretty_print_dict += f"{self.pretty_print(key)}:{self.pretty_print(value[key])}, "
            # Trim out the ending comma
            pretty_print_dict = pretty_print_dict.rstrip(", ")
            return "{" + pretty_print_dict + "}"

        if hasattr(value, "__str__"):
            return value.__str__()

        return "?UNKNOWN?"

    def on_every_keyword(self, name: str, *args: Any, **kwargs: Any):
        """
        Hook executed whenever a keyword function is invoked.

        This function is a hook that gets called any time a Keyword function is invoked.
        It will log information about the keyword and the parameters passed in.

        Args:
            name (str): The name of the function being called.
            *args (Any): arguments that have been passed to the keyword
            **kwargs (Any): kwargs that have been passed in to the keyword.

        Returns: None

        """
        args_string = ""
        if args:
            # args are treated as a tuple. Remove the enclosing tuple "()".
            args_string += self.pretty_print(args)
            args_string = args_string.rstrip(")")
            args_string = args_string.lstrip("(")
        if kwargs:
            # kwargs are treated as a dict. Remove the enclosing tuple "{}".
            args_string += self.pretty_print(kwargs)
            args_string = args_string.rstrip("}")
            args_string = args_string.lstrip("{")

        get_logger().log_keyword(f"{name}({args_string})")

    def __getattribute__(self, name: str) -> Any:
        """Intercept attribute access on a Keyword object.

        This is a default Python hook that gets called whenever Python tries to access a field or
        a function in a Keyword object. We are intercepting it here to place the on_every_keyword
        hook every time that we are calling a function.

        Args:
            name (str): The attribute or function getting accessed.

        Returns:
          Any: If we are accessing a function, we return the function, wrapped in the
        on_every_keyword hook. Otherwise, we return the field directly.

        """
        # Avoid an infinite recursive loop with the wrapper on_every_keyword or pretty_print.
        if name == "on_every_keyword" or name == "pretty_print":
            return object.__getattribute__(self, name)

        # Check if 'name' is a function or a field.
        attribute = object.__getattribute__(self, name)
        if callable(attribute):

            # attribute is actually a function. Wrap it with on_every_keyword
            def on_keyword_wrapped_function(*args, **kwargs):
                self.on_every_keyword(name, *args, **kwargs)
                return attribute(*args, **kwargs)

            return on_keyword_wrapped_function

        else:

            # attribute is just a field. Return it as-is
            return attribute

    def validate_success_return_code(self, ssh_connection: SSHConnection):
        """
        Validates a successful return code was received

        Args:
            ssh_connection (SSHConnection): the ssh connection

        """
        rc = ssh_connection.get_return_code()
        assert 0 == rc, f"Return code was {rc}"

    def validate_cmd_rejection_return_code(self, ssh_connection: SSHConnection) -> bool:
        """
        Validates a command rejection return code was received

        Args:
            ssh_connection (SSHConnection): the ssh connection

        Returns:
            bool: True if command was correctly rejected, False if it wasn't.

        """
        rc = ssh_connection.get_return_code()
        assert rc != 0, f"Return code was {rc}, command was rejected successfully."
        return True

    def validate_success_status_code(self, rest_response: RestResponse, expected_status_code: int = 200):
        """
        Validates a successful status code was received

        Args:
            rest_response (RestResponse): the rest response object
            expected_status_code(int): the expected status code - default is 200
        """
        rc = rest_response.get_status_code()
        assert expected_status_code == rc, f"Status code was {rc}"
