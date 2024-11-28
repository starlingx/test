from logging import Filter

"""
This filter class allows us to make the logger have a custom format for most log statements.
Since Exceptions and stack trace elements need a different format, they are filtered out.
"""


class LogNonExceptionFilter(Filter):

    def filter(self, record):
        """
        This function will accept any log records except those with a
        source of "EXC" (Exceptions and stack trace elements)
        Args:
          record: Record that we want to log.

        Returns: True for non-exception elements.

        """

        return "EXC" not in record.source
