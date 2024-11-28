from framework.logging.automation_logger import get_logger


class BasePage:

    def pretty_print(self, value) -> str:
        """
        This function will return a log-readable version of value to add to a logging statement.
        Args:
            value: An kind of parameter that we want to log.

        Returns: str

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

        if hasattr(value, '__str__'):
            return value.__str__()

        return "?UNKNOWN?"

    def on_every_page_action(self, name: str, *args, **kwargs):
        """
        This function is a hook that gets called any time a page action function is invoked.
        It will log information about the action and the parameters passed in.
        Args:
            name: The name of the function being called.
            *args: arguments that have been passed to the page action.
            **kwargs: kwargs that have been passed in to the page action.

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

    def __getattribute__(self, name):
        """
        This is a default Python hook that gets called whenever Python tries to access a field or
        a function in a Page object. We are intercepting it here to place the on_every_page_action
        hook every time that we are calling a function.
        Args:
            name: The attribute or function getting accessed.

        Returns: If we are accessing a function, we return the function, wrapped in the
        on_every_page_action hook. Otherwise, we return the field directly.

        """

        # Avoid an infinite recursive loop with the wrapper on_every_keyword or pretty_print.
        if name == "on_every_page_action" or name == "pretty_print":
            return object.__getattribute__(self, name)

        # Check if 'name' is a function or a field.
        attribute = object.__getattribute__(self, name)
        if callable(attribute):

            # attribute is actually a function. Wrap it with on_every_page_action
            def on_page_action_wrapped_function(*args, **kwargs):
                self.on_every_page_action(name, *args, **kwargs)
                return attribute(*args, **kwargs)

            return on_page_action_wrapped_function

        else:

            # attribute is just a field. Return it as-is
            return attribute
