"""Modern styling for the Industrial Wiring Diagram Analyzer.

This module provides a cohesive, professional visual style inspired by
modern industrial software interfaces.
"""

# Color Palette - Industrial/Technical theme
COLORS = {
    # Primary colors
    'primary': '#2C3E50',           # Dark blue-gray
    'primary_light': '#34495E',     # Lighter blue-gray
    'primary_dark': '#1A252F',      # Darker blue-gray

    # Accent colors
    'accent': '#3498DB',            # Blue
    'accent_hover': '#2980B9',      # Darker blue
    'accent_light': '#5DADE2',      # Light blue

    # Status colors
    'success': '#27AE60',           # Green
    'success_light': '#2ECC71',     # Light green
    'success_bg': '#C8F7DC',        # Light green background
    'warning': '#F39C12',           # Orange
    'warning_light': '#F1C40F',     # Yellow
    'danger': '#E74C3C',            # Red
    'danger_light': '#EC7063',      # Light red
    'danger_bg': '#FADBD8',         # Light red background

    # Neutral colors
    'background': '#F5F6FA',        # Light gray background
    'surface': '#FFFFFF',           # White surface
    'surface_dark': '#ECF0F1',      # Light gray surface
    'border': '#BDC3C7',            # Gray border
    'border_light': '#D5DBDB',      # Light border
    'text': '#2C3E50',              # Dark text
    'text_secondary': '#7F8C8D',    # Secondary text
    'text_muted': '#95A5A6',        # Muted text

    # Voltage-specific colors
    'voltage_24vdc': '#E74C3C',     # Red for 24VDC
    'voltage_0v': '#3498DB',        # Blue for 0V
    'voltage_400vac': '#2C3E50',    # Dark for 400VAC
    'voltage_230vac': '#8E44AD',    # Purple for 230VAC

    # Component state colors
    'energized': '#27AE60',         # Green
    'energized_text': '#006400',    # Dark green text
    'de_energized': '#E74C3C',      # Red
    'de_energized_text': '#8B0000', # Dark red text
    'unknown': '#95A5A6',           # Gray

    # Page highlight colors
    'current_page_highlight': '#FFF3CD',  # Light yellow for current page
    'current_page_border': '#FFC107',     # Yellow border
}


