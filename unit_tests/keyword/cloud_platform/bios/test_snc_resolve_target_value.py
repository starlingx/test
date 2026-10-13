from keywords.cloud_platform.bios.objects.snc_profile import SncProfile

# Dell profile mirrors the one SncKeywords ships: prefer 4-Way, fall back to 2-Way.
DELL_PROFILE = SncProfile(manufacturer="dell", attribute="SubNumaCluster", enable_candidates=["4-Way", "2-Way"], disable="Disabled")


def test_prefers_4way_when_allowed():
    """select_enable_value picks 4-Way when the BMC lists it as allowable."""
    assert DELL_PROFILE.select_enable_value(["4-Way", "2-Way", "Disabled"]) == "4-Way"


def test_falls_back_to_2way_when_4way_unavailable():
    """select_enable_value falls back to 2-Way when 4-Way is not allowable (e.g. SX-025)."""
    assert DELL_PROFILE.select_enable_value(["2-Way", "Disabled"]) == "2-Way"


def test_uses_preferred_when_no_allowable_list():
    """select_enable_value uses the most-preferred candidate when the BMC lists none."""
    assert DELL_PROFILE.select_enable_value(None) == "4-Way"
    assert DELL_PROFILE.select_enable_value([]) == "4-Way"


def test_returns_none_when_no_candidate_allowable():
    """select_enable_value returns None when none of the candidates is allowable."""
    assert DELL_PROFILE.select_enable_value(["Disabled"]) is None


def test_single_candidate_profile():
    """A single-candidate profile (e.g. HPE) selects that candidate when allowed."""
    hpe = SncProfile(manufacturer="hpe", attribute="SubNumaClustering", enable_candidates=["Enabled"], disable="Disabled")
    assert hpe.select_enable_value(["Enabled", "Disabled"]) == "Enabled"
    assert hpe.select_enable_value(["Disabled"]) is None
