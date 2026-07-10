"""Output parser for Heat stack SDK responses."""

from typing import List

from keywords.openstack.resources.orchestration.object.heat_stack_object import HeatStackObject


class HeatStackOutput:
    """Parses OpenStack SDK stack dicts into HeatStackObject instances."""

    def __init__(self, raw_stacks: List[dict]):
        """Initialize and parse stack dicts.

        Args:
            raw_stacks (List[dict]): List of stack dicts from SDK to_dict().
        """
        self.stacks: List[HeatStackObject] = []
        for raw in raw_stacks:
            stack = HeatStackObject()
            stack.set_id(raw.get("id", ""))
            stack.set_name(raw.get("name", ""))
            stack.set_status(raw.get("status", ""))
            stack.set_status_reason(raw.get("status_reason"))
            stack.set_description(raw.get("description"))
            stack.set_creation_time(raw.get("creation_time"))
            stack.set_updated_time(raw.get("updated_time"))
            stack.set_deletion_time(raw.get("deletion_time"))
            self.stacks.append(stack)

    def get_stacks(self) -> List[HeatStackObject]:
        """Get the list of parsed stacks.

        Returns:
            List[HeatStackObject]: List of stack objects.
        """
        return self.stacks

    def get_stack(self) -> HeatStackObject:
        """Get the single stack from a show/get response.

        Returns:
            HeatStackObject: The stack object.

        Raises:
            ValueError: If output contains no stacks.
        """
        if not self.stacks:
            raise ValueError("No stack found in output")
        return self.stacks[0]

    def get_stack_by_name(self, name: str) -> HeatStackObject:
        """Get a stack by name.

        Args:
            name (str): Stack name.

        Returns:
            HeatStackObject: Matching stack.

        Raises:
            ValueError: If no stack with that name is found.
        """
        for stack in self.stacks:
            if stack.get_name() == name:
                return stack
        raise ValueError(f"Stack '{name}' not found")

    def get_stack_by_id(self, stack_id: str) -> HeatStackObject:
        """Get a stack by ID.

        Args:
            stack_id (str): Stack ID.

        Returns:
            HeatStackObject: Matching stack.

        Raises:
            ValueError: If no stack with that ID is found.
        """
        for stack in self.stacks:
            if stack.get_id() == stack_id:
                return stack
        raise ValueError(f"Stack with ID '{stack_id}' not found")

    def is_empty(self) -> bool:
        """Check if the output contains no stacks.

        Returns:
            bool: True if no stacks in output.
        """
        return len(self.stacks) == 0
