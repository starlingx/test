class KubernetesVersionListObject:
    """KubernetesVersionListObject.

    This class represents a kube-version-list summary as an object.
    This is typically a line in the 'dcmanager kube-version-list' command output table, as shown below.

    +---------+--------+-------------+
    | version | target | state       |
    +---------+--------+-------------+
    | v1.29.2 | False  | unavailable |
    | v1.30.6 | False  | unavailable |
    | v1.31.5 | False  | unavailable |
    | v1.32.2 | True   | active      |
    | v1.33.0 | False  | available   |
    +---------+--------+-------------+

    """

    def __init__(self, version: str, target: bool, state: str):
        """
        Constructor

        Args:
            version (str): kubernetes version.
            target (bool): kubernetes target version.
            state (str): kubernetes version state.

        """
        self.version = version
        self.target = target
        self.state = state

    def get_version(self) -> str:
        """
        Getter for kubernetes version
        """
        return self.version

    def get_state(self):
        """
        Getter for kubernetes state
        """
        return self.state
