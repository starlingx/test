"""Typed IPsec application evidence."""

import copy
import json


class IPsecPolicyImagesOutput:
    """Immutable container identities indexed by role and workload identity."""

    def __init__(self, images: dict[str, dict[str, str]]):
        """Capture already normalized container records.

        Args:
            images (dict[str, dict[str, str]]): Role/workload container digests.
        """
        self.images = copy.deepcopy(images)

    def get_workload_names(self) -> tuple[str, ...]:
        """Return role/workload identities.

        Returns:
            tuple[str, ...]: Workload keys.
        """
        return tuple(self.images)

    def get_container_images(self, workload: str) -> dict[str, str]:
        """Return immutable images for a selected workload.

        Args:
            workload (str): Role/workload identity.

        Returns:
            dict[str, str]: Container digest mapping.
        """
        return dict(self.images[workload])

    def get_role_images(self, role: str) -> list[list[tuple[str, str]]]:
        """Return canonical role images independent of rollout pod names.

        Args:
            role (str): Application role, agent or manager.

        Returns:
            list[list[tuple[str, str]]]: Canonical image comparison evidence.
        """
        return sorted(sorted(value.items()) for key, value in self.images.items() if key.startswith(role + "/"))

    def get_log_summary(self) -> str:
        """Return stable readable image evidence for execution logs.

        Returns:
            str: Role/workload container identities as JSON text.
        """
        return json.dumps(self.images, sort_keys=True)
