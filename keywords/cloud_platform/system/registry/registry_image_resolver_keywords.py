from config.configuration_manager import ConfigurationManager
from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.system.registry.system_registry_image_list_keywords import SystemRegistryImageListKeywords
from keywords.cloud_platform.system.registry.system_registry_image_tags_keywords import SystemRegistryImageTagsKeywords


def _choose_name(available: list, candidates: tuple) -> str:
    """Pick one image name from a registry listing, by preference and then deterministically.

    Each candidate is tried in turn against two tiers. The first prefers an exact trailing
    repository segment, so a candidate asked for by name is not beaten by a variant that merely
    contains it. The second falls back to a substring, which is what keeps the set of findable
    images the same as before this rule existed: a registry carrying only `library/busybox-extras`
    or `radial/busyboxplus` still resolves, where an exact-segment-only rule would have reported no
    candidate at all. Both tiers sort, so the listing order never decides.

    Args:
        available (list): image names as the registry reports them.
        candidates (tuple): acceptable images in preference order.

    Returns:
        str: the chosen name, or None when no candidate is present.
    """
    for candidate in candidates:
        exact = sorted(name for name in available if name == candidate or name.endswith(f"/{candidate}"))
        if exact:
            return exact[0]
        loose = sorted(name for name in available if candidate in name)
        if loose:
            return loose[0]
    return None


class RegistryImageResolverKeywords(BaseKeyword):
    """Resolve an acceptable image in the local registry to a reference that can be pulled.

    Tests that need a throwaway workload cannot pin an image: the local registry's contents differ
    between labs, and a reference that is not present fails to pull in a way that looks exactly like
    whatever the test was actually checking. This resolves the first acceptable candidate a registry
    does hold, and fails with a named reason when it holds none.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection
        self.registry_images = SystemRegistryImageListKeywords(ssh_connection)
        self.registry_tags = SystemRegistryImageTagsKeywords(ssh_connection)

    def resolve_image_reference(self, candidates: tuple) -> str:
        """Resolve the first acceptable candidate to a fully qualified, pullable reference.

        The host prefix and the tag both matter. The registry listing carries neither, and a bare
        repository name resolves to an implicit :latest against a public registry, which fails to
        pull for a reason that has nothing to do with the caller's check.

        Nothing is cached. One caller resolves once per upgrade phase and depends on the
        reachability check running again in each of them, because a registry that went down during
        an upgrade is a regression worth reporting as itself rather than as a workload that would
        not start. A caller that resolves repeatedly within a phase should hold the result itself.

        Args:
            candidates (tuple): acceptable images in preference order. Required rather than
                defaulted, because the choice is the caller's policy: a workload that overrides the
                container command needs an image carrying a shell, and that is not a property this
                keyword can assume on a caller's behalf.

        Returns:
            str: a fully qualified image reference, host and tag included.

        Raises:
            KeywordException: when the registry is unreachable, holds none of the candidates, or
                reports the chosen image with no tags.
        """
        if not self.registry_images.is_registry_reachable():
            raise KeywordException("the local registry is not reachable, so no probe image can be resolved")

        available = self.registry_images.get_registry_image_list().get_image_names()
        chosen = _choose_name(available, candidates)
        if chosen is None:
            raise KeywordException(f"no probe image matching any of {candidates} is present in the local registry. Found: {sorted(available)}")

        tags = self.registry_tags.get_image_tags(chosen).get_tag_names()
        if not tags:
            raise KeywordException(f"the local registry reports image {chosen} with no tags, so it cannot be pulled")

        registry_url = ConfigurationManager.get_docker_config().get_local_registry().get_registry_url()
        reference = f"{registry_url}/{chosen}:{sorted(tags)[0]}"
        get_logger().log_info(f"image resolved to {reference} (tags available: {tags})")
        return reference
