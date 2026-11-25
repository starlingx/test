"""Unit tests for the reloader rollout readout.

The readout is one settled snapshot of everything the reload check decides on, so the facts are
asserted against a single instant rather than drifting across independent reads. A rollout in
flight exposes the new pod's identity before it is ready, and readiness before its environment can
be read, so reads taken at different moments can each pass while no instant ever satisfied all of
them together.

Every negative case below changes exactly one field. That matters more than it looks: a case that
changes three fields at once fails for three reasons, so it isolates none of them, and any clause of
the predicate it does not pin can be deleted with the suite still green. A case that fails for three
reasons pins none of them.

The comparison is expressed between two instances of the same type - a baseline snapshot and an
after snapshot - because that is what the phases actually produce, and nothing can be satisfied by
a value the object was told to expect.

Pure data: no SSH, no cluster, no mocking. The cluster-facing behaviour is covered in the keyword
tests.
"""

import unittest

from keywords.cloud_platform.upgrade.objects.reloader_rollout_readout import ReloaderRolloutReadout
from keywords.cloud_platform.upgrade.objects.workload_snapshot import COUNT_UNREADABLE, ENV_VALUE_UNREADABLE, GENERATION_UNREADABLE, UID_UNREADABLE, WorkloadSnapshot, coerce_int, parse_ready

NEW_VALUE = "phase-pre-7f3a1c"
OLD_VALUE = "phase-pre-0000aa"


def probe(uid: str = "probe-after", generation: object = 2, observed_generation: object = 2, ready: str = "1/1") -> WorkloadSnapshot:
    """Return a probe snapshot that has rolled relative to the baseline, unless overridden.

    Args:
        uid (str): the probe pod's UID.
        generation (object): the workload's metadata generation.
        observed_generation (object): the workload's observed generation.
        ready (str): the pod's READY column value.

    Returns:
        WorkloadSnapshot: the described probe snapshot.
    """
    return WorkloadSnapshot(uid, generation, observed_generation, ready)


def control(uid: str = "control-uid", generation: object = 1, observed_generation: object = 1, ready: str = "1/1") -> WorkloadSnapshot:
    """Return a control snapshot that is unmoved relative to the baseline, unless overridden.

    Args:
        uid (str): the control pod's UID.
        generation (object): the workload's metadata generation.
        observed_generation (object): the workload's observed generation.
        ready (str): the pod's READY column value.

    Returns:
        WorkloadSnapshot: the described control snapshot.
    """
    return WorkloadSnapshot(uid, generation, observed_generation, ready)


def readout(probe_snapshot: WorkloadSnapshot = None, control_snapshot: WorkloadSnapshot = None, env_value: str = NEW_VALUE) -> ReloaderRolloutReadout:
    """Return an after-snapshot that is fully rolled relative to baseline(), unless overridden.

    Args:
        probe_snapshot (WorkloadSnapshot): the probe snapshot, defaulting to a rolled probe.
        control_snapshot (WorkloadSnapshot): the control snapshot, defaulting to an unmoved control.
        env_value (str): the value the probe pod's environment holds.

    Returns:
        ReloaderRolloutReadout: the described paired snapshot.
    """
    return ReloaderRolloutReadout(probe_snapshot or probe(), control_snapshot or control(), env_value)


def baseline() -> ReloaderRolloutReadout:
    """Return the paired snapshot taken before the watched resource was changed.

    Returns:
        ReloaderRolloutReadout: the baseline snapshot.
    """
    return ReloaderRolloutReadout(probe(uid="probe-baseline", generation=1, observed_generation=1), control(), OLD_VALUE)


class TestCoerceInt(unittest.TestCase):
    """Cases for the numeric coercion the cluster reads depend on."""

    def test_numeric_strings_compare_as_numbers(self):
        """The reads arrive as strings, and "9" > "10" as text. Generation 9 to 10 must be a roll."""
        self.assertTrue(coerce_int("10", GENERATION_UNREADABLE) > coerce_int("9", GENERATION_UNREADABLE))

    def test_ints_pass_through(self):
        """A caller that already has an int is not penalised for it."""
        self.assertEqual(coerce_int(7, GENERATION_UNREADABLE), 7)

    def test_none_is_the_sentinel(self):
        """An absent field reads as None and must not become 0."""
        self.assertEqual(coerce_int(None, GENERATION_UNREADABLE), GENERATION_UNREADABLE)

    def test_empty_string_is_the_sentinel(self):
        """kubectl returns an empty string with status 0 for an absent jsonpath key."""
        self.assertEqual(coerce_int("", GENERATION_UNREADABLE), GENERATION_UNREADABLE)
        self.assertEqual(coerce_int("   ", GENERATION_UNREADABLE), GENERATION_UNREADABLE)

    def test_non_numeric_is_the_sentinel(self):
        """An error string in place of a value must not raise: the caller is a retry wrapper."""
        self.assertEqual(coerce_int("Error from server (NotFound)", COUNT_UNREADABLE), COUNT_UNREADABLE)

    def test_booleans_are_rejected(self):
        """bool is an int subclass, so True would silently coerce to 1 without this."""
        self.assertEqual(coerce_int(True, COUNT_UNREADABLE), COUNT_UNREADABLE)


