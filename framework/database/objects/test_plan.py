class TestPlan:
    """
    Class for test plan
    """

    def __init__(self, test_plan_name: str, description: str, run_type_id: int):
        self.test_plan_name = test_plan_name
        self.description = description
        self.run_type_id = run_type_id
        self.test_plan_id = -1
        self.locked = False

    def get_test_plan_id(self) -> int:
        """
        Getter for test plan id
        Returns: the test plan id

        """
        return self.test_plan_id

    def set_test_plan_id(self, test_plan_id):
        """
        Setter for test plan id
        Args:
            test_plan_id (): the test plan id

        Returns:

        """
        self.test_plan_id = test_plan_id

    def get_test_plan_name(self) -> str:
        """
        Getter for test plan name
        Returns: the test plan name

        """
        return self.test_plan_name

    def get_description(self) -> str:
        """
        Getter for description
        Returns: the description

        """
        return self.description

    def get_run_type_id(self) -> int:
        """
        Getter for run type id
        Returns: the run type id

        """
        return self.run_type_id

    def get_locked(self) -> bool:
        """
        Getter for locked
        Returns: True if locked

        """
        return self.locked

    def set_locked(self, locked: bool):
        """
        Setter for locked
        Args:
            locked (): locked value

        Returns:

        """
        self.locked = locked
