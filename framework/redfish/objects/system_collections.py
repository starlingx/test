class SystemCollections:
    """
    Class for SystemCollections
    """

    def __init__(self, context: str, id: str, type: str, description: str, members: list[str], data_count: int, name: str):
        """
        Initializes the SystemCollections object.

        Args:
            context (str): the context
            id (str): the id
            type (str): the type
            description (str): the description
            members (list[str]): the members
            data_count (int): the data count
            name (str): the name
        """
        self.context: str = context
        self.id: str = id
        self.type: str = type
        self.description: str = description
        self.members: list[str] = members
        self.data_count: int = data_count
        self.name: str = name

    def get_context(self) -> str:
        """
        Getter for context

        Returns:
            str: The context

        """
        return self.context

    def get_id(self) -> str:
        """
        Getter for id

        Returns:
            str: The id
        """
        return self.id

    def get_type(self) -> str:
        """
        Getter for type

        Returns:
            str: The type
        """
        return self.type

    def get_description(self) -> str:
        """
        Getter for description

        Returns:
            str: The description
        """
        return self.description

    def get_members(self) -> list[str]:
        """
        Getter for members

        Returns:
            list[str]: The members
        """
        return self.members

    def get_data_count(self) -> int:
        """
        Getter for data_count

        Returns:
            int: the data count
        """
        return self.data_count

    def get_name(self) -> str:
        """
        Getter for name

        Returns:
            str: The name
        """
        return self.name
