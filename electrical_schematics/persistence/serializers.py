"""Serializers for converting models to/from database format."""

from typing import Dict, Any, List
from electrical_schematics.models import (
    IndustrialComponent,
    IndustrialComponentType,
    SensorState,
    Wire,
    WirePoint,
    WiringDiagram
)


class ComponentSerializer:
    """Serializer for IndustrialComponent."""

    @staticmethod
    def to_dict(component: IndustrialComponent) -> Dict[str, Any]:
        """Convert component to dictionary.

        Args:
            component: Component to serialize

        Returns:
            Dictionary representation
        """
        return {
            'id': component.id,
            'type': component.type.value,
            'designation': component.designation,
            'description': component.description,
            'voltage_rating': component.voltage_rating,
            'x': component.x,
            'y': component.y,
            'width': component.width,
            'height': component.height,
            'state': component.state.value,
            'normally_open': component.normally_open,
            'contacts': component.contacts or []
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> IndustrialComponent:
        """Create component from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            IndustrialComponent instance
        """
        # Parse component type
        try:
            comp_type = IndustrialComponentType(data['type'])
        except (KeyError, ValueError):
            comp_type = IndustrialComponentType.OTHER

        # Parse state
        try:
            state = SensorState(data.get('state', 'unknown'))
        except ValueError:
            state = SensorState.UNKNOWN

        return IndustrialComponent(
            id=data['id'],
            type=comp_type,
            designation=data['designation'],
            description=data.get('description'),
            voltage_rating=data.get('voltage_rating'),
            x=data.get('x', 0.0),
            y=data.get('y', 0.0),
            width=data.get('width', 40.0),
            height=data.get('height', 30.0),
            state=state,
            normally_open=data.get('normally_open', True),
            contacts=data.get('contacts', [])
        )

    @staticmethod
    def to_db_row(component: IndustrialComponent, project_id: int, component_library_id: int = None) -> Dict[str, Any]:
        """Convert component to database row format.

        Args:
            component: Component to serialize
            project_id: Project ID
            component_library_id: Optional library template ID

        Returns:
            Dictionary for database insertion
        """
        return {
            'project_id': project_id,
            'component_library_id': component_library_id,
            'designation': component.designation,
            'component_type': component.type.value,
            'voltage_rating': component.voltage_rating,
            'x': component.x,
            'y': component.y,
            'width': component.width,
            'height': component.height,
            'page_number': 0,  # Default page
            'state': component.state.value,
            'normally_open': component.normally_open,
            'metadata': {
                'id': component.id,
                'description': component.description,
                'contacts': component.contacts or []
            }
        }

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> IndustrialComponent:
        """Create component from database row.

        Args:
            row: Database row

        Returns:
            IndustrialComponent instance
        """
        metadata = row.get('metadata', {})
        if isinstance(metadata, str):
            import json
            metadata = json.loads(metadata)

        # Parse component type
        try:
            comp_type = IndustrialComponentType(row['component_type'])
        except (KeyError, ValueError):
            comp_type = IndustrialComponentType.OTHER

        # Parse state
        try:
            state = SensorState(row.get('state', 'unknown'))
        except ValueError:
            state = SensorState.UNKNOWN

        return IndustrialComponent(
            id=metadata.get('id', f"comp_{row.get('id', 0)}"),
            type=comp_type,
            designation=row['designation'],
            description=metadata.get('description'),
            voltage_rating=row.get('voltage_rating'),
            x=row.get('x', 0.0),
            y=row.get('y', 0.0),
            width=row.get('width', 40.0),
            height=row.get('height', 30.0),
            state=state,
            normally_open=row.get('normally_open', True),
            contacts=metadata.get('contacts', [])
        )


class WireSerializer:
    """Serializer for Wire."""

    @staticmethod
    def to_dict(wire: Wire) -> Dict[str, Any]:
        """Convert wire to dictionary.

        Args:
            wire: Wire to serialize

        Returns:
            Dictionary representation
        """
        return {
            'id': wire.id,
            'voltage_level': wire.voltage_level,
            'from_component_id': wire.from_component_id,
            'to_component_id': wire.to_component_id,
            'path': [{'x': p.x, 'y': p.y} for p in wire.path]
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> Wire:
        """Create wire from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Wire instance
        """
        path = [WirePoint(p['x'], p['y']) for p in data.get('path', [])]

        return Wire(
            id=data['id'],
            voltage_level=data['voltage_level'],
            path=path,
            from_component_id=data.get('from_component_id'),
            to_component_id=data.get('to_component_id')
        )

    @staticmethod
    def to_db_row(wire: Wire, project_id: int, wire_number: int) -> Dict[str, Any]:
        """Convert wire to database row format.

        Args:
            wire: Wire to serialize
            project_id: Project ID
            wire_number: Sequential wire number

        Returns:
            Dictionary for database insertion
        """
        # Determine color based on voltage level
        if "24" in wire.voltage_level or "24VDC" in wire.voltage_level:
            color = "red"
            wire_type = "24VDC"
        elif "0V" in wire.voltage_level:
            color = "blue"
            wire_type = "0V"
        elif "AC" in wire.voltage_level:
            color = "black"
            wire_type = "AC"
        else:
            color = "gray"
            wire_type = "other"

        return {
            'project_id': project_id,
            'wire_number': wire_number,
            'voltage_level': wire.voltage_level,
            'color': color,
            'wire_type': wire_type,
            'from_component_id': wire.from_component_id,
            'from_terminal': None,  # Not tracked yet
            'to_component_id': wire.to_component_id,
            'to_terminal': None,  # Not tracked yet
            'path_json': [{'x': p.x, 'y': p.y} for p in wire.path]
        }

    @staticmethod
    def from_db_row(row: Dict[str, Any]) -> Wire:
        """Create wire from database row.

        Args:
            row: Database row

        Returns:
            Wire instance
        """
        import json

        path_json = row.get('path_json', [])
        if isinstance(path_json, str):
            path_json = json.loads(path_json)

        path = [WirePoint(p['x'], p['y']) for p in path_json]

        return Wire(
            id=f"wire_{row.get('id', 0)}",
            voltage_level=row.get('voltage_level', 'unknown'),
            path=path,
            from_component_id=row.get('from_component_id'),
            to_component_id=row.get('to_component_id')
        )


class DiagramSerializer:
    """Serializer for WiringDiagram."""

    @staticmethod
    def to_dict(diagram: WiringDiagram) -> Dict[str, Any]:
        """Convert diagram to dictionary.

        Args:
            diagram: Diagram to serialize

        Returns:
            Dictionary representation
        """
        return {
            'name': diagram.name,
            'pdf_path': str(diagram.pdf_path) if diagram.pdf_path else None,
            'page_number': diagram.page_number,
            'components': [ComponentSerializer.to_dict(c) for c in diagram.components],
            'wires': [WireSerializer.to_dict(w) for w in diagram.wires]
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> WiringDiagram:
        """Create diagram from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            WiringDiagram instance
        """
        from pathlib import Path

        components = [ComponentSerializer.from_dict(c) for c in data.get('components', [])]
        wires = [WireSerializer.from_dict(w) for w in data.get('wires', [])]

        pdf_path = data.get('pdf_path')
        if pdf_path:
            pdf_path = Path(pdf_path)

        return WiringDiagram(
            name=data['name'],
            pdf_path=pdf_path,
            page_number=data.get('page_number', 0),
            components=components,
            wires=wires
        )
