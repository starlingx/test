from keywords.files.object.head_files_output import HeadFilesOutput
from keywords.linux.dmi.object.dmi_bios_identity_output import DmiBiosIdentityOutput


def test_maps_dmi_files_to_identity_fields():
    """Populate every field whose DMI file was read."""
    head_output = HeadFilesOutput("==> /sys/class/dmi/id/bios_vendor <==\nAmerican Megatrends International, LLC.\n" "==> /sys/class/dmi/id/bios_version <==\n1.01\n" "==> /sys/class/dmi/id/bios_date <==\n12/07/2023\n" "==> /sys/class/dmi/id/board_version <==\n1395A3431801\n")
    identity = DmiBiosIdentityOutput(head_output).get_dmi_bios_identity_object()
    assert identity.get_bios_vendor() == "American Megatrends International, LLC."
    assert identity.get_bios_version() == "1.01"
    assert identity.get_bios_date() == "12/07/2023"
    assert identity.get_board_version() == "1395A3431801"


def test_missing_dmi_files_stay_none():
    """Leave fields unset when the host does not expose the file."""
    identity = DmiBiosIdentityOutput(HeadFilesOutput("")).get_dmi_bios_identity_object()
    assert identity.get_bios_version() is None
    assert set(identity.to_dictionary()) == {"bios_vendor", "bios_version", "bios_date", "sys_vendor", "product_name", "product_version", "board_vendor", "board_name", "board_version"}


def test_file_paths_cover_every_field():
    """Read one DMI file per identity field."""
    assert DmiBiosIdentityOutput.get_file_paths()[0] == "/sys/class/dmi/id/bios_vendor"
    assert len(DmiBiosIdentityOutput.get_file_paths()) == 9


def test_placeholder_values_are_not_reported():
    """Treat firmware placeholders such as a row of dots as not reported."""
    head_output = HeadFilesOutput("==> /sys/class/dmi/id/product_version <==\n....................\n" "==> /sys/class/dmi/id/board_version <==\nTo Be Filled By O.E.M.\n" "==> /sys/class/dmi/id/bios_version <==\nSE5C610.86B.01.01.3029.022420221031\n")
    identity = DmiBiosIdentityOutput(head_output).get_dmi_bios_identity_object()
    assert identity.get_product_version() is None
    assert identity.get_board_version() is None
    assert identity.get_bios_version() == "SE5C610.86B.01.01.3029.022420221031"
