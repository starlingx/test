class KubectlHostsObject:
    """
    Represents a Kubernetes CRD object.
    """

    def __init__(self, name: str):
        self.name = name
        self.insync = None
        self.reconcile = None
        

    def set_insync(self, insync: str):
        self.insync = insync

    def get_insync(self) -> str:
        """
        Getter for INSYNC entry
        Returns: The insync status of the CRD object.
        """
        return self.insync

    def set_reconcile(self, reconcile: str):
        self.reconcile = reconcile

    def get_reconcile(self) -> str:
        """
        Getter for RECONCILE entry
        Returns: The reconcile status of the CRD object.
        """
        return self.reconcile

    def get_name(self) -> str:
        """
        Getter for NAME entry
        Returns: The name of the CRD object."""
        return self.name

    def __repr__(self):
        return f"<KubectlCRDObject name={self.name} insync={self.insync} reconcile={self.reconcile}>"