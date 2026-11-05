import re


class HeadFilesOutput:
    """Parses multi-file ``head -v`` output into a path-to-content mapping.

    ``head -v`` prints a ``==> <path> <==`` header before each file it reads,
    so the contents of many small files can be returned by one command.

    ``head`` diagnostics (``head: ...``) are expected in the output when it is
    run with ``2>&1``. A file that does not exist is ignored, because patterns
    that match nothing are normal on heterogeneous hardware. Any other
    diagnostic, such as a permission failure, is kept in :meth:`get_errors`.
    """

    DIAGNOSTIC_PREFIX = "head: "
    MISSING_FILE_MESSAGE = "No such file or directory"

    HEADER_PATTERN = re.compile(r"==> (/.+) <==")

    def __init__(self, head_output: str | list[str]):
        """Constructor.

        Args:
            head_output (str | list[str]): Raw ``head -v`` output.
        """
        text = "".join(head_output) if isinstance(head_output, list) else head_output
        self.file_contents = {}
        self.errors = []
        current_path = None
        current_lines = []
        for line in text.splitlines():
            if line.startswith(self.DIAGNOSTIC_PREFIX):
                if self.MISSING_FILE_MESSAGE not in line:
                    self.errors.append(line)
                continue
            match = self.HEADER_PATTERN.fullmatch(line)
            if match:
                if current_path is not None:
                    self.file_contents[current_path] = "\n".join(current_lines).strip()
                current_path = match.group(1)
                current_lines = []
            elif current_path is not None:
                current_lines.append(line)
        if current_path is not None:
            self.file_contents[current_path] = "\n".join(current_lines).strip()

    def get_errors(self) -> list[str]:
        """Get the ``head`` diagnostics other than missing files.

        Returns:
            list[str]: Diagnostic lines such as permission failures; empty if none.
        """
        return self.errors

    def get_file_contents(self) -> dict[str, str]:
        """Get the contents of every file that was read.

        Returns:
            dict[str, str]: Mapping of file path to stripped file contents.
        """
        return self.file_contents

    def has_file(self, file_path: str) -> bool:
        """Check whether a file was read.

        Args:
            file_path (str): Absolute file path.

        Returns:
            bool: True if the output contains the file, otherwise False.
        """
        return file_path in self.file_contents

    def get_file_content(self, file_path: str) -> str:
        """Get the contents of one file.

        Args:
            file_path (str): Absolute file path.

        Returns:
            str: Stripped file contents.

        Raises:
            KeyError: If the file is not in the output.
        """
        if not self.has_file(file_path):
            raise KeyError(f"File '{file_path}' was not read")
        return self.file_contents[file_path]