class TestParseReady(unittest.TestCase):
    """Cases for the READY column parse, which the framework has already got wrong once."""

    def test_parses_the_two_halves(self):
        """The ordinary case, and the one where a hand-rolled parse swaps the halves."""
        self.assertEqual(parse_ready("2/3"), (2, 3))
        self.assertNotEqual(parse_ready("2/3"), parse_ready("3/2"))

    def test_zero_of_zero_parses_rather_than_failing(self):
        """Unreadable and not-ready stay distinct: "0/0" is read, then judged not ready."""
        self.assertEqual(parse_ready("0/0"), (0, 0))
        self.assertFalse(probe(ready="0/0").is_ready())

    def test_unparseable_values_are_sentinels(self):
        """A missing separator, a non-numeric half, an empty string or None are all unreadable."""
        for raw in (None, "", "1", "a/1", "1/a", "/", "Error from server"):
            self.assertEqual(parse_ready(raw), (COUNT_UNREADABLE, COUNT_UNREADABLE), f"raw={raw!r}")


class TestWorkloadSnapshot(unittest.TestCase):
    """Cases for one workload's readability, readiness and movement."""

    def test_ready_only_when_every_container_is_ready(self):
        """Ready is compared against total, never derived from an expected count."""
        self.assertTrue(probe(ready="2/2").is_ready())
        self.assertFalse(probe(ready="1/2").is_ready())

    def test_not_ready_when_there_are_no_containers(self):
        """Zero of zero is not readiness. A pod reporting no containers has not come up."""
        self.assertFalse(probe(ready="0/0").is_ready())

    def test_not_ready_when_the_counts_are_unreadable(self):
        """An unreadable count must not satisfy readiness through sentinel arithmetic."""
        self.assertFalse(probe(ready=None).is_ready())

    def test_readable_requires_every_field(self):
        """Each sentinel independently makes the snapshot unusable."""
        self.assertTrue(probe().is_readable())
        self.assertFalse(probe(uid=UID_UNREADABLE).is_readable())
        self.assertFalse(probe(generation=None).is_readable())
        self.assertFalse(probe(observed_generation=None).is_readable())
        self.assertFalse(probe(ready=None).is_readable())
        self.assertFalse(probe(ready="bad").is_readable())

    def test_unmoved_requires_identity_and_generation(self):
        """A pod replaced without a re-template leaves the generation where it was."""
        self.assertTrue(control().is_unmoved_from(control()))
        self.assertFalse(control(uid="control-new").is_unmoved_from(control()))
        self.assertFalse(control(generation=2).is_unmoved_from(control()))

    def test_str_names_every_fact(self):
        """A failure has to be diagnosable from the log without re-reading the cluster."""
        text = str(probe())
        for expected in ("probe-after", "generation=2", "observed_generation=2", "1/1"):
            self.assertIn(expected, text)


