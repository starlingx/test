import json

from keywords.cloud_platform.bios.objects.bios_export_artifact_writer import BiosExportArtifactWriter


def test_none_is_written_as_null(tmp_path):
    """Keep values that were not reported as JSON null, distinct from empty strings."""
    path = tmp_path / "bios_identity.json"
    BiosExportArtifactWriter().write_json(path, {"bios_version": "1.01", "product_version": None, "board_version": ""})
    assert json.loads(path.read_text()) == {"bios_version": "1.01", "product_version": None, "board_version": ""}


def test_credentials_are_redacted(tmp_path):
    """Redact credential-like keys, including nested ones."""
    path = tmp_path / "bios.json"
    BiosExportArtifactWriter().write_json(path, {"AdminPassword": "plain", "nested": [{"token": "abc"}], "ProcCStates": "Disabled"})
    assert json.loads(path.read_text()) == {"AdminPassword": "<redacted>", "nested": [{"token": "<redacted>"}], "ProcCStates": "Disabled"}
