from typing import Optional

from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_list_object import DcManagerSubcloudListObject
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_show_object import DcManagerSubcloudShowObject


class SubcloudPickResult:
    """Result of a subcloud selection performed by SubcloudPickerKeywords.

    Wraps the ``DcManagerSubcloudListObject`` for the selected subcloud and,
    when the picker had to invoke ``dcmanager subcloud show`` (because the
    ``load`` filter was used), the corresponding ``DcManagerSubcloudShowObject``.
    """

    def __init__(
        self,
        name: str,
        dcmanager_id: int,
        software_version: Optional[str],
        list_object: DcManagerSubcloudListObject,
        show_object: Optional[DcManagerSubcloudShowObject],
    ):
        """Constructor.

        Args:
            name (str): The subcloud name.
            dcmanager_id (int): The numeric dcmanager id.
            software_version (Optional[str]): The software version reported by
                ``dcmanager subcloud show``, or ``None`` when ``subcloud show``
                was not invoked.
            list_object (DcManagerSubcloudListObject): The matching row from
                ``dcmanager subcloud list``.
            show_object (Optional[DcManagerSubcloudShowObject]): The matching
                ``dcmanager subcloud show`` object, or ``None`` when not
                consulted.
        """
        self.name = name
        self.dcmanager_id = dcmanager_id
        self.software_version = software_version
        self.list_object = list_object
        self.show_object = show_object

    def get_name(self) -> str:
        """Return the subcloud name."""
        return self.name

    def get_id(self) -> int:
        """Return the subcloud's numeric dcmanager id."""
        return self.dcmanager_id

    def get_software_version(self) -> Optional[str]:
        """Return the software version reported by ``dcmanager subcloud show``.

        Returns ``None`` when the picker did not need to call ``subcloud show``
        (filters did not require the version).
        """
        return self.software_version

    def get_list_object(self) -> DcManagerSubcloudListObject:
        """Return the underlying ``DcManagerSubcloudListObject``."""
        return self.list_object

    def get_show_object(self) -> Optional[DcManagerSubcloudShowObject]:
        """Return the underlying ``DcManagerSubcloudShowObject`` if loaded."""
        return self.show_object

    def __repr__(self) -> str:
        """Developer-facing representation."""
        return f"{self.__class__.__name__}(name={self.name}, id={self.dcmanager_id}, software_version={self.software_version})"
