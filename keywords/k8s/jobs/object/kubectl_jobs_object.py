from typing import Optional


class KubectlJobObject:
    """Represents a Kubernetes job."""

    def __init__(self, name: str) -> None:
        """Instantiate a KubectlJobObject.

        Args:
            name (str): The name of the job.
        """
        self.name = name
        self.status: Optional[str] = None
        self.completions: Optional[str] = None
        self.duration: Optional[str] = None
        self.age: Optional[str] = None

    def set_status(self, status: str) -> None:
        """Set the STATUS entry.

        Args:
            status (str): The status of the job.
        """
        self.status = status

    def get_status(self) -> Optional[str]:
        """Get the STATUS entry.

        Returns:
            Optional[str]: The status of the job.
        """
        return self.status

    def set_completions(self, completions: str) -> None:
        """Set the COMPLETIONS entry.

        Args:
            completions (str): The completions of the job (e.g. '1/1').
        """
        self.completions = completions

    def get_completions(self) -> Optional[str]:
        """Get the COMPLETIONS entry.

        Returns:
            Optional[str]: The completions of the job (e.g. '1/1').
        """
        return self.completions

    def set_duration(self, duration: str) -> None:
        """Set the DURATION entry.

        Args:
            duration (str): The duration of the job.
        """
        self.duration = duration

    def get_duration(self) -> Optional[str]:
        """Get the DURATION entry.

        Returns:
            Optional[str]: The duration of the job.
        """
        return self.duration

    def set_age(self, age: str) -> None:
        """Set the AGE entry.

        Args:
            age (str): The age of the job.
        """
        self.age = age

    def get_age(self) -> Optional[str]:
        """Get the AGE entry.

        Returns:
            Optional[str]: The age of the job.
        """
        return self.age

    def get_name(self) -> str:
        """Get the NAME entry.

        Returns:
            str: The name of the job.
        """
        return self.name

    def is_completed(self) -> bool:
        """Check whether the job completed all of its requested completions.

        A job's COMPLETIONS column renders as 'succeeded/desired' (e.g. '1/1').
        The job is complete when both sides are equal and non-zero.

        Returns:
            bool: True if the job reports all completions succeeded.
        """
        if not self.completions:
            return False
        succeeded, _, desired = self.completions.partition("/")
        return succeeded != "" and succeeded == desired

    def __repr__(self) -> str:
        """Return a string representation of the job object.

        Returns:
            str: Human-readable representation.
        """
        return f"<KubectlJobObject name={self.name} status={self.status} completions={self.completions} duration={self.duration} age={self.age}>"
