from collections.abc import Iterator
from unittest.mock import MagicMock, NonCallableMagicMock, patch

import pytest

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.system.registry.registry_image_resolver_keywords import RegistryImageResolverKeywords

REGISTRY_URL = "registry.local:9001"
# The two callers' own preference tuples, which stay at their call sites. Repeated here because the
# corpus below compares against the behaviour those call sites had before the extraction.
CANDIDATES = ("busybox", "alpine", "curlimages/curl", "ceph-config-helper")


@pytest.fixture(autouse=True)
def _silence_loggers() -> Iterator[None]:
    """Silence the loggers, which raise unless a logger configuration exists.

    Yields:
        None: for the duration of each test.
    """
    with patch("keywords.base_keyword.get_logger"), patch("keywords.cloud_platform.system.registry.registry_image_resolver_keywords.get_logger"):
        yield


def _resolver(available: list, tags: list, reachable: bool = True) -> RegistryImageResolverKeywords:
    """Build a resolver whose registry reports the given names and tags.

    Args:
        available (list): image names the registry lists.
        tags (list): tags the registry reports for whichever image is chosen.
        reachable (bool): whether the registry answers at all.

    Returns:
        RegistryImageResolverKeywords: an instance wired to that registry.
    """
    keywords = RegistryImageResolverKeywords.__new__(RegistryImageResolverKeywords)

    image_list = NonCallableMagicMock()
    image_list.get_image_names = MagicMock(return_value=list(available))
    images = NonCallableMagicMock()
    images.is_registry_reachable = MagicMock(return_value=reachable)
    images.get_registry_image_list = MagicMock(return_value=image_list)

    tag_list = NonCallableMagicMock()
    tag_list.get_tag_names = MagicMock(return_value=list(tags))
    tag_reader = NonCallableMagicMock()
    tag_reader.get_image_tags = MagicMock(return_value=tag_list)

    object.__setattr__(keywords, "registry_images", images)
    object.__setattr__(keywords, "registry_tags", tag_reader)
    return keywords


def _resolve(available: list, tags: list, reachable: bool = True, candidates: tuple = CANDIDATES) -> str:
    """Resolve a reference against a stand-in registry.

    Args:
        available (list): image names the registry lists.
        tags (list): tags the registry reports.
        reachable (bool): whether the registry answers.
        candidates (tuple): the preference tuple to resolve against.

    Returns:
        str: the resolved reference.
    """
    with patch("keywords.cloud_platform.system.registry.registry_image_resolver_keywords.ConfigurationManager") as config:
        config.get_docker_config.return_value.get_local_registry.return_value.get_registry_url.return_value = REGISTRY_URL
        return _resolver(available, tags, reachable).resolve_image_reference(candidates)


