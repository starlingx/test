import re

from keywords.files.object.head_files_output import HeadFilesOutput
from keywords.linux.dmi.object.dmi_bios_identity_object import DmiBiosIdentityObject


class DmiBiosIdentityOutput:
    """Builds a DmiBiosIdentityObject from the ``/sys/class/dmi/id`` files that were read."""

    DMI_FOLDER = "/sys/class/dmi/id"
    # Firmware often leaves these in fields it does not fill in, e.g. Intel server boards report
    # a row of dots as product_version. They carry no information, so they are treated as not reported.
    PLACEHOLDER_PATTERN = re.compile(r"\.+|to be filled by o\.e\.m\.|default string|not specified", re.IGNORECASE)

    FIELD_SETTERS = {
        "bios_vendor": DmiBiosIdentityObject.set_bios_vendor,
        "bios_version": DmiBiosIdentityObject.set_bios_version,
        "bios_date": DmiBiosIdentityObject.set_bios_date,
        "sys_vendor": DmiBiosIdentityObject.set_sys_vendor,
        "product_name": DmiBiosIdentityObject.set_product_name,
        "product_version": DmiBiosIdentityObject.set_product_version,
        "board_vendor": DmiBiosIdentityObject.set_board_vendor,
        "board_name": DmiBiosIdentityObject.set_board_name,
        "board_version": DmiBiosIdentityObject.set_board_version,
    }

    def __init__(self, head_files_output: HeadFilesOutput):
        """Constructor.

        Args:
            head_files_output (HeadFilesOutput): Contents of the DMI identity files.
        """
        self.dmi_bios_identity_object = DmiBiosIdentityObject()
        for field_name, setter in self.FIELD_SETTERS.items():
            file_path = f"{self.DMI_FOLDER}/{field_name}"
            if head_files_output.has_file(file_path):
                value = head_files_output.get_file_content(file_path)
                if not self.PLACEHOLDER_PATTERN.fullmatch(value):
                    setter(self.dmi_bios_identity_object, value)

    @classmethod
    def get_file_paths(cls) -> list[str]:
        """Get the DMI files this output reads.

        Returns:
            list[str]: Absolute DMI file paths.
        """
        return [f"{cls.DMI_FOLDER}/{field_name}" for field_name in cls.FIELD_SETTERS]

    def get_dmi_bios_identity_object(self) -> DmiBiosIdentityObject:
        """Get the parsed BIOS identity.

        Returns:
            DmiBiosIdentityObject: BIOS, system and board identity.
        """
        return self.dmi_bios_identity_object
