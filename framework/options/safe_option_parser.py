from optparse import OptionConflictError, OptionParser
from typing import Any, Dict

from pytest import Parser


class SafeOptionParser:
    """Class that abstracts out the differences in setting Pytest options and OptionParser options."""

    def __init__(self, parser: Any = None):
        """Initialize SafeOptionParser with an optional OptionParser or Pytest Parser instance.

        Args:
            parser (Any): An existing OptionParser or Parser instance to wrap. If None, a new OptionParser will be created. Defaults to None.
        """
        if not parser:
            parser = OptionParser()

        options_parser = None
        if isinstance(parser, OptionParser):
            options_parser = parser

        pytest_parser = None
        if isinstance(parser, Parser):
            pytest_parser = parser

        # These implementations are mutually exclusive. Only one should be set at a time.
        self.options_parser = options_parser
        self.pytest_parser = pytest_parser

    def add_option(self, *args: Dict, **kwargs: Dict):
        """Add an option to the underlying OptionParser.

        Args:
            *args (Dict): Positional arguments to pass to OptionParser.add_option
            **kwargs (Dict): Keyword arguments to pass to OptionParser.add_option

        """
        try:
            if self.options_parser:
                self.options_parser.add_option(*args, **kwargs)
            else:
                self.pytest_parser.addoption(*args, **kwargs)
        except (OptionConflictError, ValueError):
            pass  # We know that sometimes options get added twice, but we only need them once.

    def get_option_parser(self) -> Any:
        """Get the underlying OptionParser instance.

        Returns:
            Any: The wrapped OptionParser instance.
        """
        if self.options_parser:
            return self.options_parser
        else:
            return self.pytest_parser
