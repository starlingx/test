class LsmodObject:
    """
    Simple data object representing a single lsmod entry.

    Fields:
        - name: module name
        - size: integer size
        - used: number of references
        - used_by_raw: comma-separated string of dependencies
    """

    def __init__(self) -> None:
        self._name: str | None = None
        self._size: int | None = None
        self._used: int | None = None
        self._used_by_raw: str | None = None

    def set_name(self, value: str) -> None:
        self._name = value

    def set_size(self, value: int) -> None:
        self._size = int(value)

    def set_used(self, value: int) -> None:
        self._used = int(value)

    def set_used_by_raw(self, value: str) -> None:
        self._used_by_raw = value or ""

    def get_name(self) -> str:
        return self._name

    def get_size(self) -> int:
        return self._size

    def get_used(self) -> int:
        return self._used

    def get_used_by_raw(self) -> str:
        return self._used_by_raw or ""

    def get_used_by(self) -> tuple[str, ...]:
        """
        Return a tuple of dependent modules parsed from the raw field.
        """
        raw = self.get_used_by_raw()
        if not raw:
            return tuple()
        return tuple(item.strip() for item in raw.split(",") if item.strip())
