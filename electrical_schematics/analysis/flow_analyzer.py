"""Analyze signal and electrical flow through circuits."""

import networkx as nx
from typing import List, Set
from electrical_schematics.models import Schematic, Component


class FlowAnalyzer:
    """Analyzes signal and power flow through electrical circuits."""

    def __init__(self, schematic: Schematic):
        """
        Initialize the flow analyzer.

        Args:
            schematic: The schematic to analyze
        """
        self.schematic = schematic
        self.graph = self._build_graph()

    def _build_graph(self) -> nx.DiGraph:
        """Build a directed graph from the schematic connections."""
        graph = nx.DiGraph()

        # Add nodes for each component
        for component in self.schematic.components:
            graph.add_node(component.id, component=component)

        # Add edges for each connection
        for connection in self.schematic.connections:
            graph.add_edge(
                connection.from_pin.component_id,
                connection.to_pin.component_id,
                connection=connection
            )

        return graph

    def find_signal_path(self, source_id: str, dest_id: str) -> List[str]:
        """
        Find signal path between two components.

        Args:
            source_id: ID of source component
            dest_id: ID of destination component

        Returns:
            List of component IDs in the path
        """
        try:
            return nx.shortest_path(self.graph, source_id, dest_id)
        except nx.NetworkXNoPath:
            return []

    def find_power_sources(self) -> List[Component]:
        """Find all power source components in the circuit."""
        from electrical_schematics.models import ComponentType
        return [
            comp for comp in self.schematic.components
            if comp.type == ComponentType.POWER_SOURCE
        ]

    def find_grounds(self) -> List[Component]:
        """Find all ground components in the circuit."""
        from electrical_schematics.models import ComponentType
        return [
            comp for comp in self.schematic.components
            if comp.type == ComponentType.GROUND
        ]

    def get_connected_components(self, component_id: str) -> Set[str]:
        """
        Get all components connected to the given component.

        Args:
            component_id: ID of the component

        Returns:
            Set of connected component IDs
        """
        if component_id not in self.graph:
            return set()

        # Get all nodes reachable from this component (both directions)
        descendants = nx.descendants(self.graph, component_id)
        ancestors = nx.ancestors(self.graph, component_id)

        return descendants | ancestors
