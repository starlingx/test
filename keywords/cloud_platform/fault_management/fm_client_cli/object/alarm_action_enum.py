from enum import Enum


class AlarmAction(Enum):
    """
    Class Enum to support the possible values of the first parameter for the fmClientCli command.
    Possible values for the first parameter:
        -c: create an alarm;
        -D: delete the alarm;

    """

    CREATE = "-c"
    DELETE = "-D"
