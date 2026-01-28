"""Database manager for component library and projects."""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Any
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from electrical_schematics.database.schema import SCHEMA_SQL, get_schema_version_sql, SCHEMA_VERSION


@dataclass
class ComponentTemplate:
    """Component library template."""
    id: Optional[int]
    category: str
    subcategory: Optional[str]
    name: str
    designation_prefix: Optional[str]
    component_type: str
    default_voltage: Optional[str]
    description: Optional[str]
    manufacturer: Optional[str]
    part_number: Optional[str]
    datasheet_url: Optional[str]
    image_path: Optional[str]
    symbol_svg: Optional[str]


@dataclass
class ComponentSpec:
    """Technical specification for a component."""
    id: Optional[int]
    component_id: int
    spec_name: str
    spec_value: str
    unit: Optional[str]


@dataclass
class ProjectInfo:
    """Project metadata."""
    id: Optional[int]
    name: str
    pdf_path: Optional[str]
    description: Optional[str]
    created_at: Optional[datetime]
    modified_at: Optional[datetime]


class DatabaseManager:
    """Manages SQLite database for component library and projects."""

    def __init__(self, db_path: Path):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Create database and tables if they don't exist."""
        # Create parent directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")

        # Create schema
        self.conn.executescript(SCHEMA_SQL)
        self.conn.execute(get_schema_version_sql())
        self.conn.commit()

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        try:
            yield
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    # Component Library CRUD operations

    def add_component_template(self, template: ComponentTemplate) -> int:
        """Add a new component template to the library.

        Args:
            template: Component template to add

        Returns:
            ID of newly created template
        """
        cursor = self.conn.execute("""
            INSERT INTO component_library (
                category, subcategory, name, designation_prefix, component_type,
                default_voltage, description, manufacturer, part_number,
                datasheet_url, image_path, symbol_svg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template.category,
            template.subcategory,
            template.name,
            template.designation_prefix,
            template.component_type,
            template.default_voltage,
            template.description,
            template.manufacturer,
            template.part_number,
            template.datasheet_url,
            template.image_path,
            template.symbol_svg
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_component_template(self, template_id: int) -> Optional[ComponentTemplate]:
        """Get a component template by ID.

        Args:
            template_id: Template ID

        Returns:
            ComponentTemplate if found, None otherwise
        """
        row = self.conn.execute(
            "SELECT * FROM component_library WHERE id = ?",
            (template_id,)
        ).fetchone()

        if row:
            return ComponentTemplate(
                id=row['id'],
                category=row['category'],
                subcategory=row['subcategory'],
                name=row['name'],
                designation_prefix=row['designation_prefix'],
                component_type=row['component_type'],
                default_voltage=row['default_voltage'],
                description=row['description'],
                manufacturer=row['manufacturer'],
                part_number=row['part_number'],
                datasheet_url=row['datasheet_url'],
                image_path=row['image_path'],
                symbol_svg=row['symbol_svg']
            )
        return None

    def get_component_templates(self, category: Optional[str] = None) -> List[ComponentTemplate]:
        """Get component templates, optionally filtered by category.

        Args:
            category: Category to filter by (None = all)

        Returns:
            List of component templates
        """
        if category:
            rows = self.conn.execute(
                "SELECT * FROM component_library WHERE category = ? ORDER BY name",
                (category,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM component_library ORDER BY category, name"
            ).fetchall()

        return [ComponentTemplate(
            id=row['id'],
            category=row['category'],
            subcategory=row['subcategory'],
            name=row['name'],
            designation_prefix=row['designation_prefix'],
            component_type=row['component_type'],
            default_voltage=row['default_voltage'],
            description=row['description'],
            manufacturer=row['manufacturer'],
            part_number=row['part_number'],
            datasheet_url=row['datasheet_url'],
            image_path=row['image_path'],
            symbol_svg=row['symbol_svg']
        ) for row in rows]

    def search_templates(self, query: str) -> List[ComponentTemplate]:
        """Search component templates by name, manufacturer, or part number.

        Args:
            query: Search query

        Returns:
            List of matching templates
        """
        search_pattern = f"%{query}%"
        rows = self.conn.execute("""
            SELECT * FROM component_library
            WHERE name LIKE ? OR manufacturer LIKE ? OR part_number LIKE ?
            ORDER BY name
        """, (search_pattern, search_pattern, search_pattern)).fetchall()

        return [ComponentTemplate(
            id=row['id'],
            category=row['category'],
            subcategory=row['subcategory'],
            name=row['name'],
            designation_prefix=row['designation_prefix'],
            component_type=row['component_type'],
            default_voltage=row['default_voltage'],
            description=row['description'],
            manufacturer=row['manufacturer'],
            part_number=row['part_number'],
            datasheet_url=row['datasheet_url'],
            image_path=row['image_path'],
            symbol_svg=row['symbol_svg']
        ) for row in rows]

    def update_template(self, template_id: int, template: ComponentTemplate) -> None:
        """Update an existing component template.

        Args:
            template_id: ID of template to update
            template: Updated template data
        """
        self.conn.execute("""
            UPDATE component_library SET
                category = ?, subcategory = ?, name = ?, designation_prefix = ?,
                component_type = ?, default_voltage = ?, description = ?,
                manufacturer = ?, part_number = ?, datasheet_url = ?,
                image_path = ?, symbol_svg = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            template.category, template.subcategory, template.name,
            template.designation_prefix, template.component_type,
            template.default_voltage, template.description, template.manufacturer,
            template.part_number, template.datasheet_url, template.image_path,
            template.symbol_svg, template_id
        ))
        self.conn.commit()

    def delete_template(self, template_id: int) -> None:
        """Delete a component template.

        Args:
            template_id: ID of template to delete
        """
        self.conn.execute("DELETE FROM component_library WHERE id = ?", (template_id,))
        self.conn.commit()

    def add_component_spec(self, spec: ComponentSpec) -> int:
        """Add a technical specification for a component.

        Args:
            spec: Specification to add

        Returns:
            ID of newly created spec
        """
        cursor = self.conn.execute("""
            INSERT INTO component_specs (component_id, spec_name, spec_value, unit)
            VALUES (?, ?, ?, ?)
        """, (spec.component_id, spec.spec_name, spec.spec_value, spec.unit))
        self.conn.commit()
        return cursor.lastrowid

    def get_component_specs(self, component_id: int) -> List[ComponentSpec]:
        """Get all specifications for a component.

        Args:
            component_id: Component ID

        Returns:
            List of specifications
        """
        rows = self.conn.execute(
            "SELECT * FROM component_specs WHERE component_id = ?",
            (component_id,)
        ).fetchall()

        return [ComponentSpec(
            id=row['id'],
            component_id=row['component_id'],
            spec_name=row['spec_name'],
            spec_value=row['spec_value'],
            unit=row['unit']
        ) for row in rows]

    def save_component_image(
        self,
        component_id: int,
        image_type: str,
        image_data: bytes,
        image_format: str,
        width: int,
        height: int
    ) -> int:
        """Save an image for a component.

        Args:
            component_id: Component ID
            image_type: Type of image (symbol, photo, datasheet_preview)
            image_data: Binary image data
            image_format: Image format (png, jpg, svg)
            width: Image width
            height: Image height

        Returns:
            ID of newly created image record
        """
        cursor = self.conn.execute("""
            INSERT INTO component_images (
                component_id, image_type, image_data, image_format, width, height
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (component_id, image_type, image_data, image_format, width, height))
        self.conn.commit()
        return cursor.lastrowid

    def get_component_image(
        self,
        component_id: int,
        image_type: str
    ) -> Optional[Tuple[bytes, str, int, int]]:
        """Get an image for a component.

        Args:
            component_id: Component ID
            image_type: Type of image

        Returns:
            Tuple of (image_data, format, width, height) or None
        """
        row = self.conn.execute("""
            SELECT image_data, image_format, width, height
            FROM component_images
            WHERE component_id = ? AND image_type = ?
        """, (component_id, image_type)).fetchone()

        if row:
            return (row['image_data'], row['image_format'], row['width'], row['height'])
        return None

    # Project CRUD operations

    def create_project(
        self,
        name: str,
        pdf_path: Optional[str] = None,
        description: Optional[str] = None
    ) -> int:
        """Create a new project.

        Args:
            name: Project name
            pdf_path: Path to source PDF file
            description: Project description

        Returns:
            ID of newly created project
        """
        cursor = self.conn.execute("""
            INSERT INTO projects (name, pdf_path, description)
            VALUES (?, ?, ?)
        """, (name, pdf_path, description))
        self.conn.commit()
        return cursor.lastrowid

    def get_project(self, project_id: int) -> Optional[ProjectInfo]:
        """Get project by ID.

        Args:
            project_id: Project ID

        Returns:
            ProjectInfo if found, None otherwise
        """
        row = self.conn.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,)
        ).fetchone()

        if row:
            return ProjectInfo(
                id=row['id'],
                name=row['name'],
                pdf_path=row['pdf_path'],
                description=row['description'],
                created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                modified_at=datetime.fromisoformat(row['modified_at']) if row['modified_at'] else None
            )
        return None

    def list_projects(self, limit: int = 100) -> List[ProjectInfo]:
        """List all projects.

        Args:
            limit: Maximum number of projects to return

        Returns:
            List of projects ordered by most recently modified
        """
        rows = self.conn.execute(
            "SELECT * FROM projects ORDER BY modified_at DESC LIMIT ?",
            (limit,)
        ).fetchall()

        return [ProjectInfo(
            id=row['id'],
            name=row['name'],
            pdf_path=row['pdf_path'],
            description=row['description'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            modified_at=datetime.fromisoformat(row['modified_at']) if row['modified_at'] else None
        ) for row in rows]

    def update_project_modified(self, project_id: int) -> None:
        """Update project modified timestamp.

        Args:
            project_id: Project ID
        """
        self.conn.execute(
            "UPDATE projects SET modified_at = CURRENT_TIMESTAMP WHERE id = ?",
            (project_id,)
        )
        self.conn.commit()

    def delete_project(self, project_id: int) -> None:
        """Delete a project and all associated data.

        Args:
            project_id: Project ID
        """
        self.conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        self.conn.commit()

    def get_categories(self) -> List[str]:
        """Get list of all component categories.

        Returns:
            List of unique categories
        """
        rows = self.conn.execute(
            "SELECT DISTINCT category FROM component_library ORDER BY category"
        ).fetchall()
        return [row['category'] for row in rows]

    def get_schema_version(self) -> int:
        """Get current database schema version.

        Returns:
            Schema version number
        """
        row = self.conn.execute("SELECT MAX(version) as version FROM schema_version").fetchone()
        return row['version'] if row and row['version'] else 0

    def add_from_digikey(
        self,
        digikey_product,  # DigiKeyProductDetails
        category: str,
        subcategory: Optional[str],
        component_type: str,
        designation_prefix: str
    ) -> int:
        """Add component to library from DigiKey product data.

        Args:
            digikey_product: DigiKey product details
            category: Component category
            subcategory: Component subcategory
            component_type: IndustrialComponentType enum value
            designation_prefix: Designation prefix (e.g., 'K', 'S', 'M')

        Returns:
            ID of newly created component template
        """
        # Determine voltage from parameters
        voltage = None
        for param_name, param_value in digikey_product.parameters.items():
            if 'voltage' in param_name.lower() or 'coil' in param_name.lower():
                voltage = param_value
                break

        # Create template
        template = ComponentTemplate(
            id=None,
            category=category,
            subcategory=subcategory,
            name=f"{digikey_product.manufacturer} {digikey_product.manufacturer_part_number}",
            designation_prefix=designation_prefix,
            component_type=component_type,
            default_voltage=voltage,
            description=digikey_product.description,
            manufacturer=digikey_product.manufacturer,
            part_number=digikey_product.part_number,
            datasheet_url=digikey_product.primary_datasheet,
            image_path=digikey_product.primary_photo,
            symbol_svg=None
        )

        with self.transaction():
            # Add template
            component_id = self.add_component_template(template)

            # Add specifications
            for param_name, param_value in digikey_product.parameters.items():
                spec = ComponentSpec(
                    id=None,
                    component_id=component_id,
                    spec_name=param_name,
                    spec_value=param_value,
                    unit=None  # Could parse units from value
                )
                self.add_component_spec(spec)

        return component_id
