"""Database schema definitions for component library and projects."""

# SQL schema for SQLite database

SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- Component library tables

CREATE TABLE IF NOT EXISTS component_library (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    subcategory TEXT,
    name TEXT NOT NULL,
    designation_prefix TEXT,
    component_type TEXT NOT NULL,
    default_voltage TEXT,
    description TEXT,
    manufacturer TEXT,
    part_number TEXT,
    datasheet_url TEXT,
    image_path TEXT,
    symbol_svg TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS component_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id INTEGER NOT NULL,
    spec_name TEXT NOT NULL,
    spec_value TEXT NOT NULL,
    unit TEXT,
    FOREIGN KEY (component_id) REFERENCES component_library(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS component_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id INTEGER NOT NULL,
    image_type TEXT NOT NULL,
    image_data BLOB,
    image_format TEXT,
    width INTEGER,
    height INTEGER,
    FOREIGN KEY (component_id) REFERENCES component_library(id) ON DELETE CASCADE
);

-- Project and diagram tables

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    pdf_path TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS diagram_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    component_library_id INTEGER,
    designation TEXT NOT NULL,
    component_type TEXT NOT NULL,
    description TEXT,
    voltage_rating TEXT,
    x REAL NOT NULL,
    y REAL NOT NULL,
    width REAL NOT NULL,
    height REAL NOT NULL,
    page_number INTEGER DEFAULT 0,
    state TEXT DEFAULT 'UNKNOWN',
    normally_open INTEGER DEFAULT 1,
    metadata TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (component_library_id) REFERENCES component_library(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS diagram_wires (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    wire_number TEXT,
    voltage_level TEXT,
    color TEXT,
    wire_type TEXT,
    from_component_id INTEGER,
    from_terminal TEXT,
    to_component_id INTEGER,
    to_terminal TEXT,
    path_json TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (from_component_id) REFERENCES diagram_components(id) ON DELETE SET NULL,
    FOREIGN KEY (to_component_id) REFERENCES diagram_components(id) ON DELETE SET NULL
);

-- Indexes for performance

CREATE INDEX IF NOT EXISTS idx_component_library_category ON component_library(category);
CREATE INDEX IF NOT EXISTS idx_component_library_type ON component_library(component_type);
CREATE INDEX IF NOT EXISTS idx_component_library_part ON component_library(part_number);
CREATE INDEX IF NOT EXISTS idx_diagram_components_project ON diagram_components(project_id);
CREATE INDEX IF NOT EXISTS idx_diagram_wires_project ON diagram_wires(project_id);
CREATE INDEX IF NOT EXISTS idx_component_specs_component ON component_specs(component_id);
CREATE INDEX IF NOT EXISTS idx_component_images_component ON component_images(component_id);

-- Schema version tracking

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_schema_version_sql() -> str:
    """Get SQL to insert current schema version."""
    return f"INSERT OR REPLACE INTO schema_version (version) VALUES ({SCHEMA_VERSION});"
