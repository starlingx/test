from logging import Filter

"""
This filter class allows us to make the logger have a trivial format
when logging Exceptions and stack traces.
"""


class LogExceptionFilter(Filter):

    def filter(self, record):
        """
        This function will accept only log records that have a source of "EXC", meaning
        that they are exceptions or stack trace elements.
        Args:
          record: Record that we want to log.

        Returns: True for exception elements.

        """
        return "EXC" in record.source
