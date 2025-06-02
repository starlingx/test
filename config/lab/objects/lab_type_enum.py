from enum import Enum


class LabTypeEnum(Enum):
    """Enumeration for different types of labs.

    This enum is used to categorize labs based on their type, such as 'Simplex', 'Duplex', or 'AIO+'.

    """

    SIMPLEX = "Simplex"  # A lab with a single controller.
    DUPLEX = "Duplex"  # A lab with two controllers for redundancy.
    AIO_PLUS = "AIO+"  # A lab with an All-In-One Plus configuration, typically with additional resources or capabilities.
    STORAGE = "Storage"  # A lab that has storage nodes > 0
    STANDARD = "Standard"  # A lab that has worker nodes > 0