def get_main_stylesheet() -> str:
    """Get the main application stylesheet.

    Returns:
        CSS/QSS stylesheet string
    """
    return f"""
/* Main Window */
QMainWindow {{
    background-color: {COLORS['background']};
}}

QMainWindow::separator {{
    background-color: {COLORS['border']};
    width: 2px;
    height: 2px;
}}

/* Menu Bar */
QMenuBar {{
    background-color: {COLORS['primary']};
    color: white;
    padding: 4px;
    font-size: 13px;
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 6px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['primary_light']};
}}

QMenu {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {COLORS['accent']};
    color: white;
}}

QMenu::separator {{
    height: 1px;
    background-color: {COLORS['border_light']};
    margin: 4px 8px;
}}

/* Status Bar */
QStatusBar {{
    background-color: {COLORS['primary']};
    color: white;
    font-size: 12px;
    padding: 4px;
}}

QStatusBar QLabel {{
    color: white;
    margin-right: 10px;
}}

/* Dock Widgets */
QDockWidget {{
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(float.png);
    font-weight: bold;
    color: {COLORS['text']};
}}

QDockWidget::title {{
    background-color: {COLORS['primary']};
    color: white;
    padding: 8px;
    text-align: left;
}}

QDockWidget::close-button, QDockWidget::float-button {{
    background-color: transparent;
    border: none;
    padding: 2px;
}}

QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
    background-color: {COLORS['primary_light']};
    border-radius: 4px;
}}

/* Buttons */
QPushButton {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: {COLORS['surface_dark']};
    border-color: {COLORS['accent']};
}}

QPushButton:pressed {{
    background-color: {COLORS['border_light']};
}}

QPushButton:disabled {{
    background-color: {COLORS['surface_dark']};
    color: {COLORS['text_muted']};
    border-color: {COLORS['border_light']};
}}

QPushButton:checked {{
    background-color: {COLORS['accent']};
    color: white;
    border-color: {COLORS['accent_hover']};
}}

/* Primary Button */
QPushButton[class="primary"] {{
    background-color: {COLORS['accent']};
    color: white;
    border-color: {COLORS['accent_hover']};
}}

QPushButton[class="primary"]:hover {{
    background-color: {COLORS['accent_hover']};
}}

/* Success Button */
QPushButton[class="success"] {{
    background-color: {COLORS['success']};
    color: white;
    border-color: {COLORS['success']};
}}

/* Danger Button */
QPushButton[class="danger"] {{
    background-color: {COLORS['danger']};
    color: white;
    border-color: {COLORS['danger']};
}}

/* Input Fields */
QLineEdit {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {COLORS['accent']};
}}

QLineEdit:focus {{
    border-color: {COLORS['accent']};
    border-width: 2px;
}}

QLineEdit:disabled {{
    background-color: {COLORS['surface_dark']};
    color: {COLORS['text_muted']};
}}

QLineEdit::placeholder {{
    color: {COLORS['text_muted']};
}}

/* Combo Box */
QComboBox {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    min-height: 20px;
}}

QComboBox:hover {{
    border-color: {COLORS['accent']};
}}

QComboBox:focus {{
    border-color: {COLORS['accent']};
    border-width: 2px;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS['text_secondary']};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    selection-background-color: {COLORS['accent']};
    selection-color: white;
    padding: 4px;
}}

/* Spin Box */
QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 13px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {COLORS['accent']};
    border-width: 2px;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: {COLORS['surface_dark']};
    border: none;
    width: 20px;
}}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {COLORS['border_light']};
}}

/* Check Box */
QCheckBox {{
    color: {COLORS['text']};
    font-size: 13px;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {COLORS['border']};
    border-radius: 4px;
    background-color: {COLORS['surface']};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS['accent']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}

/* Tree Widget */
QTreeWidget {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    font-size: 13px;
    outline: none;
}}

QTreeWidget::item {{
    padding: 6px 4px;
    border-radius: 4px;
}}

QTreeWidget::item:hover {{
    background-color: {COLORS['surface_dark']};
}}

QTreeWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: white;
}}

QTreeWidget::branch {{
    background-color: transparent;
}}

QTreeWidget::branch:has-children:closed {{
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 8px solid {COLORS['text_secondary']};
}}

QTreeWidget::branch:has-children:open {{
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-bottom: 8px solid {COLORS['text_secondary']};
}}

QHeaderView::section {{
    background-color: {COLORS['primary']};
    color: white;
    padding: 8px;
    border: none;
    font-weight: bold;
}}

/* List Widget */
QListWidget {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    font-size: 13px;
    outline: none;
}}

QListWidget::item {{
    padding: 8px;
    border-radius: 4px;
    border-left: 3px solid transparent;
}}

QListWidget::item:hover {{
    background-color: {COLORS['surface_dark']};
}}

QListWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: white;
}}

/* Table Widget */
QTableWidget {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    gridline-color: {COLORS['border_light']};
    font-size: 13px;
}}

QTableWidget::item {{
    padding: 8px;
}}

QTableWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: white;
}}

/* Text Edit */
QTextEdit {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px;
    font-size: 13px;
    font-family: "Consolas", "Monaco", monospace;
}}

QTextEdit:focus {{
    border-color: {COLORS['accent']};
    border-width: 2px;
}}

/* Scroll Area */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

/* Scroll Bars */
QScrollBar:vertical {{
    background-color: {COLORS['surface_dark']};
    width: 12px;
    border-radius: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 6px;
    min-height: 30px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['text_secondary']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {COLORS['surface_dark']};
    height: 12px;
    border-radius: 6px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['border']};
    border-radius: 6px;
    min-width: 30px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['text_secondary']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* Tab Widget */
QTabWidget::pane {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 8px;
}}

QTabBar::tab {{
    background-color: {COLORS['surface_dark']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 10px 16px;
    margin-right: 2px;
    font-size: 13px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['surface']};
    border-bottom: 2px solid {COLORS['accent']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['border_light']};
}}

/* Group Box */
QGroupBox {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 16px;
    font-size: 13px;
    font-weight: bold;
    color: {COLORS['text']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 12px;
    margin-left: 8px;
    background-color: {COLORS['primary']};
    color: white;
    border-radius: 4px;
}}

/* Splitter */
QSplitter::handle {{
    background-color: {COLORS['border']};
}}

QSplitter::handle:horizontal {{
    width: 4px;
}}

QSplitter::handle:vertical {{
    height: 4px;
}}

QSplitter::handle:hover {{
    background-color: {COLORS['accent']};
}}

/* Dialog */
QDialog {{
    background-color: {COLORS['background']};
}}

QDialogButtonBox QPushButton {{
    min-width: 80px;
}}

/* Labels */
QLabel {{
    color: {COLORS['text']};
    font-size: 13px;
}}

/* Tool Tips */
QToolTip {{
    background-color: {COLORS['primary']};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* Progress Bar */
QProgressBar {{
    background-color: {COLORS['surface_dark']};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 4px;
}}
"""