class TestReloaderRolloutReadout(unittest.TestCase):
    """Cases for the paired rollout predicate. Each negative case changes exactly one field."""

    def test_fully_rolled_when_every_fact_holds(self):
        """A re-templated and observed probe, ready, holding the new value, with an unmoved control."""
        self.assertTrue(readout().is_rolled_from(baseline(), NEW_VALUE))

    def test_not_rolled_when_only_the_probe_identity_is_unchanged(self):
        """Isolates the pod-identity clause: everything else holds and only the UID is the old one.

        This is the clause the whole check exists for - the watched resource changed and the pod was
        not replaced - and an over-specified case left it with no test of its own.
        """
        self.assertFalse(readout(probe(uid="probe-baseline")).is_rolled_from(baseline(), NEW_VALUE))

    def test_rolled_when_the_generation_advanced_by_more_than_one(self):
        """The generation is compared for advance, not for an exact increment.

        One apply that changes two watched references draws one patch per reference, so the
        generation can step by more than one. Requiring an increment of exactly one would fail a
        correct rollout, and nothing else in the suite distinguishes the two rules.
        """
        self.assertTrue(readout(probe(generation=3, observed_generation=3)).is_rolled_from(baseline(), NEW_VALUE))

    def test_not_rolled_when_only_the_generation_did_not_advance(self):
        """Isolates the generation clause. A replaced pod alone is a pod that died, not a roll."""
        self.assertFalse(readout(probe(generation=1)).is_rolled_from(baseline(), NEW_VALUE))

    def test_not_rolled_when_only_the_observed_generation_lags(self):
        """Isolates the observed-generation clause. The controller has not acted yet."""
        self.assertFalse(readout(probe(observed_generation=1)).is_rolled_from(baseline(), NEW_VALUE))

    def test_not_rolled_when_only_the_probe_is_not_ready(self):
        """Isolates probe readiness. A rolled workload whose pod never comes up delivered nothing."""
        self.assertFalse(readout(probe(ready="0/1")).is_rolled_from(baseline(), NEW_VALUE))

    def test_not_rolled_when_only_the_value_is_stale(self):
        """Isolates the delivery clause. This is what separates a reload from a restart."""
        self.assertFalse(readout(env_value=OLD_VALUE).is_rolled_from(baseline(), NEW_VALUE))

    def test_not_rolled_when_only_the_control_pod_was_replaced(self):
        """Isolates the control identity clause: its generation holds and only the pod is new.

        A node eviction, a manual delete or a ReplicaSet recreate all look like this. The control
        exists to prove reloader acted on the annotated workload only, and a control whose pod was
        replaced by anything cannot support that.
        """
        self.assertFalse(readout(control_snapshot=control(uid="control-new")).is_rolled_from(baseline(), NEW_VALUE))

    def test_not_rolled_when_only_the_control_generation_advanced(self):
        """Isolates the control generation clause. An annotation-blind reloader re-templates both."""
        self.assertFalse(readout(control_snapshot=control(generation=2)).is_rolled_from(baseline(), NEW_VALUE))

    def test_not_rolled_when_only_the_control_is_not_ready(self):
        """Isolates control readiness. A control that died is trivially unmoved and proves nothing."""
        self.assertFalse(readout(control_snapshot=control(ready="0/1")).is_rolled_from(baseline(), NEW_VALUE))

    def test_not_rolled_when_any_probe_read_failed(self):
        """A failed read is not evidence of a replaced pod, in either direction."""
        self.assertFalse(readout(probe(uid=UID_UNREADABLE)).is_rolled_from(baseline(), NEW_VALUE))
        self.assertFalse(readout(probe(generation=None)).is_rolled_from(baseline(), NEW_VALUE))
        self.assertFalse(readout(probe(ready=None)).is_rolled_from(baseline(), NEW_VALUE))

    def test_not_rolled_when_any_control_read_failed(self):
        """An unreadable control cannot be asserted as unmoved."""
        self.assertFalse(readout(control_snapshot=control(uid=UID_UNREADABLE)).is_rolled_from(baseline(), NEW_VALUE))
        self.assertFalse(readout(control_snapshot=control(generation=None)).is_rolled_from(baseline(), NEW_VALUE))
        self.assertFalse(readout(control_snapshot=control(ready=None)).is_rolled_from(baseline(), NEW_VALUE))

    def test_not_rolled_when_the_environment_is_unreadable(self):
        """An absent variable reads as the sentinel and must not satisfy the value assertion."""
        self.assertFalse(readout(env_value=ENV_VALUE_UNREADABLE).is_rolled_from(baseline(), NEW_VALUE))
        self.assertFalse(readout(env_value=None).is_rolled_from(baseline(), NEW_VALUE))

    def test_not_rolled_when_the_baseline_itself_is_unreadable(self):
        """A sentinel-bearing baseline would make the comparison more permissive, not less.

        An all-sentinel baseline has a UID that differs from any real one and a generation below any
        real one, so every probe-side clause would pass against it.
        """
        unreadable = ReloaderRolloutReadout(probe(uid=UID_UNREADABLE, generation=None, observed_generation=None, ready=None), control(), OLD_VALUE)
        self.assertFalse(readout().is_rolled_from(unreadable, NEW_VALUE))

    def test_not_rolled_when_the_expected_value_is_empty(self):
        """An empty expectation cannot be satisfied: a readable environment never equals "".

        No explicit guard is needed for this, because an unreadable
        environment is refused by is_readable(), and a readable one cannot equal the empty string.
        """
        self.assertFalse(readout().is_rolled_from(baseline(), ""))

    def test_not_rolled_when_the_generation_went_backwards(self):
        """Isolates > rather than != on the generation.

        A workload deleted and recreated comes back at generation 1. Its pod identity is new, so
        with a != comparison a recreated workload would score as a successful reloader roll. Only a
        strictly advancing generation means the existing workload was re-templated.
        """
        older = ReloaderRolloutReadout(probe(uid="probe-baseline", generation=5, observed_generation=5), control(), OLD_VALUE)
        self.assertFalse(readout(probe(generation=1, observed_generation=1)).is_rolled_from(older, NEW_VALUE))

    def test_none_reads_are_normalised_to_sentinels(self):
        """A None from a failed read must become the sentinel, not survive as None.

        Without the normalisation a None uid or environment compares unequal to its sentinel, so the
        snapshot reports itself readable and the predicate proceeds on a value that was never read.
        """
        self.assertFalse(probe(uid=None).is_readable())
        self.assertFalse(readout(env_value=None).is_readable())

    def test_readable_requires_both_workloads_and_the_environment(self):
        """Readability is the precondition for any conclusion, and all three parts are required."""
        self.assertTrue(readout().is_readable())
        self.assertFalse(readout(probe(uid=UID_UNREADABLE)).is_readable())
        self.assertFalse(readout(control_snapshot=control(generation=None)).is_readable())
        self.assertFalse(readout(env_value=ENV_VALUE_UNREADABLE).is_readable())
        self.assertFalse(readout(env_value=None).is_readable())

    def test_str_names_both_workloads_and_the_value(self):
        """One log line has to carry enough to diagnose which side failed."""
        text = str(readout())
        for expected in ("probe-after", "control-uid", NEW_VALUE):
            self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