class TestResolution:
    """What the resolver picks, and why."""

    def test_the_preference_order_decides_before_anything_else(self):
        """An earlier candidate wins even when a later one is also present."""
        available = ["docker.io/curlimages/curl", "docker.io/library/busybox"]
        assert _resolve(available, ["1.37.0"]) == f"{REGISTRY_URL}/docker.io/library/busybox:1.37.0"

    def test_the_name_is_chosen_by_sorting_within_a_candidate(self):
        """Two repositories can satisfy one candidate, and listing order must not decide."""
        available = ["docker.io/z-mirror/busybox", "docker.io/a-mirror/busybox"]
        assert _resolve(available, ["1.37.0"]) == f"{REGISTRY_URL}/docker.io/a-mirror/busybox:1.37.0"

    def test_the_tag_is_chosen_by_sorting(self):
        """Which tag is immaterial for a throwaway image; that it is reproducible is not."""
        assert _resolve(["docker.io/library/busybox"], ["1.37.0", "1.36.1"]).endswith(":1.36.1")

    def test_an_exact_trailing_segment_is_preferred_over_a_substring(self):
        """A variant name must not beat the image actually asked for."""
        available = ["docker.io/library/busybox-extras", "docker.io/library/busybox"]
        assert _resolve(available, ["1.37.0"]) == f"{REGISTRY_URL}/docker.io/library/busybox:1.37.0"

    def test_a_variant_name_is_still_found_when_it_is_all_there_is(self):
        """The tiering must not shrink what can be found.

        A strict segment match alone would reject busybox-extras, radial/busyboxplus and
        alpine/socat - all shell-capable, all found by the substring form this replaces. Losing
        images to gain determinism is a trade with no upside when tiering gets both.
        """
        assert _resolve(["docker.io/library/busybox-extras"], ["1.37.0"]).endswith("/docker.io/library/busybox-extras:1.37.0")

    def test_an_exact_bare_name_beats_a_variant_that_sorts_before_it(self):
        """The exact tier has to recognise a bare name, not only a suffixed one.

        Without the equality arm a bare "busybox" is invisible to the exact tier, falls through to
        the substring tier, and loses to any variant that sorts ahead of it alphabetically.
        """
        available = ["alpine-busybox", "busybox"]
        assert _resolve(available, ["1.37.0"]) == f"{REGISTRY_URL}/busybox:1.37.0"

    def test_the_fallback_tier_sorts_too(self):
        """Determinism must hold in the substring tier, not only the exact one.

        A registry carrying two variant names and no exact match still has to resolve the same way
        on every run, otherwise the tiering has only moved the nondeterminism one level down.
        """
        available = ["docker.io/z/busyboxplus", "docker.io/a/busybox-extras"]
        assert _resolve(available, ["1.37.0"]) == f"{REGISTRY_URL}/docker.io/a/busybox-extras:1.37.0"

    def test_a_bare_unprefixed_name_matches(self):
        """A registry is not obliged to report a host or project prefix."""
        assert _resolve(["busybox"], ["1.37.0"]) == f"{REGISTRY_URL}/busybox:1.37.0"

    def test_a_candidate_containing_a_slash_matches(self):
        """curlimages/curl is a candidate with a slash in it.

        The review suggested matching the final path component as name.split("/")[-1] == candidate.
        That can never match this candidate, so the second-preference image would silently stop
        being selectable.
        """
        assert _resolve(["docker.io/curlimages/curl"], ["8.19.0"], candidates=("curlimages/curl",)).endswith("/docker.io/curlimages/curl:8.19.0")

    def test_the_registry_is_asked_every_call(self):
        """Resolution is not cached here.

        One caller resolves once per upgrade phase and relies on the reachability check running
        again in each one, because a registry that went down during the upgrade is a regression that
        must be reported as itself rather than as a pod that would not start. Caching belongs to the
        caller that resolves repeatedly within a phase, not to this keyword.
        """
        resolver = _resolver(["docker.io/library/busybox"], ["1.37.0"])
        with patch("keywords.cloud_platform.system.registry.registry_image_resolver_keywords.ConfigurationManager") as config:
            config.get_docker_config.return_value.get_local_registry.return_value.get_registry_url.return_value = REGISTRY_URL
            resolver.resolve_image_reference(CANDIDATES)
            resolver.resolve_image_reference(CANDIDATES)
        assert resolver.registry_images.is_registry_reachable.call_count == 2


class TestFailures:
    """Each failure names itself rather than surfacing later as something else."""

    def test_an_unreachable_registry_fails_as_itself(self):
        """Otherwise it surfaces as an image that will not pull."""
        with pytest.raises(KeywordException, match="not reachable"):
            _resolve(["docker.io/library/busybox"], ["1.37.0"], reachable=False)

    def test_no_candidate_fails_and_names_what_was_found(self):
        """The listing is the only thing that makes this diagnosable on an unfamiliar lab."""
        with pytest.raises(KeywordException, match="nginx"):
            _resolve(["docker.io/library/nginx"], ["1.0"])

    def test_an_untagged_image_fails_rather_than_pulling_latest(self):
        """A bare name resolves to an implicit :latest against a public registry."""
        with pytest.raises(KeywordException, match="no tags"):
            _resolve(["docker.io/library/busybox"], [])


# --------------------------------------------------------------------------------------------------
# Characterisation corpus.
#
# The lab these keywords run on is no longer reachable, so the before/after comparison cannot be run
# on hardware. These are the two selection rules as they stood before the extraction, copied
# verbatim, and the corpus asserts the new implementation agrees with both of them everywhere except
# where it is meant to differ. That is a proof of inertness rather than an assertion of a golden
# value: on the single-name single-tag shape a real lab reports, every candidate implementation
# agrees, so a recorded golden reference would prove nothing.
# --------------------------------------------------------------------------------------------------


