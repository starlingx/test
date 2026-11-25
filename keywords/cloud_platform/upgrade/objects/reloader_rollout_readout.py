"""Snapshots of the reloader probe and its negative control, taken at one instant.

The reload check has several facts to establish and they are only meaningful together. A rollout in
flight exposes the new pod's identity before it is ready, and readiness before its environment can
be read, so independent waits can each pass without any single instant having satisfied all of
them. Reading them into one object, then deciding once, removes that whole class of flake. The object is
not literally atomic - building one costs several kubectl round-trips - so the guarantee comes from
the retry window reading a fresh snapshot each poll until one of them satisfies everything.

Note that validate_equals_with_retry raises TimeoutError when the window expires, so assertions
placed after it never run on a failing system. The caller must therefore log str() of each snapshot
as it polls, or a failure arrives as a bare timeout with nothing to diagnose.

Two types rather than one flat record: a WorkloadSnapshot (workload_snapshot.py) carries what is true of one workload, and
the readout pairs the annotated probe with the unannotated control. That split is what lets the
control be held to the same readability and readiness standard as the probe, which a flat record
quietly failed to do.
"""

from typing import Union

from keywords.cloud_platform.upgrade.objects.workload_snapshot import ENV_VALUE_UNREADABLE, WorkloadSnapshot


class ReloaderRolloutReadout:
    """One settled snapshot of the annotated probe and its unannotated negative control.

    The probe is expected to roll and carry the changed value. The control consumes its own
    ConfigMap and Secret and carries no reloader annotation, so it is expected not to move at all: a
    reloader that rolls it has ignored annotations entirely, and anything other than reloader rolling
    both workloads would otherwise satisfy every probe-side assertion.
    """

    def __init__(self, probe: WorkloadSnapshot, control: WorkloadSnapshot, env_value: Union[str, None]):
        """Store one paired snapshot.

        Args:
            probe (WorkloadSnapshot): the annotated probe workload.
            control (WorkloadSnapshot): the unannotated negative control workload.
            env_value (Union[str, None]): the value the probe pod's environment holds, or
                ENV_VALUE_UNREADABLE when absent or unreadable.
        """
        self.probe = probe
        self.control = control
        self.env_value = env_value if env_value is not None else ENV_VALUE_UNREADABLE

    def get_probe(self) -> WorkloadSnapshot:
        """Return the probe workload snapshot.

        Returns:
            WorkloadSnapshot: the annotated probe.
        """
        return self.probe

    def get_control(self) -> WorkloadSnapshot:
        """Return the negative control workload snapshot.

        Returns:
            WorkloadSnapshot: the unannotated control.
        """
        return self.control

    def get_env_value(self) -> str:
        """Return the value the probe pod's environment holds.

        Returns:
            str: the value, or ENV_VALUE_UNREADABLE when absent or unreadable.
        """
        return self.env_value

    def is_readable(self) -> bool:
        """Return whether every read in this paired snapshot completed.

        Returns:
            bool: True when both workloads are fully readable and the environment was read.
        """
        return self.probe.is_readable() and self.control.is_readable() and self.env_value != ENV_VALUE_UNREADABLE

    def is_rolled_from(self, baseline: "ReloaderRolloutReadout", expected_env_value: str) -> bool:
        """Return whether the probe rolled and delivered, and the control did not move.

        Every condition is evaluated against this one snapshot, and against a baseline that must
        itself be fully readable - a sentinel-bearing baseline would otherwise make the comparison
        strictly more permissive rather than failing:
            both snapshots are fully readable;
            the probe was re-templated, the controller acted, and its new pod is ready;
            the probe's new pod holds the value written for this phase;
            the control is unmoved in both identity and generation, and is still ready.

        The control's readiness is asserted because a control that died is trivially unmoved, and
        would satisfy the comparison while proving nothing.

        An empty expected_env_value needs no guard here: an unreadable environment is refused by
        is_readable(), and a readable one cannot equal the empty string, so no input could reach a
        guard for it. The keyword generates the phase value and asserts it is non-empty there, where
        the assertion is reachable and testable.

        Args:
            baseline (ReloaderRolloutReadout): the snapshot taken before the watched change.
            expected_env_value (str): the value written to the watched resource for this phase.

        Returns:
            bool: True when the probe rolled and delivered and the control stayed put.
        """
        if not self.is_readable() or not baseline.is_readable():
            return False
        probe_delivered = self.probe.has_rolled_from(baseline.probe) and self.probe.is_ready() and self.env_value == expected_env_value
        control_held = self.control.is_unmoved_from(baseline.control) and self.control.is_ready()
        return probe_delivered and control_held

    def __str__(self) -> str:
        """Return a human-readable snapshot for logging.

        Returns:
            str: both workload snapshots and the observed environment value, on one line.
        """
        return f"ReloaderRolloutReadout(probe={self.probe}, control={self.control}, env_value={self.env_value!r})"