def get_component_palette_stylesheet() -> str:
    """Get stylesheet for the component palette.

    Returns:
        CSS/QSS stylesheet string
    """
    return f"""
/* Component Palette Container */
QDockWidget QWidget {{
    background-color: {COLORS['surface']};
}}

/* Component Category Header */
QTreeWidget::item[type="category"] {{
    background-color: {COLORS['primary_light']};
    color: white;
    font-weight: bold;
    padding: 8px;
}}

/* Component Item */
QTreeWidget::item[type="component"] {{
    padding: 6px;
}}

/* Search Box */
QLineEdit#searchBox {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 14px;
}}

QLineEdit#searchBox:focus {{
    border-color: {COLORS['accent']};
}}

/* Action Buttons */
QPushButton#addButton {{
    background-color: {COLORS['success']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px;
    font-weight: bold;
}}

QPushButton#addButton:hover {{
    background-color: {COLORS['success_light']};
}}

QPushButton#refreshButton {{
    background-color: {COLORS['accent']};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px;
    font-weight: bold;
}}

QPushButton#refreshButton:hover {{
    background-color: {COLORS['accent_hover']};
}}
"""


def get_toolbar_stylesheet() -> str:
    """Get stylesheet for toolbars.

    Returns:
        CSS/QSS stylesheet string
    """
    return f"""
/* Toolbar Container */
QWidget#toolbar {{
    background-color: {COLORS['surface']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 4px 8px;
}}

/* Toolbar Buttons */
QWidget#toolbar QPushButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 6px 12px;
    margin: 2px;
}}

QWidget#toolbar QPushButton:hover {{
    background-color: {COLORS['surface_dark']};
    border-color: {COLORS['border']};
}}

QWidget#toolbar QPushButton:checked {{
    background-color: {COLORS['accent']};
    color: white;
}}

/* Wire Type Buttons */
QPushButton#wire24V:checked {{
    background-color: {COLORS['voltage_24vdc']};
    color: white;
}}

QPushButton#wire0V:checked {{
    background-color: {COLORS['voltage_0v']};
    color: white;
}}

QPushButton#wireAC:checked {{
    background-color: {COLORS['voltage_400vac']};
    color: white;
}}
"""


