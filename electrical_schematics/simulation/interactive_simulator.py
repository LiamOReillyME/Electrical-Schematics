"""Interactive electrical simulation with real-time voltage flow visualization."""

import networkx as nx
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from electrical_schematics.models import (
    WiringDiagram,
    IndustrialComponent,
    IndustrialComponentType,
    SensorState,
    Wire
)


class CircuitState(Enum):
    """State of a circuit element."""
    ENERGIZED = "energized"
    DE_ENERGIZED = "de_energized"
    FAULTED = "faulted"


@dataclass
class VoltageNode:
    """Represents a node in the electrical circuit."""

    component_id: str
    terminal: Optional[str] = None
    voltage_level: Optional[float] = None  # Actual voltage value
    voltage_type: str = "UNKNOWN"  # 24VDC, 400VAC, etc.
    is_energized: bool = False
    current_flow: float = 0.0  # Amperes (for future enhancement)


@dataclass
class CircuitPath:
    """A traced path through the circuit."""

    source: str
    destination: str
    path_nodes: List[str]
    voltage_type: str
    is_active: bool
    blocking_component: Optional[str] = None


class InteractiveSimulator:
    """Interactive electrical circuit simulator with real-time updates."""

    def __init__(self, diagram: WiringDiagram):
        """Initialize the simulator.

        Args:
            diagram: Wiring diagram to simulate
        """
        self.diagram = diagram
        self.control_graph = nx.Graph()  # 24VDC control circuits
        self.power_graph = nx.Graph()    # 400VAC power circuits

        self.voltage_nodes: Dict[str, VoltageNode] = {}
        self.active_paths: List[CircuitPath] = []

        self._build_graphs()

    def _build_graphs(self) -> None:
        """Build separate graphs for control and power circuits."""
        # Add all components as nodes
        for comp in self.diagram.components:
            self.voltage_nodes[comp.id] = VoltageNode(
                component_id=comp.id,
                voltage_type=comp.voltage_rating,
                is_energized=False
            )

            # Add to appropriate graph based on voltage
            if comp.voltage_rating in ["24VDC", "5VDC"]:
                self.control_graph.add_node(comp.id, component=comp)
            elif comp.voltage_rating in ["400VAC", "230VAC"]:
                self.power_graph.add_node(comp.id, component=comp)
            else:
                # Add to both (relays/contactors bridge both circuits)
                self.control_graph.add_node(comp.id, component=comp)
                self.power_graph.add_node(comp.id, component=comp)

        # Add wire connections
        for wire in self.diagram.wires:
            if not wire.from_component_id or not wire.to_component_id:
                continue

            # Determine which graph(s) this wire belongs to
            if wire.voltage_level in ["24VDC", "5VDC"]:
                if (wire.from_component_id in self.control_graph and
                    wire.to_component_id in self.control_graph):
                    self.control_graph.add_edge(
                        wire.from_component_id,
                        wire.to_component_id,
                        wire=wire
                    )
            elif wire.voltage_level in ["400VAC", "230VAC"]:
                if (wire.from_component_id in self.power_graph and
                    wire.to_component_id in self.power_graph):
                    self.power_graph.add_edge(
                        wire.from_component_id,
                        wire.to_component_id,
                        wire=wire
                    )

    def simulate_step(self) -> Dict[str, VoltageNode]:
        """Run one simulation step.

        Returns:
            Dictionary of component_id to VoltageNode with current state
        """
        # Reset all nodes
        for node in self.voltage_nodes.values():
            node.is_energized = False
            node.voltage_level = None

        self.active_paths = []

        # Simulate control circuit (24VDC)
        self._simulate_circuit(self.control_graph, "24VDC", 24.0)

        # Simulate power circuit (400VAC)
        self._simulate_circuit(self.power_graph, "400VAC", 400.0)

        return self.voltage_nodes

    def _simulate_circuit(self, graph: nx.Graph, voltage_type: str, voltage_value: float) -> None:
        """Simulate voltage flow in a specific circuit.

        Args:
            graph: Circuit graph to simulate
            voltage_type: Type of voltage (24VDC, 400VAC, etc.)
            voltage_value: Nominal voltage value
        """
        # Find power sources for this voltage type
        power_sources = [
            node_id for node_id, data in graph.nodes(data=True)
            if data.get('component') and
            data['component'].voltage_rating == voltage_type and
            self._is_power_source(data['component'])
        ]

        # Trace from each power source
        for source_id in power_sources:
            self._trace_from_source(graph, source_id, voltage_type, voltage_value)

    def _is_power_source(self, component: IndustrialComponent) -> bool:
        """Check if component is a power source."""
        return component.type in [
            IndustrialComponentType.POWER_24VDC,
            IndustrialComponentType.POWER_400VAC,
            IndustrialComponentType.POWER_230VAC
        ]

    def _trace_from_source(
        self,
        graph: nx.Graph,
        source_id: str,
        voltage_type: str,
        voltage_value: float
    ) -> None:
        """Trace voltage from a power source using BFS.

        Args:
            graph: Circuit graph
            source_id: Power source component ID
            voltage_type: Voltage type
            voltage_value: Voltage value
        """
        visited = set()
        queue = [(source_id, [])]  # (node_id, path)

        while queue:
            current_id, path = queue.pop(0)

            if current_id in visited:
                continue

            visited.add(current_id)
            new_path = path + [current_id]

            # Mark this node as energized
            if current_id in self.voltage_nodes:
                node = self.voltage_nodes[current_id]
                node.is_energized = True
                node.voltage_level = voltage_value
                node.voltage_type = voltage_type

            # Get component
            if current_id not in graph:
                continue

            component = graph.nodes[current_id].get('component')
            if not component:
                continue

            # Check if current can flow through this component
            if not self._can_conduct(component):
                # Record blocked path
                continue

            # Continue to neighbors
            for neighbor_id in graph.neighbors(current_id):
                if neighbor_id not in visited:
                    queue.append((neighbor_id, new_path))

    def _can_conduct(self, component: IndustrialComponent) -> bool:
        """Check if component allows current to flow.

        Args:
            component: Component to check

        Returns:
            True if current can flow through this component
        """
        # Power sources always conduct
        if self._is_power_source(component):
            return True

        # Sensors/switches depend on state
        if component.is_sensor():
            if component.normally_open:
                return component.state == SensorState.ON
            else:  # Normally closed
                return component.state == SensorState.OFF

        # Fuses can be blown (future enhancement)
        if component.type in [IndustrialComponentType.FUSE, IndustrialComponentType.CIRCUIT_BREAKER]:
            # Check if faulted (for now, assume good)
            return True

        # Contactors/relays - need to check coil energization
        if component.type in [IndustrialComponentType.CONTACTOR, IndustrialComponentType.RELAY]:
            # If this is in the control graph, it's the coil - always conducts
            # If in power graph, it's the contacts - check if coil is energized
            return self._is_contactor_closed(component)

        # Most other components conduct
        return True

    def _is_contactor_closed(self, component: IndustrialComponent) -> bool:
        """Check if a contactor/relay is closed (coil energized).

        Args:
            component: Contactor/relay component

        Returns:
            True if contacts are closed
        """
        # Check if the control side (coil) is energized
        # The coil would be in the control graph (24VDC)
        # For now, simplified: check if component itself is energized
        node = self.voltage_nodes.get(component.id)
        if node:
            return node.is_energized
        return False

    def trace_coil_circuit(self, contactor_designation: str) -> CircuitPath:
        """Trace where a contactor coil gets its 24VDC from.

        Args:
            contactor_designation: Contactor designation (e.g., "K1")

        Returns:
            CircuitPath showing the 24VDC path to the coil
        """
        component = self.diagram.get_component_by_designation(contactor_designation)
        if not component:
            return CircuitPath(
                source="NOT_FOUND",
                destination=contactor_designation,
                path_nodes=[],
                voltage_type="UNKNOWN",
                is_active=False,
                blocking_component=f"Component {contactor_designation} not found"
            )

        # Find path from 24VDC source to this component
        power_sources = [
            comp for comp in self.diagram.components
            if comp.voltage_rating == "24VDC" and self._is_power_source(comp)
        ]

        for source in power_sources:
            try:
                path = nx.shortest_path(self.control_graph, source.id, component.id)

                # Check if path is active (all components conducting)
                is_active = True
                blocking = None

                for node_id in path[1:]:  # Skip source
                    comp = self.diagram.get_component(node_id)
                    if comp and not self._can_conduct(comp):
                        is_active = False
                        blocking = comp.designation
                        break

                return CircuitPath(
                    source=source.designation,
                    destination=contactor_designation,
                    path_nodes=[self.diagram.get_component(nid).designation for nid in path],
                    voltage_type="24VDC",
                    is_active=is_active,
                    blocking_component=blocking
                )
            except nx.NetworkXNoPath:
                continue

        return CircuitPath(
            source="NO_PATH",
            destination=contactor_designation,
            path_nodes=[],
            voltage_type="24VDC",
            is_active=False,
            blocking_component="No path found"
        )

    def trace_contact_circuit(self, contactor_designation: str) -> Tuple[CircuitPath, CircuitPath]:
        """Trace the main contact circuit (power side).

        Args:
            contactor_designation: Contactor designation

        Returns:
            Tuple of (supply_path, load_path) showing where power comes from and goes to
        """
        component = self.diagram.get_component_by_designation(contactor_designation)
        if not component:
            empty = CircuitPath("NOT_FOUND", contactor_designation, [], "UNKNOWN", False)
            return (empty, empty)

        # Find power sources feeding this contactor
        power_sources = [
            comp for comp in self.diagram.components
            if comp.voltage_rating in ["400VAC", "230VAC"] and self._is_power_source(comp)
        ]

        supply_path = None
        for source in power_sources:
            try:
                path = nx.shortest_path(self.power_graph, source.id, component.id)
                supply_path = CircuitPath(
                    source=source.designation,
                    destination=contactor_designation,
                    path_nodes=[self.diagram.get_component(nid).designation for nid in path],
                    voltage_type=source.voltage_rating,
                    is_active=self._is_contactor_closed(component),
                    blocking_component=None if self._is_contactor_closed(component) else contactor_designation
                )
                break
            except nx.NetworkXNoPath:
                continue

        # Find loads fed by this contactor
        load_path = None
        # Look for motors or other loads downstream
        try:
            descendants = nx.descendants(self.power_graph, component.id)
            loads = [
                nid for nid in descendants
                if self.diagram.get_component(nid).type == IndustrialComponentType.MOTOR
            ]

            if loads:
                path = nx.shortest_path(self.power_graph, component.id, loads[0])
                load_comp = self.diagram.get_component(loads[0])
                load_path = CircuitPath(
                    source=contactor_designation,
                    destination=load_comp.designation,
                    path_nodes=[self.diagram.get_component(nid).designation for nid in path],
                    voltage_type=component.voltage_rating,
                    is_active=self._is_contactor_closed(component),
                    blocking_component=None if self._is_contactor_closed(component) else contactor_designation
                )
        except:
            pass

        if not supply_path:
            supply_path = CircuitPath("NO_PATH", contactor_designation, [], "UNKNOWN", False)
        if not load_path:
            load_path = CircuitPath(contactor_designation, "NO_LOAD", [], "UNKNOWN", False)

        return (supply_path, load_path)

    def toggle_component(self, designation: str) -> Dict[str, VoltageNode]:
        """Toggle a component state (contactor, switch, fuse).

        Args:
            designation: Component designation to toggle

        Returns:
            Updated voltage nodes after simulation
        """
        component = self.diagram.get_component_by_designation(designation)
        if not component:
            return self.voltage_nodes

        # Toggle based on component type
        if component.is_sensor():
            # Toggle sensor state
            if component.state == SensorState.OFF:
                component.state = SensorState.ON
            elif component.state == SensorState.ON:
                component.state = SensorState.OFF
            else:
                component.state = SensorState.ON

        elif component.type in [IndustrialComponentType.CONTACTOR, IndustrialComponentType.RELAY]:
            # Toggle contactor (simulate energizing/de-energizing coil)
            if component.state == SensorState.OFF:
                component.state = SensorState.ON
            else:
                component.state = SensorState.OFF

        elif component.type in [IndustrialComponentType.FUSE, IndustrialComponentType.CIRCUIT_BREAKER]:
            # Toggle fuse state (trip/reset)
            if component.state == SensorState.OFF:
                component.state = SensorState.ON  # Good
            else:
                component.state = SensorState.OFF  # Blown/Tripped

        # Re-simulate
        return self.simulate_step()

    def get_energized_components(self, voltage_type: Optional[str] = None) -> List[IndustrialComponent]:
        """Get list of currently energized components.

        Args:
            voltage_type: Filter by voltage type (24VDC, 400VAC, etc.), or None for all

        Returns:
            List of energized components
        """
        result = []
        for comp_id, node in self.voltage_nodes.items():
            if node.is_energized:
                if voltage_type is None or node.voltage_type == voltage_type:
                    comp = self.diagram.get_component(comp_id)
                    if comp:
                        result.append(comp)
        return result

    def explain_state(self, designation: str) -> str:
        """Generate detailed explanation of component state.

        Args:
            designation: Component designation

        Returns:
            Human-readable explanation
        """
        component = self.diagram.get_component_by_designation(designation)
        if not component:
            return f"Component {designation} not found."

        node = self.voltage_nodes.get(component.id)

        explanation = f"Component: {designation}\n"
        explanation += f"Type: {component.type.value}\n"
        explanation += f"Rated: {component.voltage_rating}\n"
        explanation += f"Status: {'ENERGIZED' if node and node.is_energized else 'DE-ENERGIZED'}\n"

        if node and node.is_energized:
            explanation += f"Current Voltage: {node.voltage_level}V ({node.voltage_type})\n"

        # For contactors, show both coil and contact status
        if component.type in [IndustrialComponentType.CONTACTOR, IndustrialComponentType.RELAY]:
            explanation += "\n--- COIL CIRCUIT (Control) ---\n"
            coil_path = self.trace_coil_circuit(designation)
            explanation += f"24VDC Source: {coil_path.source}\n"
            explanation += f"Path: {' → '.join(coil_path.path_nodes)}\n"
            explanation += f"Active: {'YES' if coil_path.is_active else 'NO'}\n"
            if coil_path.blocking_component:
                explanation += f"Blocked by: {coil_path.blocking_component}\n"

            explanation += "\n--- MAIN CONTACTS (Power) ---\n"
            supply_path, load_path = self.trace_contact_circuit(designation)
            explanation += f"Supply from: {supply_path.source}\n"
            explanation += f"Supply path: {' → '.join(supply_path.path_nodes)}\n"
            explanation += f"Load to: {load_path.destination}\n"
            explanation += f"Load path: {' → '.join(load_path.path_nodes)}\n"
            explanation += f"Contacts: {'CLOSED' if coil_path.is_active else 'OPEN'}\n"

        return explanation
