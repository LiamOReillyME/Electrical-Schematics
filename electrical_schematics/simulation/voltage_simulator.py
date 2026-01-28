"""Simulate voltage flow through industrial wiring diagrams."""

import networkx as nx
from typing import List, Set, Dict, Tuple
from electrical_schematics.models.diagram import WiringDiagram
from electrical_schematics.models.industrial_component import IndustrialComponent, SensorState
from electrical_schematics.models.wire import Wire


class VoltageSimulator:
    """Simulates voltage flow through circuits based on component states."""

    def __init__(self, diagram: WiringDiagram):
        """
        Initialize the voltage simulator.

        Args:
            diagram: The wiring diagram to simulate
        """
        self.diagram = diagram
        self.graph = self._build_graph()

    def _build_graph(self) -> nx.Graph:
        """Build an undirected graph of electrical connections."""
        graph = nx.Graph()

        # Add all components as nodes
        for comp in self.diagram.components:
            graph.add_node(comp.id, component=comp)

        # Add wires as edges
        for wire in self.diagram.wires:
            if wire.from_component_id and wire.to_component_id:
                graph.add_edge(
                    wire.from_component_id,
                    wire.to_component_id,
                    wire=wire
                )

        return graph

    def simulate(self) -> Dict[str, bool]:
        """
        Simulate voltage flow through the circuit.

        Returns:
            Dictionary mapping component IDs to energized state
        """
        energized: Dict[str, bool] = {}

        # Start from power sources
        power_sources = self.diagram.get_power_sources()

        for source in power_sources:
            # Find all components reachable from this power source
            # considering component states (sensors ON/OFF)
            reachable = self._trace_voltage_from(source.id)

            for comp_id in reachable:
                energized[comp_id] = True

        return energized

    def _trace_voltage_from(self, source_id: str) -> Set[str]:
        """
        Trace voltage flow from a component using BFS.

        Only follows paths where all intermediate components allow current flow.

        Args:
            source_id: Starting component ID

        Returns:
            Set of component IDs that are energized
        """
        energized = {source_id}
        queue = [source_id]
        visited = set()

        while queue:
            current_id = queue.pop(0)

            if current_id in visited:
                continue
            visited.add(current_id)

            current_comp = self.diagram.get_component(current_id)
            if not current_comp:
                continue

            # Only continue through components that allow current flow
            if not current_comp.is_energized():
                continue

            # Find all neighbors in the graph
            if current_id in self.graph:
                for neighbor_id in self.graph.neighbors(current_id):
                    if neighbor_id not in visited:
                        energized.add(neighbor_id)
                        queue.append(neighbor_id)

        return energized

    def get_voltage_path(self, from_id: str, to_id: str) -> List[str]:
        """
        Find a voltage path between two components.

        Args:
            from_id: Source component ID
            to_id: Destination component ID

        Returns:
            List of component IDs in the path, or empty if no path exists
        """
        # Check if both components exist
        if from_id not in self.graph or to_id not in self.graph:
            return []

        # Build a subgraph containing only energized components
        energized = self.simulate()
        subgraph = self.graph.subgraph([
            comp_id for comp_id, is_energized in energized.items()
            if is_energized
        ])

        try:
            return nx.shortest_path(subgraph, from_id, to_id)
        except nx.NetworkXNoPath:
            return []

    def explain_voltage_flow(self, component_id: str) -> str:
        """
        Generate a human-readable explanation of voltage flow to a component.

        Args:
            component_id: Component to explain

        Returns:
            Text explanation
        """
        comp = self.diagram.get_component(component_id)
        if not comp:
            return f"Component {component_id} not found."

        energized = self.simulate()
        is_energized = energized.get(component_id, False)

        explanation = f"Component: {comp}\n"
        explanation += f"Status: {'ENERGIZED' if is_energized else 'NOT ENERGIZED'}\n\n"

        if is_energized:
            # Find path from power sources
            power_sources = self.diagram.get_power_sources()
            for source in power_sources:
                path = self.get_voltage_path(source.id, component_id)
                if path:
                    explanation += f"Voltage path from {source.designation}:\n"
                    for i, comp_id in enumerate(path):
                        c = self.diagram.get_component(comp_id)
                        if c:
                            state_info = ""
                            if c.is_sensor():
                                state_info = f" (State: {c.state.value})"
                            explanation += f"  {i+1}. {c.designation}{state_info}\n"
                    break
        else:
            explanation += "Possible reasons:\n"
            # Check sensors in potential paths
            sensors = self.diagram.get_sensors()
            for sensor in sensors:
                if sensor.state == SensorState.OFF and sensor.normally_open:
                    explanation += f"  - {sensor.designation} is OFF (normally open)\n"
                elif sensor.state == SensorState.ON and not sensor.normally_open:
                    explanation += f"  - {sensor.designation} is ON (normally closed)\n"

        return explanation
