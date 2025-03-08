"""
Module pertaining to documents
"""

from holdings.models import HoldingAccountDocument


class DocumentParser:
    """
    Parser for holding account documents.
    """

    document: HoldingAccountDocument
    _contents: str | None
    _lines: list[str] | None

    def __init__(self, document: HoldingAccountDocument) -> None:
        self.document = document
        self._contents = None
        self._lines = None

    @property
    def contents(self) -> str:
        """
        The raw contents of the document.
        """
        if self._contents is not None:
            return self._contents

        with self.document.document.open() as fobj:
            self._contents = fobj.read().decode()

        assert self._contents is not None
        return self._contents

    @property
    def lines(self) -> list[str]:
        """
        ``list`` of lines represented by the file.
        """
        if self._lines is not None:
            return self._lines

        self._lines = self.contents.splitlines()
        assert self._lines is not None
        return self._lines

    def find_line(self, startswith: str | None = None, start: int = 0) -> int:
        """
        Find the line that starts with the given *startswith* ``str`` from the
        given *start* index.
        """
        for i, line in enumerate(self.lines[start:]):
            if startswith is None:
                if not line:
                    return i + start

                continue

            if line.startswith(startswith):
                return i + start

        raise AssertionError(f"Not found: {startswith}")

    def lines_between(self, begin: str, end: str | None = None) -> list[str]:
        """
        Return the lines between the given *begin* and *end* strings.
        """
        start_idx = self.find_line(begin)
        end_idx = self.find_line(end, start_idx)
        return self.lines[start_idx:end_idx]
