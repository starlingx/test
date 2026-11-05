"""A snapshot of one reloader test workload and its current pod, taken at one instant.

Every numeric field is coerced on the way in. The underlying reads are jsonpath string reads, and
comparing them as strings makes generation 9 to 10 look like a regression, so coercion is the
object's job rather than each caller's.
"""

from typing import Union

# Returned by the UID reads when the read could not be completed. Deliberately not a value any
# assertion accepts, and deliberately distinguishable from a changed identity: a failed read must
# not be mistaken for a pod that was replaced.
UID_UNREADABLE = ""
# Returned by the generation reads when the read could not be completed, or when the value could
# not be parsed. Real generations start at 1, so a negative value cannot compare as advanced.
GENERATION_UNREADABLE = -1
# Returned by the container-count reads on the same terms. Real counts are zero or more, so a
# negative value is distinguishable from a pod that genuinely reports no containers.
COUNT_UNREADABLE = -1
# Returned by the environment read when the variable is absent or the read failed. The phase values
# the check writes are always non-empty, so an empty string cannot be mistaken for a real value.
ENV_VALUE_UNREADABLE = ""


def coerce_int(raw: Union[str, int, None], sentinel: int) -> int:
    """Return raw as an int, or the sentinel when it cannot be read as one.

    The cluster reads arrive as jsonpath strings and can be empty when the field is absent. A
    string comparison would make generation "9" greater than "10", so every numeric field is
    coerced here rather than trusted. A value that cannot be parsed is not an error to raise: the
    readers sit inside a retry wrapper that retries values, not exceptions.

    Args:
        raw (Union[str, int, None]): the value as read, which may be None, empty or non-numeric.
        sentinel (int): the value to return when raw cannot be read as an int.

    Returns:
        int: the parsed integer, or the sentinel.
    """
    try:
        return int(str(raw))
    except ValueError:
        # One path covers every unreadable shape: None, empty, whitespace-only, booleans and
        # genuinely non-numeric text. No explicit branch is needed for any of them, because
        # int(str(x)) raises ValueError for all of them - including bool, once there is no int fast
        # path ahead of this to accept it.
        return sentinel


def parse_ready(raw: Union[str, None]) -> "tuple[int, int]":
    """Return the (ready, total) container counts parsed from a READY column value.

    The cluster and the framework both yield this as one string, "1/1", so it is parsed here rather
    than split by each caller. Two reasons that matters. The framework has already written this
    parse wrong once - KubectlPodObject.is_ready compares the halves as strings with no zero guard,
    so "0/0" reports ready - and a caller that passes the halves in the wrong order is invisible for
    "1/1", which is the steady state of a single-replica probe.

    Unreadable and not-ready are kept distinct, which is why this returns counts rather than a bool:
    a failed read must keep a retry window going, while a genuine not-ready must be able to fail.

    Args:
        raw (Union[str, None]): the READY column value, such as "2/2", or None when unread.

    Returns:
        tuple[int, int]: the ready and total counts, or COUNT_UNREADABLE for both when unparseable.
    """
    ready_text, _, total_text = str(raw).partition("/")
    ready = coerce_int(ready_text, COUNT_UNREADABLE)
    total = coerce_int(total_text, COUNT_UNREADABLE)
    if ready == COUNT_UNREADABLE or total == COUNT_UNREADABLE:
        # Either half unreadable makes both unreadable: a half-read count supports no conclusion.
        # None and a missing separator need no guard of their own: both make coerce_int return the
        # sentinel, which this branch already catches.
        return COUNT_UNREADABLE, COUNT_UNREADABLE
    return ready, total


