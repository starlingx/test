"""Unit tests for the default Horizon URL of the lab config."""

import json

from config.lab.objects.lab_config import LabConfig
from framework.resources.resource_finder import get_stx_resource_path


def _load_lab_config(tmp_path, floating_ip: str, horizon_url: str = None) -> LabConfig:
    """
    Build a LabConfig from the simplex template with a given floating IP.

    Args:
        tmp_path: pytest temporary directory.
        floating_ip (str): floating IP to put in the lab config.
        horizon_url (str): explicit horizon_url to set, or None to leave it out.

    Returns:
        LabConfig: the loaded lab config.
    """
    import json5

    with open(get_stx_resource_path("config/lab/files/template_simplex.json5")) as template:
        lab_dict = json5.load(template)
    lab_dict["floating_ip"] = floating_ip
    lab_dict.pop("horizon_url", None)
    if horizon_url:
        lab_dict["horizon_url"] = horizon_url
    config_file = tmp_path / "lab.json5"
    config_file.write_text(json.dumps(lab_dict))
    return LabConfig(str(config_file))


def test_default_horizon_url_for_ipv4_has_no_brackets(tmp_path):
    """An IPv4 floating IP gives a plain URL; brackets would make it invalid."""
    lab_config = _load_lab_config(tmp_path, "10.44.10.179")
    assert lab_config.get_horizon_url() == "https://10.44.10.179:8443/", "IPv4 horizon URL must not be bracketed"


def test_default_horizon_url_for_ipv6_is_bracketed(tmp_path):
    """An IPv6 floating IP is bracketed in the URL."""
    lab_config = _load_lab_config(tmp_path, "3851:dc57:c69a:3c77:5d53:29a1:f39c:3d9f")
    assert lab_config.get_horizon_url() == "https://[3851:dc57:c69a:3c77:5d53:29a1:f39c:3d9f]:8443/", "IPv6 horizon URL must be bracketed"


def test_explicit_horizon_url_is_kept(tmp_path):
    """A horizon_url set in the lab config is used as it is."""
    lab_config = _load_lab_config(tmp_path, "10.44.10.179", horizon_url="https://example.test:9999/")
    assert lab_config.get_horizon_url() == "https://example.test:9999/", "explicit horizon_url must win"
