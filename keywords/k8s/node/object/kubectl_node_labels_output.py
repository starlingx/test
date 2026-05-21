from typing import Dict, List


class KubectlNodeLabelsOutput:
    """Output object for node labels from 'kubectl get node <name> -o json'."""

    def __init__(self, labels: Dict[str, str]):
        """Constructor.

        Args:
            labels (Dict[str, str]): Dictionary of label key-value pairs.
        """
        self._labels = labels

    def get_labels(self) -> Dict[str, str]:
        """Returns all labels as a dictionary.

        Returns:
            Dict[str, str]: All label key-value pairs.
        """
        return self._labels

    def get_keys(self) -> List[str]:
        """Returns all label keys.

        Returns:
            List[str]: List of label keys.
        """
        return list(self._labels.keys())

    def get_keys_by_prefix(self, prefix: str) -> List[str]:
        """Returns label keys that contain the given prefix.

        Args:
            prefix (str): Substring to filter label keys by.

        Returns:
            List[str]: List of matching label keys.
        """
        return [k for k in self._labels if prefix in k]

    def get_value(self, key: str) -> str:
        """Returns the value for a specific label key.

        Args:
            key (str): Label key.

        Returns:
            str: Label value, or None if key not found.
        """
        return self._labels.get(key)

    def get_count(self) -> int:
        """Returns the total number of labels.

        Returns:
            int: Label count.
        """
        return len(self._labels)

    def get_count_by_prefix(self, prefix: str) -> int:
        """Returns the count of labels matching a prefix.

        Args:
            prefix (str): Substring to filter label keys by.

        Returns:
            int: Count of matching labels.
        """
        return len(self.get_keys_by_prefix(prefix))
