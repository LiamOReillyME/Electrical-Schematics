"""Parser for extracting contact configuration from component descriptions."""

import re
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class ContactConfiguration:
    """Configuration of electrical contacts for a component.

    Represents the switching contacts and terminals of industrial components
    like relays, contactors, switches, and terminal blocks.
    """

    # Contact counts
    no_contacts: int = 0  # Normally Open contacts
    nc_contacts: int = 0  # Normally Closed contacts
    poles: int = 0  # Total poles (for DPDT, SPDT, etc.)

    # Component type classification
    component_type: str = "unknown"  # relay, contactor, terminal_block, switch, etc.

    # Terminal block specific
    positions: int = 0  # Number of terminal positions

    # Power contacts (for contactors)
    power_contacts: int = 0  # Main power switching contacts (1-2, 3-4, 5-6)

    # Additional metadata
    auxiliary_contacts: bool = False  # Has auxiliary contacts
    three_phase: bool = False  # Three-phase contactor/motor starter

    # Raw data
    description: str = ""  # Original description

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "no_contacts": self.no_contacts,
            "nc_contacts": self.nc_contacts,
            "poles": self.poles,
            "component_type": self.component_type,
            "positions": self.positions,
            "power_contacts": self.power_contacts,
            "auxiliary_contacts": self.auxiliary_contacts,
            "three_phase": self.three_phase,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContactConfiguration":
        """Create from dictionary."""
        return cls(
            no_contacts=data.get("no_contacts", 0),
            nc_contacts=data.get("nc_contacts", 0),
            poles=data.get("poles", 0),
            component_type=data.get("component_type", "unknown"),
            positions=data.get("positions", 0),
            power_contacts=data.get("power_contacts", 0),
            auxiliary_contacts=data.get("auxiliary_contacts", False),
            three_phase=data.get("three_phase", False),
            description=data.get("description", ""),
        )


