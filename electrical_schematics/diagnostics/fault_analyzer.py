"""Rule-based fault analysis and diagnostics."""

from dataclasses import dataclass
from typing import List, Optional
from electrical_schematics.models.diagram import WiringDiagram
from electrical_schematics.models.industrial_component import SensorState
from electrical_schematics.simulation import VoltageSimulator


@dataclass
class FaultCondition:
    """Describes a fault condition."""
    symptom: str  # What the user observes
    expected_component: str  # Component that should be working
    expected_state: str  # Expected state (e.g., "energized", "on")


@dataclass
class DiagnosticResult:
    """Result of diagnostic analysis."""
    fault_condition: FaultCondition
    possible_causes: List[str]
    suggested_checks: List[str]
    affected_components: List[str]


class FaultAnalyzer:
    """Analyzes faults and provides diagnostic guidance."""

    def __init__(self, diagram: WiringDiagram):
        """
        Initialize the fault analyzer.

        Args:
            diagram: The wiring diagram to analyze
        """
        self.diagram = diagram
        self.simulator = VoltageSimulator(diagram)

    def diagnose(self, fault: FaultCondition) -> DiagnosticResult:
        """
        Analyze a fault condition and provide diagnostic guidance.

        Args:
            fault: The fault condition to diagnose

        Returns:
            Diagnostic result with possible causes and checks
        """
        possible_causes = []
        suggested_checks = []
        affected_components = []

        # Get the component mentioned in the fault
        comp = self.diagram.get_component_by_designation(fault.expected_component)

        if not comp:
            possible_causes.append(f"Component {fault.expected_component} not found in diagram")
            return DiagnosticResult(fault, possible_causes, suggested_checks, affected_components)

        # Simulate current state
        energized = self.simulator.simulate()
        is_energized = energized.get(comp.id, False)

        # If component should be energized but isn't
        if fault.expected_state.lower() in ["energized", "on", "active"]:
            if not is_energized:
                # Trace back to find the issue
                self._find_deenergized_causes(
                    comp.id,
                    possible_causes,
                    suggested_checks,
                    affected_components
                )

        # If component should be de-energized but is
        elif fault.expected_state.lower() in ["deenergized", "off", "inactive"]:
            if is_energized:
                possible_causes.append(
                    f"{comp.designation} is receiving voltage when it shouldn't"
                )
                self._find_unwanted_energization_causes(
                    comp.id,
                    possible_causes,
                    suggested_checks,
                    affected_components
                )

        return DiagnosticResult(
            fault_condition=fault,
            possible_causes=possible_causes,
            suggested_checks=suggested_checks,
            affected_components=affected_components
        )

    def _find_deenergized_causes(
        self,
        component_id: str,
        causes: List[str],
        checks: List[str],
        affected: List[str]
    ) -> None:
        """Find why a component is not energized."""
        comp = self.diagram.get_component(component_id)
        if not comp:
            return

        # Check for path from power sources
        power_sources = self.diagram.get_power_sources()
        has_path = False

        for source in power_sources:
            # Try to find path without considering sensor states
            try:
                import networkx as nx
                path = nx.shortest_path(self.simulator.graph, source.id, component_id)
                has_path = True

                # Check each component in the path
                for comp_id in path[1:]:  # Skip the power source itself
                    path_comp = self.diagram.get_component(comp_id)
                    if path_comp and path_comp.is_sensor():
                        if not path_comp.is_energized():
                            causes.append(
                                f"{path_comp.designation} is blocking current "
                                f"(State: {path_comp.state.value}, "
                                f"Type: {'NO' if path_comp.normally_open else 'NC'})"
                            )
                            checks.append(f"Check if {path_comp.designation} is functioning properly")
                            checks.append(f"Verify {path_comp.designation} wiring and connections")
                            affected.append(path_comp.designation)

            except:
                continue

        if not has_path:
            causes.append(f"No electrical path exists from power source to {comp.designation}")
            checks.append("Check wiring diagram for missing connections")

        # Check for common issues
        checks.append(f"Check fuses and circuit breakers in the circuit")
        checks.append(f"Verify {comp.designation} is properly wired")
        checks.append(f"Test voltage at {comp.designation} terminals with multimeter")

    def _find_unwanted_energization_causes(
        self,
        component_id: str,
        causes: List[str],
        checks: List[str],
        affected: List[str]
    ) -> None:
        """Find why a component is energized when it shouldn't be."""
        comp = self.diagram.get_component(component_id)
        if not comp:
            return

        causes.append("Possible short circuit or stuck relay contact")

        # Find which sensors should be blocking but aren't
        sensors = self.diagram.get_sensors()
        for sensor in sensors:
            if sensor.state == SensorState.ON and not sensor.normally_open:
                causes.append(f"{sensor.designation} (NC contact) may be stuck closed")
                affected.append(sensor.designation)

        checks.append(f"Check for short circuits near {comp.designation}")
        checks.append("Verify all safety interlocks are functioning")
        checks.append("Check relay contacts for welding or sticking")