class WorkloadSnapshot:
    """What was true of one workload and its current pod at a single instant.

    Used for both the annotated probe and the unannotated control, so the control is held to the
    same readability and readiness standard as the probe. Exposes typed getters rather than fields,
    as the framework requires.
    """

    def __init__(
        self,
        uid: Union[str, None],
        generation: Union[str, int, None],
        observed_generation: Union[str, int, None],
        ready: Union[str, None],
    ):
        """Store one workload's reads, parsing the READY string and coercing the generations.

        Args:
            uid (Union[str, None]): the current pod's UID, or None when the read failed.
            generation (Union[str, int, None]): the workload's metadata generation, as read.
            observed_generation (Union[str, int, None]): the workload's observed generation, as read.
            ready (Union[str, None]): the pod's READY column value, such as "2/2", or None.
        """
        self.uid = uid if uid is not None else UID_UNREADABLE
        self.generation = coerce_int(generation, GENERATION_UNREADABLE)
        self.observed_generation = coerce_int(observed_generation, GENERATION_UNREADABLE)
        self.ready_containers, self.total_containers = parse_ready(ready)

    def get_uid(self) -> str:
        """Return the current pod's UID.

        Returns:
            str: the pod UID, or UID_UNREADABLE when the read failed.
        """
        return self.uid

    def get_generation(self) -> int:
        """Return the workload's metadata generation.

        Returns:
            int: the generation, or GENERATION_UNREADABLE when unread or unparseable.
        """
        return self.generation

    def get_observed_generation(self) -> int:
        """Return the workload's observed generation.

        Returns:
            int: the observed generation, or GENERATION_UNREADABLE when unread or unparseable.
        """
        return self.observed_generation

    def get_ready_containers(self) -> int:
        """Return the ready container count in the current pod.

        Returns:
            int: the ready count, or COUNT_UNREADABLE when unread or unparseable.
        """
        return self.ready_containers

    def get_total_containers(self) -> int:
        """Return the total container count in the current pod.

        Returns:
            int: the total count, or COUNT_UNREADABLE when unread or unparseable.
        """
        return self.total_containers

    def is_readable(self) -> bool:
        """Return whether every read for this workload completed.

        A snapshot carrying a sentinel supports no conclusion in either direction: an unreadable UID
        is not evidence of a replaced pod, and an unreadable generation is not evidence of an
        unmoved workload. Both failure modes matter, because the probe is asserted to have moved and
        the control is asserted not to have.

        Returns:
            bool: True when no read for this workload returned its sentinel.
        """
        return self.uid != UID_UNREADABLE and self.generation != GENERATION_UNREADABLE and self.observed_generation != GENERATION_UNREADABLE and self.ready_containers != COUNT_UNREADABLE and self.total_containers != COUNT_UNREADABLE

    def is_ready(self) -> bool:
        """Return whether every container in the current pod is ready.

        Ready is compared against total rather than against an expected count, because deriving an
        expected container count is what made an earlier sibling check fail every phase on a healthy
        system. Zero of zero is not readiness: a pod reporting no containers has not come up.

        Returns:
            bool: True when there is at least one container and all of them are ready.
        """
        return self.total_containers > 0 and self.ready_containers == self.total_containers

    def has_rolled_from(self, baseline: "WorkloadSnapshot") -> bool:
        """Return whether this workload was re-templated and the controller acted on it.

        Args:
            baseline (WorkloadSnapshot): the snapshot taken before the watched change.

        Returns:
            bool: True when the pod identity changed, the generation advanced and was observed.

        Note:
            observedGeneration is compared for equality, not with >=. Kubernetes never reports it
            ahead of generation, so the two differ only while a rollout is in flight; equality is
            therefore the precise statement that the controller has caught up. A >= variant is
            behaviourally identical and no test can separate them.
        """
        return self.uid != baseline.uid and self.generation > baseline.generation and self.observed_generation == self.generation

    def is_unmoved_from(self, baseline: "WorkloadSnapshot") -> bool:
        """Return whether this workload is untouched since the baseline.

        Identity as well as generation, because a pod can be replaced without the workload being
        re-templated - a node eviction, a manual delete or a ReplicaSet-level recreate all leave the
        generation where it was. The control exists to prove reloader acted on the annotated
        workload only, and a control whose pod was replaced by anything cannot support that.

        Args:
            baseline (WorkloadSnapshot): the snapshot taken before the watched change.

        Returns:
            bool: True when both the pod identity and the generation are unchanged.
        """
        return self.uid == baseline.uid and self.generation == baseline.generation

    def __str__(self) -> str:
        """Return a human-readable snapshot for logging.

        Returns:
            str: every fact this workload snapshot carries, on one line.
        """
        return f"WorkloadSnapshot(uid={self.uid!r}, generation={self.generation}, observed_generation={self.observed_generation}, ready={self.ready_containers}/{self.total_containers})"
