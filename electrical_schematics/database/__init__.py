"""Database module for component library and project persistence."""

from electrical_schematics.database.manager import (
    DatabaseManager,
    ComponentTemplate,
    ComponentSpec,
    ProjectInfo
)
from electrical_schematics.database.populate_defaults import (
    load_default_library,
    initialize_database_with_defaults
)

__all__ = [
    'DatabaseManager',
    'ComponentTemplate',
    'ComponentSpec',
    'ProjectInfo',
    'load_default_library',
    'initialize_database_with_defaults',
]
