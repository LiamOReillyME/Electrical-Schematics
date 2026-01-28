"""Project manager for saving and loading wiring diagrams."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from electrical_schematics.database import DatabaseManager
from electrical_schematics.models import WiringDiagram
from electrical_schematics.persistence.serializers import (
    ComponentSerializer,
    WireSerializer,
    DiagramSerializer
)


@dataclass
class ProjectInfo:
    """Information about a saved project."""
    id: int
    name: str
    pdf_path: Optional[str]
    description: Optional[str]
    created_at: datetime
    modified_at: datetime
    component_count: int = 0
    wire_count: int = 0


class ProjectManager:
    """Manager for saving and loading projects."""

    def __init__(self, db_manager: DatabaseManager):
        """Initialize project manager.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager

    def save_project(self, diagram: WiringDiagram, name: str, description: str = None) -> int:
        """Save a wiring diagram as a project.

        Args:
            diagram: Wiring diagram to save
            name: Project name
            description: Optional project description

        Returns:
            Project ID
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            # Start transaction
            conn.execute("BEGIN TRANSACTION")

            # Insert or update project metadata
            cursor.execute("""
                INSERT INTO projects (name, pdf_path, description, created_at, modified_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (name, str(diagram.pdf_path) if diagram.pdf_path else None, description))

            project_id = cursor.lastrowid

            # Save components
            for component in diagram.components:
                row = ComponentSerializer.to_db_row(component, project_id)
                cursor.execute("""
                    INSERT INTO diagram_components (
                        project_id, component_library_id, designation, component_type,
                        voltage_rating, x, y, width, height, page_number,
                        state, normally_open, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['project_id'],
                    row['component_library_id'],
                    row['designation'],
                    row['component_type'],
                    row['voltage_rating'],
                    row['x'],
                    row['y'],
                    row['width'],
                    row['height'],
                    row['page_number'],
                    row['state'],
                    row['normally_open'],
                    json.dumps(row['metadata'])
                ))

            # Save wires
            for idx, wire in enumerate(diagram.wires, start=1):
                row = WireSerializer.to_db_row(wire, project_id, idx)
                cursor.execute("""
                    INSERT INTO diagram_wires (
                        project_id, wire_number, voltage_level, color, wire_type,
                        from_component_id, from_terminal, to_component_id, to_terminal,
                        path_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['project_id'],
                    row['wire_number'],
                    row['voltage_level'],
                    row['color'],
                    row['wire_type'],
                    row['from_component_id'],
                    row['from_terminal'],
                    row['to_component_id'],
                    row['to_terminal'],
                    json.dumps(row['path_json'])
                ))

            # Commit transaction
            conn.commit()
            return project_id

        except Exception as e:
            # Rollback on error
            conn.rollback()
            raise Exception(f"Failed to save project: {e}")

    def update_project(self, project_id: int, diagram: WiringDiagram, name: str = None, description: str = None) -> None:
        """Update an existing project.

        Args:
            project_id: Project ID to update
            diagram: Updated wiring diagram
            name: Optional new name
            description: Optional new description
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            # Start transaction
            conn.execute("BEGIN TRANSACTION")

            # Update project metadata
            if name or description:
                if name and description:
                    cursor.execute("""
                        UPDATE projects
                        SET name = ?, description = ?, modified_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (name, description, project_id))
                elif name:
                    cursor.execute("""
                        UPDATE projects
                        SET name = ?, modified_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (name, project_id))
                elif description:
                    cursor.execute("""
                        UPDATE projects
                        SET description = ?, modified_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (description, project_id))
            else:
                cursor.execute("""
                    UPDATE projects
                    SET modified_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (project_id,))

            # Delete existing components and wires
            cursor.execute("DELETE FROM diagram_components WHERE project_id = ?", (project_id,))
            cursor.execute("DELETE FROM diagram_wires WHERE project_id = ?", (project_id,))

            # Save new components
            for component in diagram.components:
                row = ComponentSerializer.to_db_row(component, project_id)
                cursor.execute("""
                    INSERT INTO diagram_components (
                        project_id, component_library_id, designation, component_type,
                        voltage_rating, x, y, width, height, page_number,
                        state, normally_open, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['project_id'],
                    row['component_library_id'],
                    row['designation'],
                    row['component_type'],
                    row['voltage_rating'],
                    row['x'],
                    row['y'],
                    row['width'],
                    row['height'],
                    row['page_number'],
                    row['state'],
                    row['normally_open'],
                    json.dumps(row['metadata'])
                ))

            # Save new wires
            for idx, wire in enumerate(diagram.wires, start=1):
                row = WireSerializer.to_db_row(wire, project_id, idx)
                cursor.execute("""
                    INSERT INTO diagram_wires (
                        project_id, wire_number, voltage_level, color, wire_type,
                        from_component_id, from_terminal, to_component_id, to_terminal,
                        path_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['project_id'],
                    row['wire_number'],
                    row['voltage_level'],
                    row['color'],
                    row['wire_type'],
                    row['from_component_id'],
                    row['from_terminal'],
                    row['to_component_id'],
                    row['to_terminal'],
                    json.dumps(row['path_json'])
                ))

            # Commit transaction
            conn.commit()

        except Exception as e:
            # Rollback on error
            conn.rollback()
            raise Exception(f"Failed to update project: {e}")

    def load_project(self, project_id: int) -> WiringDiagram:
        """Load a project by ID.

        Args:
            project_id: Project ID to load

        Returns:
            WiringDiagram instance
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        # Load project metadata
        cursor.execute("""
            SELECT id, name, pdf_path, description, created_at, modified_at
            FROM projects
            WHERE id = ?
        """, (project_id,))

        project_row = cursor.fetchone()
        if not project_row:
            raise ValueError(f"Project {project_id} not found")

        # Load components
        cursor.execute("""
            SELECT id, project_id, component_library_id, designation, component_type,
                   voltage_rating, x, y, width, height, page_number,
                   state, normally_open, metadata
            FROM diagram_components
            WHERE project_id = ?
        """, (project_id,))

        components = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            component = ComponentSerializer.from_db_row(row_dict)
            components.append(component)

        # Load wires
        cursor.execute("""
            SELECT id, project_id, wire_number, voltage_level, color, wire_type,
                   from_component_id, from_terminal, to_component_id, to_terminal,
                   path_json
            FROM diagram_wires
            WHERE project_id = ?
            ORDER BY wire_number
        """, (project_id,))

        wires = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            wire = WireSerializer.from_db_row(row_dict)
            wires.append(wire)

        # Create diagram
        pdf_path = Path(project_row['pdf_path']) if project_row['pdf_path'] else None

        diagram = WiringDiagram(
            name=project_row['name'],
            pdf_path=pdf_path,
            page_number=0,
            components=components,
            wires=wires
        )

        return diagram

    def list_projects(self, limit: int = None) -> List[ProjectInfo]:
        """List all projects.

        Args:
            limit: Optional limit on number of projects

        Returns:
            List of ProjectInfo objects
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT
                p.id, p.name, p.pdf_path, p.description, p.created_at, p.modified_at,
                COUNT(DISTINCT c.id) as component_count,
                COUNT(DISTINCT w.id) as wire_count
            FROM projects p
            LEFT JOIN diagram_components c ON p.id = c.project_id
            LEFT JOIN diagram_wires w ON p.id = w.project_id
            GROUP BY p.id
            ORDER BY p.modified_at DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)

        projects = []
        for row in cursor.fetchall():
            projects.append(ProjectInfo(
                id=row['id'],
                name=row['name'],
                pdf_path=row['pdf_path'],
                description=row['description'],
                created_at=datetime.fromisoformat(row['created_at']),
                modified_at=datetime.fromisoformat(row['modified_at']),
                component_count=row['component_count'],
                wire_count=row['wire_count']
            ))

        return projects

    def list_recent_projects(self, limit: int = 10) -> List[ProjectInfo]:
        """List recent projects.

        Args:
            limit: Number of projects to return

        Returns:
            List of ProjectInfo objects
        """
        return self.list_projects(limit=limit)

    def delete_project(self, project_id: int) -> None:
        """Delete a project.

        Args:
            project_id: Project ID to delete
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            conn.execute("BEGIN TRANSACTION")

            # Delete components and wires (cascaded by foreign keys)
            cursor.execute("DELETE FROM diagram_components WHERE project_id = ?", (project_id,))
            cursor.execute("DELETE FROM diagram_wires WHERE project_id = ?", (project_id,))

            # Delete project
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to delete project: {e}")

    def export_project(self, project_id: int, export_path: Path) -> None:
        """Export project to JSON file.

        Args:
            project_id: Project ID to export
            export_path: Path to export file
        """
        diagram = self.load_project(project_id)
        data = DiagramSerializer.to_dict(diagram)

        with open(export_path, 'w') as f:
            json.dump(data, f, indent=2)

    def import_project(self, import_path: Path, name: str = None) -> int:
        """Import project from JSON file.

        Args:
            import_path: Path to import file
            name: Optional name override

        Returns:
            Project ID
        """
        with open(import_path, 'r') as f:
            data = json.load(f)

        diagram = DiagramSerializer.from_dict(data)

        # Use provided name or name from file
        project_name = name or diagram.name or import_path.stem

        return self.save_project(diagram, project_name, "Imported from JSON")