def _old_istio(available: list, tags: list) -> str:
    """Reproduce istio's selection as it stood before the extraction.

    Args:
        available (list): image names the registry lists.
        tags (list): tags for the chosen image.

    Returns:
        str: the reference istio would have built.
    """
    chosen = next((name for candidate in CANDIDATES for name in available if candidate in name), None)
    return f"{REGISTRY_URL}/{chosen}:{tags[0]}"


def _old_reloader(available: list, tags: list) -> str:
    """Reproduce reloader's selection as it stood before the extraction.

    Args:
        available (list): image names the registry lists.
        tags (list): tags for the chosen image.

    Returns:
        str: the reference reloader would have built.
    """
    chosen = next((name for candidate in CANDIDATES for name in sorted(available) if candidate in name), None)
    return f"{REGISTRY_URL}/{chosen}:{sorted(tags)[0]}"


# Each entry is (name, available, tags, diverges_from_istio, diverges_from_reloader).
# Divergence is allowed only where the new rule is strictly more determined than the old one.
CORPUS = [
    # The listing recorded on a 26.03 AIO-SX, which carried curlimages/curl and no busybox.
    ("recorded 26.03 registry", ["registry.k8s.io/pause", "docker.io/curlimages/curl", "docker.io/openstackhelm/ceph-config-helper"], ["8.17.0"], False, False),
    ("single busybox, single tag", ["docker.io/library/busybox"], ["1.37.0"], False, False),
    ("bare unprefixed name", ["busybox"], ["1.37.0"], False, False),
    ("variant name only", ["docker.io/library/busybox-extras"], ["1.37.0"], False, False),
    ("curl candidate with a slash", ["docker.io/curlimages/curl"], ["8.19.0"], False, False),
    # Multiple repositories satisfy one candidate: istio took listing order, the new rule sorts.
    ("multi-mirror busybox", ["docker.io/z-mirror/busybox", "docker.io/a-mirror/busybox"], ["1.37.0"], True, False),
    # Multiple tags: istio took listing order, the new rule sorts.
    ("multi-tag busybox", ["docker.io/library/busybox"], ["1.37.0", "1.36.1"], True, False),
    # Exact segment beats substring. Both old rules took whichever the listing offered first.
    ("variant and exact together", ["docker.io/library/busybox-extras", "docker.io/library/busybox"], ["1.37.0"], True, False),
    # Only variant names, listed out of order: both old rules took the listing's first, the new
    # rule sorts within the fallback tier too.
    ("two variant names out of order", ["docker.io/z/busyboxplus", "docker.io/a/busybox-extras"], ["1.37.0"], True, False),
    # A variant that sorts before the exact match: both old rules took the variant, because
    # neither distinguished an exact repository segment from a substring. The new rule prefers the
    # image actually asked for.
    ("variant sorts before the exact match", ["docker.io/a/busybox-extras", "docker.io/z/busybox"], ["1.37.0"], True, True),
]


class TestAgreementWithThePreviousImplementations:
    """The new rule must change nothing except where it is meant to."""

    @pytest.mark.parametrize("name,available,tags,diverges_istio,diverges_reloader", CORPUS)
    def test_agreement(self, name: str, available: list, tags: list, diverges_istio: bool, diverges_reloader: bool):
        """Compare the new resolution against both previous rules.

        Args:
            name (str): the fixture's name, for the failure message.
            available (list): image names the registry lists.
            tags (list): tags for the chosen image.
            diverges_istio (bool): whether divergence from istio's old rule is intended here.
            diverges_reloader (bool): whether divergence from reloader's old rule is intended here.
        """
        new = _resolve(available, tags)
        istio_old = _old_istio(available, tags)
        reloader_old = _old_reloader(available, tags)

        if diverges_istio:
            assert new != istio_old, f"{name}: divergence from istio was expected here but did not happen"
        else:
            assert new == istio_old, f"{name}: istio's result changed and that was not intended"

        if diverges_reloader:
            assert new != reloader_old, f"{name}: divergence from reloader was expected here but did not happen"
        else:
            assert new == reloader_old, f"{name}: reloader's result changed and that was not intended"

    def test_the_corpus_covers_both_divergence_directions(self):
        """A corpus where nothing diverges would pass against an unchanged implementation."""
        assert any(entry[3] for entry in CORPUS), "no fixture exercises divergence from istio"
        assert any(entry[4] for entry in CORPUS), "no fixture exercises divergence from reloader"
        assert any(not entry[3] and not entry[4] for entry in CORPUS), "no fixture pins agreement with both"
