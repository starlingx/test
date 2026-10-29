"""A phase of a DC operation, bounded by a start and stop log marker."""


class KpiLogPhase:
    """One phase of a DC operation, bounded by a start and stop log marker.

    Attributes:
        name (str): Phase name (becomes the KPI name suffix).
        start_log (str): Logical log holding the start marker ('dcmanager'/'state').
        start_marker (str): Substring that marks the phase start.
        stop_log (str): Logical log holding the stop marker.
        stop_marker (str): Substring that marks the phase stop.
        start_pick (str): 'first' or 'last' occurrence to anchor the start on.
        stop_pick (str): 'first' or 'last' occurrence to anchor the stop on.
    """

    def __init__(self, name: str, start_log: str, start_marker: str, stop_log: str, stop_marker: str, start_pick: str = "last", stop_pick: str = "last"):
        """Initialize a KpiLogPhase.

        Args:
            name (str): Phase name.
            start_log (str): Logical log for the start marker.
            start_marker (str): Start marker substring.
            stop_log (str): Logical log for the stop marker.
            stop_marker (str): Stop marker substring.
            start_pick (str): 'first' or 'last'. Defaults to 'last'.
            stop_pick (str): 'first' or 'last'. Defaults to 'last'.
        """
        self.name = name
        self.start_log = start_log
        self.start_marker = start_marker
        self.stop_log = stop_log
        self.stop_marker = stop_marker
        self.start_pick = start_pick
        self.stop_pick = stop_pick
