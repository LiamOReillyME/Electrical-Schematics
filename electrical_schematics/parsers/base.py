"""Base parser interface for schematic file formats."""

from abc import ABC, abstractmethod
from pathlib import Path
from electrical_schematics.models import Schematic


class SchematicParser(ABC):
    """Abstract base class for schematic parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> Schematic:
        """
        Parse a schematic file.

        Args:
            file_path: Path to the schematic file

        Returns:
            Parsed Schematic object

        Raises:
            ValueError: If file format is invalid
            FileNotFoundError: If file doesn't exist
        """
        pass

    @abstractmethod
    def can_parse(self, file_path: Path) -> bool:
        """
        Check if this parser can handle the given file.

        Args:
            file_path: Path to check

        Returns:
            True if this parser can handle the file
        """
        pass