class ContactConfigParser:
    """Parses component descriptions to extract contact configurations.

    Understands common industrial electrical component descriptions and extracts
    switching contact information for icon generation.
    """

    # Component type keywords
    RELAY_KEYWORDS = ['relay', 'relais']
    CONTACTOR_KEYWORDS = ['contactor', 'schütz', 'schutz']
    TERMINAL_KEYWORDS = ['terminal block', 'terminal strip', 'connector']
    SWITCH_KEYWORDS = ['switch', 'selector', 'button', 'estop', 'e-stop']
    BREAKER_KEYWORDS = ['circuit breaker', 'breaker', 'mcb', 'mccb']
    MOTOR_KEYWORDS = ['motor', 'starter']

    def parse_description(self, description: str, category: str = "") -> ContactConfiguration:
        """Parse component description to extract contact configuration.

        Args:
            description: Component description from DigiKey or manufacturer
            category: Optional category hint (e.g., "Relays", "Contactors")

        Returns:
            ContactConfiguration with extracted data
        """
        if not description:
            return ContactConfiguration()

        desc_lower = description.lower()

        config = ContactConfiguration(description=description)

        # Determine component type
        config.component_type = self._classify_component_type(desc_lower, category)

        # Extract contact counts
        config.no_contacts = self._extract_no_contacts(desc_lower)
        config.nc_contacts = self._extract_nc_contacts(desc_lower)
        config.poles = self._extract_poles(desc_lower)

        # Extract pole configuration (SPDT, DPDT, etc.)
        pole_config = self._extract_pole_configuration(desc_lower)
        if pole_config:
            config.poles = pole_config['poles']
            config.no_contacts = max(config.no_contacts, pole_config.get('no_contacts', 0))
            config.nc_contacts = max(config.nc_contacts, pole_config.get('nc_contacts', 0))

        # Extract terminal positions
        config.positions = self._extract_terminal_positions(desc_lower)

        # Detect three-phase
        config.three_phase = self._detect_three_phase(desc_lower)

        # Calculate power contacts for contactors
        if config.component_type == 'contactor' and config.three_phase:
            config.power_contacts = 3  # Three phases

        # Detect auxiliary contacts
        config.auxiliary_contacts = 'auxiliary' in desc_lower or 'aux' in desc_lower

        # Validate and normalize
        self._validate_config(config)

        logger.debug(f"Parsed contact config: {config.component_type}, "
                     f"NO={config.no_contacts}, NC={config.nc_contacts}, "
                     f"poles={config.poles}")

        return config

    def _classify_component_type(self, description: str, category: str = "") -> str:
        """Classify component type from description and category.

        Args:
            description: Lowercase description
            category: Optional category string

        Returns:
            Component type: relay, contactor, terminal_block, switch, etc.
        """
        category_lower = category.lower() if category else ""

        # Check category first (more reliable)
        if any(kw in category_lower for kw in ['relay', 'relais']):
            return 'relay'
        if any(kw in category_lower for kw in ['contactor', 'motor starter']):
            return 'contactor'
        if any(kw in category_lower for kw in ['terminal', 'connector']):
            return 'terminal_block'
        if any(kw in category_lower for kw in ['switch', 'button']):
            return 'switch'
        if any(kw in category_lower for kw in ['breaker', 'circuit protection']):
            return 'circuit_breaker'

        # Check description
        if any(kw in description for kw in self.CONTACTOR_KEYWORDS):
            return 'contactor'
        if any(kw in description for kw in self.RELAY_KEYWORDS):
            return 'relay'
        if any(kw in description for kw in self.TERMINAL_KEYWORDS):
            return 'terminal_block'
        if any(kw in description for kw in self.SWITCH_KEYWORDS):
            return 'switch'
        if any(kw in description for kw in self.BREAKER_KEYWORDS):
            return 'circuit_breaker'
        if any(kw in description for kw in self.MOTOR_KEYWORDS):
            return 'motor'

        return 'unknown'

    def _extract_no_contacts(self, description: str) -> int:
        """Extract number of NO (Normally Open) contacts.

        Args:
            description: Lowercase description

        Returns:
            Number of NO contacts, or 0 if not found
        """
        # Pattern: "2 NO", "3NO", "2-NO", etc.
        patterns = [
            r'(\d+)\s*[-\s]?no(?:\s+contact|s)?',
            r'(\d+)\s*[-\s]?n\.?o\.?',
            r'(\d+)\s*[-\s]?normally\s+open',
        ]

        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return 0

    def _extract_nc_contacts(self, description: str) -> int:
        """Extract number of NC (Normally Closed) contacts.

        Args:
            description: Lowercase description

        Returns:
            Number of NC contacts, or 0 if not found
        """
        # Pattern: "2 NC", "1NC", "2-NC", etc.
        patterns = [
            r'(\d+)\s*[-\s]?nc(?:\s+contact|s)?',
            r'(\d+)\s*[-\s]?n\.?c\.?',
            r'(\d+)\s*[-\s]?normally\s+closed',
        ]

        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return 0

    def _extract_poles(self, description: str) -> int:
        """Extract number of poles.

        Args:
            description: Lowercase description

        Returns:
            Number of poles, or 0 if not found
        """
        # Pattern: "2 pole", "3-pole", "4 poles", etc.
        patterns = [
            r'(\d+)\s*[-\s]?pole?s?',
            r'(\d+)p\s',
        ]

        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return 0

    def _extract_pole_configuration(self, description: str) -> Optional[Dict[str, int]]:
        """Extract pole configuration from abbreviations like SPDT, DPDT.

        Args:
            description: Lowercase description

        Returns:
            Dict with poles, no_contacts, nc_contacts, or None
        """
        # SPST = Single Pole Single Throw (1 pole, 1 NO or 1 NC)
        # SPDT = Single Pole Double Throw (1 pole, 1 NO + 1 NC)
        # DPST = Double Pole Single Throw (2 poles, 2 NO or 2 NC)
        # DPDT = Double Pole Double Throw (2 poles, 2 NO + 2 NC)
        # 3PDT = 3 Pole Double Throw (3 poles, 3 NO + 3 NC)
        # 4PDT = 4 Pole Double Throw (4 poles, 4 NO + 4 NC)

        configs = {
            'spst': {'poles': 1, 'no_contacts': 1, 'nc_contacts': 0},
            'spdt': {'poles': 1, 'no_contacts': 1, 'nc_contacts': 1},
            'dpst': {'poles': 2, 'no_contacts': 2, 'nc_contacts': 0},
            'dpdt': {'poles': 2, 'no_contacts': 2, 'nc_contacts': 2},
            '3pdt': {'poles': 3, 'no_contacts': 3, 'nc_contacts': 3},
            '4pdt': {'poles': 4, 'no_contacts': 4, 'nc_contacts': 4},
        }

        for config_name, config_data in configs.items():
            if config_name in description:
                return config_data

        return None

    def _extract_terminal_positions(self, description: str) -> int:
        """Extract number of terminal positions for terminal blocks.

        Args:
            description: Lowercase description

        Returns:
            Number of positions, or 0 if not found
        """
        # Pattern: "10 position", "10-position", "10 positions", etc.
        patterns = [
            r'(\d+)\s*[-\s]?position?s?',
            r'(\d+)\s*[-\s]?way',
            r'(\d+)\s*[-\s]?terminal',
        ]

        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return 0

    def _detect_three_phase(self, description: str) -> bool:
        """Detect if component is for three-phase applications.

        Args:
            description: Lowercase description

        Returns:
            True if three-phase
        """
        indicators = [
            '3-phase', '3 phase', 'three phase', 'three-phase',
            '3ph', '400v', '480v', '690v',  # Common 3-phase voltages
        ]
        return any(ind in description for ind in indicators)

    def _validate_config(self, config: ContactConfiguration) -> None:
        """Validate and normalize contact configuration.

        Args:
            config: ContactConfiguration to validate (modified in place)
        """
        # If we have poles but no contacts, infer from component type
        if config.poles > 0 and config.no_contacts == 0 and config.nc_contacts == 0:
            if config.component_type in ['relay', 'contactor']:
                # Assume SPST by default (one NO contact per pole)
                config.no_contacts = config.poles

        # If terminal block, ensure positions is set
        if config.component_type == 'terminal_block' and config.positions == 0:
            # Try to extract from poles or contacts
            if config.poles > 0:
                config.positions = config.poles
            elif config.no_contacts > 0:
                config.positions = config.no_contacts

        # Normalize empty configs
        if (config.no_contacts == 0 and config.nc_contacts == 0 and
                config.poles == 0 and config.positions == 0):
            # Default values based on component type
            if config.component_type == 'relay':
                config.no_contacts = 1
                config.poles = 1
            elif config.component_type == 'contactor':
                config.power_contacts = 3  # Assume 3-phase
                config.no_contacts = 1  # One auxiliary