def get_simulation_panel_stylesheet() -> str:
    """Get stylesheet for the simulation panel.

    Returns:
        CSS/QSS stylesheet string
    """
    return f"""
/* Simulation Panel */
QWidget#simulationPanel {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
}}

/* Component List Item - Energized */
QListWidget::item[state="energized"] {{
    background-color: {COLORS['success_bg']};
    border-left: 4px solid {COLORS['energized']};
    color: {COLORS['energized_text']};
}}

/* Component List Item - De-energized */
QListWidget::item[state="de-energized"] {{
    background-color: {COLORS['danger_bg']};
    border-left: 4px solid {COLORS['de_energized']};
    color: {COLORS['de_energized_text']};
}}

/* Component List Item - Unknown */
QListWidget::item[state="unknown"] {{
    background-color: rgba(149, 165, 166, 0.1);
    border-left: 4px solid {COLORS['unknown']};
}}

/* Component List Item - Current Page */
QListWidget::item[current_page="true"] {{
    font-weight: bold;
}}

/* Toggle Button */
QPushButton#toggleButton {{
    background-color: {COLORS['surface_dark']};
    border: 2px solid {COLORS['border']};
    border-radius: 12px;
    padding: 8px 16px;
}}

QPushButton#toggleButton:checked {{
    background-color: {COLORS['success']};
    border-color: {COLORS['success']};
    color: white;
}}

QPushButton#toggleButton:hover {{
    border-color: {COLORS['accent']};
}}

/* Page Filter Label */
QLabel#pageFilterLabel {{
    color: {COLORS['text_secondary']};
    font-size: 11px;
    font-style: italic;
}}

/* Page Count Label */
QLabel#pageCountLabel {{
    color: {COLORS['text_muted']};
    font-size: 11px;
    padding: 2px 6px;
    background-color: {COLORS['surface_dark']};
    border-radius: 4px;
}}
"""


def get_interactive_panel_stylesheet() -> str:
    """Get stylesheet for the interactive simulation panel.

    Returns:
        CSS/QSS stylesheet string
    """
    return f"""
/* Interactive Panel Component List */
QListWidget#componentList {{
    font-family: "Consolas", "Monaco", "Courier New", monospace;
    font-size: 11px;
}}

/* Hint label styling */
QLabel#hintLabel {{
    color: {COLORS['text_muted']};
    font-size: 11px;
    font-style: italic;
    padding: 4px;
}}

/* Component detail text */
QTextEdit#componentDetail {{
    font-family: "Consolas", "Monaco", "Courier New", monospace;
    font-size: 12px;
    background-color: {COLORS['surface_dark']};
}}
"""


def get_wire_colors() -> dict:
    """Get color definitions for wire types.

    Returns:
        Dict mapping wire types to colors
    """
    return {
        '24VDC': COLORS['voltage_24vdc'],
        '0V': COLORS['voltage_0v'],
        '400VAC': COLORS['voltage_400vac'],
        '230VAC': COLORS['voltage_230vac'],
        'PE': '#27AE60',  # Green for protective earth
        'UNKNOWN': COLORS['text_muted'],
    }


def get_component_state_colors() -> dict:
    """Get color definitions for component states.

    Returns:
        Dict mapping states to background and text colors
    """
    return {
        'energized': {
            'background': COLORS['success_bg'],
            'text': COLORS['energized_text'],
            'border': COLORS['energized'],
        },
        'de_energized': {
            'background': COLORS['danger_bg'],
            'text': COLORS['de_energized_text'],
            'border': COLORS['de_energized'],
        },
        'unknown': {
            'background': COLORS['surface_dark'],
            'text': COLORS['text_secondary'],
            'border': COLORS['unknown'],
        },
        'current_page': {
            'background': COLORS['current_page_highlight'],
            'border': COLORS['current_page_border'],
        },
    }


def apply_theme(app) -> None:
    """Apply the complete theme to the application.

    Args:
        app: QApplication instance
    """
    full_stylesheet = get_main_stylesheet()
    full_stylesheet += get_component_palette_stylesheet()
    full_stylesheet += get_toolbar_stylesheet()
    full_stylesheet += get_simulation_panel_stylesheet()
    full_stylesheet += get_interactive_panel_stylesheet()

    app.setStyleSheet(full_stylesheet)
