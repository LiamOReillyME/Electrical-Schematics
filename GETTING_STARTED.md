# Getting Started - Industrial Wiring Diagram Analyzer

Welcome! This guide will help you quickly get up and running with the Industrial Wiring Diagram Analyzer.

## New User? Start Here!

### Step 1: Verify Installation

Run the automated installation check:

```bash
cd /home/liam-oreilly/claude.projects/electricalSchematics
python check_installation.py
```

✅ If you see "INSTALLATION COMPLETE - READY TO RUN", proceed to Step 2.

❌ If there are errors, see [STARTUP_TROUBLESHOOTING.md](STARTUP_TROUBLESHOOTING.md#installation-verification) for solutions.

### Step 2: Test Features

Run the feature demo to verify everything works:

```bash
python demo_all_features.py
```

✅ If you see "ALL CORE FEATURES WORKING", proceed to Step 3.

❌ If features aren't working, see [STARTUP_TROUBLESHOOTING.md](STARTUP_TROUBLESHOOTING.md#feature-testing) for fixes.

### Step 3: Launch the Application

Start the GUI:

```bash
python -m electrical_schematics.main
```

You should see the main window with three panels:
- **Left**: PDF navigation
- **Center**: PDF viewer with interactive schematic
- **Right**: Component list and simulation controls

### Step 4: Load a Test PDF

1. Click **File → Open PDF**
2. Select `DRAWER.pdf`
3. Wait 2-5 seconds for auto-analysis

You should see:
- ✅ "DRAWER FORMAT DETECTED" in console
- ✅ 24 components listed in right panel
- ✅ Status bar shows "24 components, 27 wires loaded"

### Step 5: Verify Visual Features

1. Navigate to **page 9** in the PDF viewer
2. Look for colored overlays on component tags:
   - 🟢 **Green** = Energized (has voltage)
   - 🔴 **Red** = De-energized (no voltage)

3. **Double-click** a component (e.g., `-F2`)
   - Details dialog should open
   - Shows type, voltage, state

4. Click the **toggle button** to change state
   - Overlay color should change in PDF viewer
   - Other components may change state due to circuit logic

## Documentation Index

### Quick References
- **[QUICK_START.md](QUICK_START.md)** - Comprehensive quick start guide
  - Installation
  - Launch methods
  - Feature walkthroughs
  - Keyboard shortcuts
  - Success criteria checklist

### Troubleshooting
- **[STARTUP_TROUBLESHOOTING.md](STARTUP_TROUBLESHOOTING.md)** - Complete troubleshooting guide
  - Common issues and solutions
  - Feature verification checklist
  - Advanced debugging
  - Error message reference

### Feature Documentation
- **[CLAUDE.md](CLAUDE.md)** - Complete system documentation
  - Architecture overview
  - Development commands
  - Module responsibilities
  - Testing guidelines

- **[INTERACTIVE_SIMULATION.md](INTERACTIVE_SIMULATION.md)** - Simulation engine details
  - Dual-circuit architecture (24VDC control + 400VAC power)
  - Component toggling
  - Circuit path tracing
  - State explanation

- **[VISUAL_OVERLAY.md](VISUAL_OVERLAY.md)** - Visual overlay system
  - How overlays work
  - Coordinate mapping
  - Real-time updates
  - Customization options

### Format Specifications
- **[electrical_schematics/pdf/README_DRAWER.md](electrical_schematics/pdf/README_DRAWER.md)** - DRAWER format specification
  - Device tag list structure
  - Cable routing tables
  - Terminal reference format
  - Cross-page wire tracing

## Common Questions

### "I don't see any features working"

**Most likely cause:** Application launched but PDF not loaded or wrong format

**Solution:**
1. Ensure you're using the test file `DRAWER.pdf` (provided)
2. Click File → Open PDF and select DRAWER.pdf
3. Wait for console message "DRAWER FORMAT DETECTED"
4. Check right panel for component list (should show 24 items)

See: [STARTUP_TROUBLESHOOTING.md - Issue 4](STARTUP_TROUBLESHOOTING.md#issue-4-no-components-loaded-from-pdf)

### "Components loaded but no overlays visible"

**Most likely cause:** Viewing wrong page (TOC or cable diagram instead of schematic)

**Solution:**
1. Use page navigation to go to page 9
2. Schematic pages are 7-24 in DRAWER.pdf
3. Avoid pages 1-6 (TOC), 26-27 (device list), 28-40 (cable tables)

See: [STARTUP_TROUBLESHOOTING.md - Issue 5](STARTUP_TROUBLESHOOTING.md#issue-5-visual-overlays-not-visible)

### "Can't draw wires - no terminal circles appear"

**Most likely cause:** Old code version (terminal detection radius fix needed)

**Solution:**
```bash
git pull origin main
pip install -e .
```

See: [STARTUP_TROUBLESHOOTING.md - Issue 8](STARTUP_TROUBLESHOOTING.md#issue-8-wire-drawing-terminals-not-detected)

### "AttributeError when querying DigiKey"

**Most likely cause:** Old code version (get_digikey_config method missing)

**Solution:**
```bash
git pull origin main
```

See: [STARTUP_TROUBLESHOOTING.md - Issue 7](STARTUP_TROUBLESHOOTING.md#issue-7-digikey-query-error)

## Feature Highlights

### Automatic Format Detection
- **DRAWER format**: Industrial electrical diagrams with device tags and cable tables
- **Parts List format**: PDFs with component parts lists
- **Manual mode**: Annotate any PDF manually

### Visual Overlays
- Real-time color-coded highlighting
- Green = energized, Red = de-energized
- Multi-page component tracking
- Zoom-adaptive rendering

### Interactive Simulation
- Dual-circuit support (24VDC control + 400VAC power)
- Component toggling (relays, contactors, switches, fuses)
- Circuit path tracing
- State explanation

### Wire Management
- Auto-generated wire routing (Manhattan style)
- Manual wire drawing with terminal detection
- Voltage level color coding
- Cross-page wire tracing

## System Requirements

### Python
- **Minimum:** Python 3.10
- **Recommended:** Python 3.11 or 3.12
- **Supported:** Python 3.13 (may need dependency updates)

### Dependencies
All dependencies auto-installed with `pip install -e .`

**Core:**
- PySide6 ≥ 6.6.0 (Qt GUI framework)
- PyMuPDF ≥ 1.23.0 (PDF rendering)
- networkx ≥ 3.2 (Circuit graph modeling)

**Optional:**
- pytesseract ≥ 0.3.10 (OCR for scanned PDFs)
- DigiKey API credentials (for part lookup)

### Platform
- **Linux:** Full support (tested on Ubuntu 20.04+)
- **Windows:** Full support (tested on Windows 10/11)
- **macOS:** Full support (tested on macOS 12+)

### Display
- GUI requires X11 server (Linux) or native display
- Headless mode not supported (PDF rendering requires display)

## Test Results

### Installation Check Results
```bash
cat installation_check_results.txt
```

Output summary:
- ✅ Python 3.13.7
- ✅ All required dependencies installed
- ✅ All critical files present
- ✅ Modules importable

### Feature Demo Results
```bash
cat feature_demo_results.txt
```

Output summary:
- ✅ Format detection: DRAWER
- ✅ 24 components loaded and positioned
- ✅ 27 wire connections loaded
- ✅ 6 wire paths generated (21 cross-page)
- ✅ Simulation engine functional
- ✅ Component toggling works (+2 components energized on toggle)

## Example Workflows

### Workflow 1: Load and Analyze DRAWER Diagram

```bash
# 1. Launch application
python -m electrical_schematics.main

# 2. Load PDF
File → Open PDF → Select DRAWER.pdf

# 3. Navigate to schematic page
Page controls → Go to page 9

# 4. View component details
Double-click -F2 circuit breaker → See voltage: 230VAC

# 5. Toggle component
Click toggle button → OFF → ON

# 6. Observe results
Watch overlay change from red to green
See connected components energize
```

### Workflow 2: Trace Circuit Path

```bash
# 1. Load DRAWER.pdf (as above)

# 2. Right-click component
Right-click -A1 (PLC) in component list

# 3. Select trace option
Trace Circuit Path

# 4. View results
Path highlighted in PDF viewer
Console shows: 24V → -G1 → -A1
```

### Workflow 3: Manual Wire Drawing

```bash
# 1. Load any PDF

# 2. Activate draw mode
Click "Draw Wire" button in toolbar

# 3. Select start terminal
Hover over component → Yellow circles appear
Click terminal to start

# 4. Select end terminal
Move to another component
Click terminal to complete

# 5. Verify wire
Check wire list in right panel
Wire should appear with endpoints
```

### Workflow 4: Command-Line Analysis

```bash
# Use examples scripts for non-GUI analysis

# Analyze DRAWER format
python examples/analyze_drawer_diagram.py

# Test interactive simulation
python examples/interactive_simulation_test.py

# Test visual overlays
python examples/visual_overlay_test.py
```

## Development Setup

For developers who want to modify the application:

### Install Dev Dependencies
```bash
pip install -e ".[dev]"
```

Includes:
- pytest (testing)
- black (code formatting)
- ruff (linting)
- mypy (type checking)

### Run Tests
```bash
# All tests
pytest

# Specific module
pytest tests/test_voltage_simulator.py -v

# With coverage
pytest --cov=electrical_schematics
```

### Code Quality
```bash
# Format code
black .

# Lint code
ruff check .

# Type check
mypy electrical_schematics
```

See: [CLAUDE.md - Development Commands](CLAUDE.md#development-commands)

## What's Next?

After verifying the application works:

1. **Explore Features:**
   - Try all interactive features listed in [QUICK_START.md](QUICK_START.md#testing-features)
   - Test with different PDF formats
   - Experiment with manual annotation

2. **Load Your Diagrams:**
   - Start with DRAWER format if available
   - Try Parts List auto-detection
   - Use manual mode for custom PDFs

3. **Customize Settings:**
   - Overlay colors and transparency
   - Terminal detection radius
   - Simulation parameters

4. **Read Advanced Docs:**
   - [INTERACTIVE_SIMULATION.md](INTERACTIVE_SIMULATION.md) - Deep dive into simulation
   - [VISUAL_OVERLAY.md](VISUAL_OVERLAY.md) - Overlay system details
   - [AUTO_PLACEMENT_ARCHITECTURE.md](AUTO_PLACEMENT_ARCHITECTURE.md) - Auto-placement algorithm

## Need Help?

### Check Documentation First
1. **[QUICK_START.md](QUICK_START.md)** - Quick how-to guides
2. **[STARTUP_TROUBLESHOOTING.md](STARTUP_TROUBLESHOOTING.md)** - Problem solving
3. **[CLAUDE.md](CLAUDE.md)** - Complete reference

### Run Diagnostics
```bash
# Check installation
python check_installation.py

# Test features
python demo_all_features.py
```

### Verify Latest Code
```bash
# Check what version you have
git log --oneline -5

# Pull latest updates
git pull origin main
pip install -e .
```

### Report Issues
When reporting problems, include:
- Output of `check_installation.py`
- Output of `demo_all_features.py`
- Console output with errors
- Steps to reproduce

## Success!

If you've completed all steps above and see:
- ✅ Application launches without errors
- ✅ DRAWER.pdf loads with 24 components
- ✅ Visual overlays visible on page 9
- ✅ Component toggle changes overlay colors
- ✅ Wire drawing shows terminal circles

**Congratulations! The application is fully operational.**

You're ready to start analyzing industrial wiring diagrams!

---

*For questions or issues, see [STARTUP_TROUBLESHOOTING.md](STARTUP_TROUBLESHOOTING.md)*
