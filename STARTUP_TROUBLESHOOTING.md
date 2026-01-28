# Startup and Troubleshooting Guide
## Industrial Wiring Diagram Analyzer

This comprehensive guide will help you launch the application, verify features are working, and troubleshoot common issues.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Installation Verification](#installation-verification)
3. [Feature Testing](#feature-testing)
4. [Common Issues and Solutions](#common-issues-and-solutions)
5. [Feature Checklist](#feature-checklist)
6. [Advanced Troubleshooting](#advanced-troubleshooting)

---

## Quick Start

### Launch the Application

**Method 1: Python Module (Recommended)**
```bash
cd /home/liam-oreilly/claude.projects/electricalSchematics
python -m electrical_schematics.main
```

**Method 2: Entry Point**
```bash
electrical_schematics
```

**Method 3: Direct Execution**
```bash
python electrical_schematics/main.py
```

### First Launch Expectations

When the application launches successfully, you should see:

1. **Main Window**: Three-panel layout with PDF viewer, component list, and analysis tools
2. **Menu Bar**: File, Edit, View, Simulation, Help
3. **Tool Bar**: Buttons for Draw Wire, Toggle Component, Trace Circuit
4. **Status Bar**: Ready for PDF loading

**Window Layout:**
```
┌────────────────────────────────────────────────────────────────┐
│ File  Edit  View  Simulation  Help                             │
│ [Open] [Save] [Draw Wire] [Toggle] [Trace] [Simulate]         │
├────────────────┬───────────────────────────┬───────────────────┤
│                │                           │ Interactive Panel │
│  PDF List      │     PDF Viewer            │                   │
│  Navigation    │     (Center Panel)        │ Component List:   │
│                │                           │ [Search filter]   │
│  [No PDFs]     │  [Drop PDF here or        │                   │
│                │   File → Open PDF]        │ □ Component 1     │
│                │                           │ □ Component 2     │
│                │                           │                   │
│                │                           │ [Simulate]        │
│                │                           │ Circuit Details   │
│                │                           │                   │
└────────────────┴───────────────────────────┴───────────────────┘
Status: Ready                                    0 components loaded
```

---

## Installation Verification

### Automated Check

Run the installation check script:

```bash
cd /home/liam-oreilly/claude.projects/electricalSchematics
python check_installation.py
```

**Expected Output:**
```
============================================================
INSTALLATION CHECK - Industrial Wiring Diagram Analyzer
============================================================

Python Environment
------------------------------------------------------------
✓ Python version: 3.13.7
✓ Python executable: .../electrical/bin/python
✓ Platform: linux

Dependency Check
------------------------------------------------------------
✓ PySide6: 6.10.1
✓ PyMuPDF: 1.26.7
✓ networkx: 3.6.1
✓ matplotlib: 3.10.8
✓ numpy: 2.4.1
✓ PIL: 12.1.0
✓ fastapi: 0.128.0
✓ uvicorn: 0.40.0
✓ httpx: 0.28.1
✓ requests: 2.32.5
✓ pytesseract: 0.3.13

Module Import Check
------------------------------------------------------------
✓ electrical_schematics module importable
✓ electrical_schematics.models
✓ electrical_schematics.gui
✓ electrical_schematics.pdf
✓ electrical_schematics.simulation

Critical Files Check
------------------------------------------------------------
✓ electrical_schematics/main.py (769 bytes)
✓ electrical_schematics/gui/main_window.py (72,528 bytes)
✓ electrical_schematics/pdf/auto_loader.py (28,181 bytes)
✓ DRAWER.pdf (888,702 bytes)

============================================================
✅✅✅ INSTALLATION COMPLETE - READY TO RUN ✅✅✅
============================================================
```

### Manual Verification

Check dependencies manually:

```bash
# Check Python version (3.10+ required, 3.13 supported)
python --version

# Check key packages
pip list | grep -E "PySide6|PyMuPDF|networkx|pytesseract"

# Verify module can be imported
python -c "import electrical_schematics; print('OK')"
```

---

## Feature Testing

### Automated Feature Demo

Run the feature demo script to verify all features:

```bash
cd /home/liam-oreilly/claude.projects/electricalSchematics
python demo_all_features.py
```

**Expected Output Summary:**
```
======================================================================
          INDUSTRIAL WIRING DIAGRAM ANALYZER - FEATURE DEMO
======================================================================

✅ DiagramAutoLoader imported
✅ WiringDiagram model imported
✅ InteractiveSimulator imported
✅ Test PDF found: DRAWER.pdf
✅ Format detected: drawer
✅ Components loaded: 24
✅ Components positioned: 24/24
✅ Multi-page components: 15
✅ Wires loaded: 27
✅ Wire paths generated: 6/27
✅ Simulator initialized
✅ Initial simulation: 0 components energized

======================================================================
                    🎉 ALL CORE FEATURES WORKING 🎉
======================================================================
```

### Manual Feature Testing

#### 1. Load DRAWER Format PDF

**Steps:**
1. Launch application: `python -m electrical_schematics.main`
2. Click **File → Open PDF**
3. Select `DRAWER.pdf`
4. Wait 2-5 seconds for auto-analysis

**Expected Console Output:**
```
Loading PDF: DRAWER.pdf
Analyzing format...
✓ DRAWER FORMAT DETECTED
✓ Parsing device tags from pages 26-27...
✓ Found 24 components
✓ Parsing cable routing from pages 28-40...
✓ Found 27 wire connections
✓ Auto-positioning components...
✓ Positioned 24/24 components
✓ Generating wire paths...
✓ Ready for simulation
```

**Expected UI Updates:**
- Right panel: 24 components listed
- Status bar: "24 components, 27 wires loaded"
- PDF viewer: Schematic pages loaded

#### 2. Visual Overlays

**Steps:**
1. After loading DRAWER.pdf
2. Navigate to page 9 in PDF viewer (use page controls)
3. Look for colored rectangles on component tags

**What to See:**
- Green overlays = Energized components (has voltage)
- Red overlays = De-energized components (no voltage)
- Overlays align with component tags like `-K1`, `-U1`, `+DG-M1`
- Overlays scale when zooming in/out

**Troubleshooting:**
- If no overlays visible: Check you're on a schematic page (not TOC or cable diagram)
- Try pages 7-24 for DRAWER.pdf
- Zoom in to ensure overlays render correctly

#### 3. Component List & Interaction

**Steps:**
1. Look at right panel after loading PDF
2. See list of 24 components
3. Try search filter (type "K" to filter relays)
4. Double-click a component

**Expected:**
- Component details dialog opens
- Shows: designation, type, voltage rating, state
- Has toggle button for changeable components
- Has "Query DigiKey" button (if API configured)

#### 4. Component Toggle & State Change

**Steps:**
1. Double-click component `-F2` (circuit breaker)
2. Dialog shows current state: OFF
3. Click toggle button → ON
4. Click OK
5. Watch PDF viewer

**Expected:**
- Overlay color changes from red to green
- Other connected components may change state
- Status bar updates: "Simulation updated"
- Console shows: "Component -F2 state changed: OFF → ON"

**From Test Results:**
```
Testing component toggle...
   Toggling -F2...
✅ After toggle: 2 components energized
✅ Simulation responded: +2 components changed state
```

#### 5. Wire Drawing

**Steps:**
1. Click "Draw Wire" button in toolbar
2. Hover mouse over a component
3. Yellow terminal detection circles should appear
4. Click a terminal to start wire
5. Move to another component
6. Click another terminal to complete

**Expected:**
- Terminal circles appear around components
- Rubber-band line follows cursor
- Wire added to diagram when completed
- Wire appears in wire list

**Troubleshooting:**
- Terminal circles not appearing? Ensure latest code (terminal detection radius fix)
- Detection radius increased from 5px to 15px in recent commits

#### 6. Circuit Tracing

**Steps:**
1. Right-click a component in the list
2. Select "Trace Circuit Path"
3. See highlighted path in viewer

**Expected:**
- Path highlights in yellow/orange
- Shows: Power source → intermediates → target
- Console shows path details

---

## Common Issues and Solutions

### Issue 1: "No module named 'electrical_schematics'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'electrical_schematics'
```

**Causes:**
- Package not installed
- Wrong virtual environment
- Wrong directory

**Solutions:**
```bash
# Solution 1: Install package
cd /home/liam-oreilly/claude.projects/electricalSchematics
pip install -e .

# Solution 2: Activate correct virtual environment
source electrical/bin/activate  # or venv/bin/activate
pip install -e .

# Solution 3: Verify you're in project directory
pwd  # Should show .../electricalSchematics
ls pyproject.toml  # Should exist
```

### Issue 2: Qt Platform Plugin Error

**Symptoms:**
```
qt.qpa.plugin: Could not find the Qt platform plugin "xcb"
```

**Causes:**
- Missing X11 display configuration
- Running on headless server
- Missing Qt dependencies

**Solutions:**
```bash
# Solution 1: Set Qt platform explicitly
export QT_QPA_PLATFORM=xcb
python -m electrical_schematics.main

# Solution 2: For headless systems (use offscreen)
export QT_QPA_PLATFORM=offscreen
# Note: GUI won't display, only for testing

# Solution 3: Install Qt dependencies (Ubuntu/Debian)
sudo apt-get install libxcb-xinerama0 libxkbcommon-x11-0
```

### Issue 3: PyMuPDF Import Failure

**Symptoms:**
```
ImportError: No module named 'fitz'
```

**Causes:**
- PyMuPDF not installed
- Version incompatibility

**Solutions:**
```bash
# Solution 1: Install/upgrade PyMuPDF
pip install --upgrade PyMuPDF>=1.23.0

# Solution 2: Force reinstall
pip install --force-reinstall PyMuPDF

# Verify installation
python -c "import fitz; print(fitz.__version__)"
```

### Issue 4: No Components Loaded from PDF

**Symptoms:**
- PDF opens but component list is empty
- Console shows: "No components found"

**Causes:**
- PDF not in DRAWER or Parts List format
- PDF is image-based (scanned)
- Text extraction failed

**Solutions:**
1. **Check PDF format:**
   - DRAWER format has device tags on pages 26-27
   - Parts List format has parts table with component info
   - Use provided test files: DRAWER.pdf, AO.pdf

2. **Enable OCR for scanned PDFs:**
   - Install Tesseract: `sudo apt-get install tesseract-ocr`
   - PDF will be converted to images and OCR applied

3. **Use manual annotation mode:**
   - Open any PDF
   - Click/drag to select component areas
   - Enter component details manually

### Issue 5: Visual Overlays Not Visible

**Symptoms:**
- Components loaded but no green/red overlays on PDF
- Overlay transparency makes them invisible

**Causes:**
- Viewing wrong page (TOC or cable diagram)
- Auto-placement failed
- Overlays outside viewport
- Overlay toggle disabled

**Solutions:**
1. **Check page number:**
   - Navigate to schematic pages (7-24 for DRAWER.pdf)
   - Avoid TOC (pages 1-5), cable diagrams (pages 28-40)

2. **Verify auto-placement:**
   - Check console for "Positioned X/Y components"
   - If 0 positioned, OCR may have failed

3. **Toggle overlays:**
   - Look for "Show Overlays" toggle in toolbar
   - Ensure it's ON (button highlighted)

4. **Adjust transparency:**
   - Settings → Overlay Transparency
   - Increase opacity from default 30% to 60%

### Issue 6: Wires Not Rendered

**Symptoms:**
- Wires loaded (console shows "27 wires") but not visible
- No lines connecting components

**Causes:**
- Wire paths not generated
- Wire color same as background
- Zoom level too low
- Format detection priority bug (fixed in recent commits)

**Solutions:**
1. **Verify wire paths generated:**
   - Console should show "Wire paths generated: X/Y"
   - If 0 paths, wire routing may have failed

2. **Zoom in:**
   - Wires are thin by default
   - Use zoom controls (+ button or scroll)
   - Wires should be visible at 150% zoom

3. **Check wire color settings:**
   - Red = 24VDC control wires
   - Blue = Ground/0V wires
   - Black = 400VAC power wires
   - Adjust background if color invisible

4. **Pull latest code:**
   ```bash
   git pull origin main
   pip install -e .
   ```
   Recent fix: Format detection priority corrected

### Issue 7: DigiKey Query Error

**Symptoms:**
```
AttributeError: 'SettingsManager' object has no attribute 'get_digikey_config'
```

**Causes:**
- Missing method in older code version
- Settings manager not initialized

**Solutions:**
1. **Pull latest code:**
   ```bash
   git pull origin main
   # Latest commit added get_digikey_config() method
   ```

2. **Configure DigiKey API:**
   - Get API key from DigiKey developer portal
   - Settings → DigiKey → Enter API credentials
   - Note: Query works without error now, but needs valid key for results

### Issue 8: Wire Drawing Terminals Not Detected

**Symptoms:**
- Click "Draw Wire" button
- No yellow terminal circles appear when hovering
- Can't click terminals

**Causes:**
- Terminal detection radius too small (5px in old code)
- Components not positioned correctly

**Solutions:**
1. **Pull latest code:**
   ```bash
   git pull origin main
   # Latest commit increased radius from 5px to 15px
   ```

2. **Verify components have positions:**
   - Check component list shows positions
   - Components at (0, 0) won't have terminals drawn

3. **Zoom in:**
   - Terminal circles are small
   - Zoom to 150-200% for easier clicking

---

## Feature Checklist

Use this checklist to verify all features are working:

### Core Features
- [ ] **Application Launches** - No import errors, GUI appears
- [ ] **PDF Loading** - DRAWER.pdf opens without errors
- [ ] **Format Detection** - Console shows "DRAWER FORMAT DETECTED"
- [ ] **Component Loading** - Right panel shows 24 components
- [ ] **Wire Loading** - Console shows "27 wires loaded"

### Visual Features
- [ ] **Auto-Placement** - Navigate to page 9, see overlays on components
- [ ] **Overlay Colors** - Green for energized, red for de-energized
- [ ] **Overlay Scaling** - Overlays scale when zooming
- [ ] **Wire Rendering** - Lines visible connecting components (may need zoom)
- [ ] **Multi-Page Tracking** - Same component highlighted on multiple pages

### Interactive Features
- [ ] **Component Dialog** - Double-click component, dialog opens
- [ ] **State Toggle** - Change component state, overlay color updates
- [ ] **Search Filter** - Type in search box, list filters correctly
- [ ] **Component Selection** - Click component, details shown below

### Advanced Features
- [ ] **Wire Drawing** - Click "Draw Wire", terminal circles appear
- [ ] **Terminal Detection** - Circles appear when hovering components
- [ ] **Manual Wire Creation** - Click two terminals, wire created
- [ ] **Circuit Tracing** - Right-click component, trace path works
- [ ] **Simulation Update** - Toggle component, simulation recalculates

### API Features (Optional)
- [ ] **DigiKey Query** - No AttributeError when querying
- [ ] **Part Lookup** - DigiKey search returns results (needs API key)
- [ ] **Specification Import** - Import component specs from DigiKey

---

## Advanced Troubleshooting

### Enable Debug Logging

Add logging to see detailed debug information:

```python
# Edit electrical_schematics/main.py
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Then run:
```bash
python -m electrical_schematics.main 2>&1 | tee debug.log
```

### Check Console Output

Key messages to look for on startup:
```
Starting Industrial Wiring Diagram Analyzer...
Qt Platform: xcb
Python: 3.13.7
PySide6: 6.10.1
Loading theme: modern_dark
Main window initialized
Ready for PDF loading
```

On PDF load:
```
Loading: /path/to/DRAWER.pdf
File size: 867.9 KB
Format analysis starting...
DRAWER format detected (confidence: HIGH)
Parsing components from pages 26-27...
Extracted 24 devices
Parsing cables from pages 28-40...
Extracted 27 connections
Auto-placement: Analyzing pages 7-24...
OCR confidence: 0.85
Positioned 24/24 components
Wire routing: Manhattan style
Generated 6 wire paths (21 cross-page)
Simulation initialized
```

### Performance Monitoring

Monitor resource usage:

```bash
# Memory usage
ps aux | grep python | grep electrical

# CPU usage
top -p $(pgrep -f electrical_schematics)

# Expected typical usage:
# Memory: 200-400 MB for medium diagrams
# CPU: 5-15% when idle, 40-80% during PDF load
```

### Verify Git Commits

Ensure you have latest bug fixes:

```bash
git log --oneline -10
```

Recent important commits:
- `Terminal detection radius fix` - Wire drawing terminals
- `DigiKey config method fix` - get_digikey_config() added
- `Format detection priority fix` - DRAWER vs Parts List priority
- `Visual overlay system` - Component highlighting
- `Interactive simulation` - Component toggle and state

If missing commits:
```bash
git pull origin main
pip install -e . --force-reinstall
```

### Test Individual Components

Test parsers independently:

```bash
# Test DRAWER parser
python -c "
from electrical_schematics.pdf.drawer_parser import DrawerParser
from pathlib import Path
parser = DrawerParser(Path('DRAWER.pdf'))
diagram = parser.parse()
print(f'Components: {len(diagram.components)}')
print(f'Wires: {len(diagram.wires)}')
"

# Test auto-loader
python -c "
from electrical_schematics.pdf.auto_loader import DiagramAutoLoader
from pathlib import Path
diagram, fmt = DiagramAutoLoader.load_diagram(Path('DRAWER.pdf'))
print(f'Format: {fmt}')
print(f'Components: {len(diagram.components)}')
"
```

### Run Unit Tests

Run the test suite:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_voltage_simulator.py -v

# Run with coverage
pytest --cov=electrical_schematics

# Run tests for specific feature
pytest -k "interactive" -v
```

---

## Getting Help

### If Features Still Not Working

1. **Run diagnostic scripts:**
   ```bash
   python check_installation.py
   python demo_all_features.py
   ```

2. **Check versions:**
   ```bash
   python --version
   pip list | grep -E "PySide6|PyMuPDF|networkx"
   ```

3. **Verify latest code:**
   ```bash
   git log --oneline -5
   git status
   ```

4. **Reinstall dependencies:**
   ```bash
   pip install -e . --force-reinstall
   ```

5. **Check documentation:**
   - `QUICK_START.md` - Quick start guide
   - `CLAUDE.md` - Complete system documentation
   - `INTERACTIVE_SIMULATION.md` - Simulation details
   - `VISUAL_OVERLAY.md` - Overlay system guide

### Reporting Issues

When reporting problems, include:

1. **Environment:**
   - Python version: `python --version`
   - OS: `uname -a`
   - Dependencies: `pip list > deps.txt`

2. **Error Output:**
   - Full console output
   - Error traceback
   - Screenshots of issue

3. **Steps to Reproduce:**
   - PDF file used
   - Actions taken
   - Expected vs actual behavior

4. **Diagnostic Output:**
   ```bash
   python check_installation.py > install.txt
   python demo_all_features.py > features.txt
   ```

### Additional Resources

- **Examples:**
  - `examples/analyze_drawer_diagram.py` - CLI parsing
  - `examples/interactive_simulation_test.py` - Simulation API
  - `examples/visual_overlay_test.py` - Overlay testing

- **Documentation:**
  - `electrical_schematics/pdf/README_DRAWER.md` - DRAWER format spec
  - Architecture diagrams in CLAUDE.md
  - Test coverage reports in htmlcov/

---

## Success Criteria

Your installation is fully working if you can:

1. ✅ Launch application without errors
2. ✅ Load DRAWER.pdf automatically (24 components, 27 wires)
3. ✅ See visual overlays on page 9 (green/red rectangles)
4. ✅ Double-click component and open details dialog
5. ✅ Toggle component state and see overlay color change
6. ✅ Click "Draw Wire" and see terminal detection circles
7. ✅ Right-click component and trace circuit path
8. ✅ Filter component list with search box
9. ✅ Zoom in/out and overlays scale correctly
10. ✅ Query DigiKey without AttributeError

If all 10 items work, congratulations - the application is fully operational!

---

## Next Steps

After verifying everything works:

1. **Explore Example Scripts:**
   - Try `examples/analyze_drawer_diagram.py` for CLI parsing
   - Test `examples/interactive_simulation_test.py` for simulation API

2. **Load Your Own Diagrams:**
   - Start with DRAWER format if available
   - Try Parts List auto-detection for other formats
   - Use manual annotation for custom PDFs

3. **Customize Settings:**
   - Overlay colors and transparency
   - Terminal detection radius
   - Simulation propagation settings
   - PDF rendering quality

4. **Advanced Features:**
   - Multi-voltage circuit analysis
   - Fault diagnosis mode
   - Custom component library
   - Wire path optimization algorithms

5. **Integration:**
   - DigiKey API for part specifications
   - PLC programming verification
   - Export to CAD formats
   - Automated test generation

Happy analyzing!
