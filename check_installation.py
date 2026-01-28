#!/usr/bin/env python3
"""Check if all dependencies and features are properly installed."""

import sys
from pathlib import Path

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60)

def print_section(text):
    """Print a section header."""
    print(f"\n{text}")
    print("-" * 60)

print_header("INSTALLATION CHECK - Industrial Wiring Diagram Analyzer")

# Check Python version
print_section("Python Environment")
print(f"✓ Python version: {sys.version.split()[0]}")
print(f"✓ Python executable: {sys.executable}")
print(f"✓ Platform: {sys.platform}")

if sys.version_info < (3, 10):
    print("  ⚠ WARNING: Python 3.10+ recommended for best compatibility")
elif sys.version_info >= (3, 13):
    print("  ℹ INFO: Python 3.13 detected - some dependencies may need updates")

# Check dependencies
print_section("Dependency Check")

dependencies = {
    "PySide6": ("PySide6", "6.6.0"),
    "PyMuPDF": ("fitz", "1.23.0"),  # PyMuPDF imports as 'fitz'
    "networkx": ("networkx", "3.2"),
    "matplotlib": ("matplotlib", "3.8.0"),
    "numpy": ("numpy", "1.26.0"),
    "PIL": ("PIL", "10.0.0"),  # Pillow
    "fastapi": ("fastapi", "0.109.0"),
    "uvicorn": ("uvicorn", "0.27.0"),
    "httpx": ("httpx", "0.26.0"),
    "requests": ("requests", "2.31.0"),
    "pytesseract": ("pytesseract", "0.3.10"),
}

missing_deps = []
outdated_deps = []

for display_name, (import_name, min_version) in dependencies.items():
    try:
        mod = __import__(import_name)
        version = getattr(mod, "__version__", "unknown")
        print(f"✓ {display_name}: {version}")

        # Check version if possible
        if version != "unknown":
            try:
                from packaging import version as pkg_version
                if pkg_version.parse(version) < pkg_version.parse(min_version):
                    outdated_deps.append((display_name, version, min_version))
                    print(f"  ⚠ Outdated (minimum: {min_version})")
            except:
                pass  # Skip version comparison if packaging not available

    except ImportError as e:
        print(f"✗ {display_name}: NOT INSTALLED")
        missing_deps.append(display_name)

# Check optional dependencies
print_section("Optional Dependencies")
optional_deps = {
    "pytest": ("pytest", "Testing framework"),
    "black": ("black", "Code formatter"),
    "ruff": ("ruff", "Linter"),
    "mypy": ("mypy", "Type checker"),
}

for display_name, (import_name, description) in optional_deps.items():
    try:
        mod = __import__(import_name)
        version = getattr(mod, "__version__", "unknown")
        print(f"✓ {display_name}: {version} ({description})")
    except ImportError:
        print(f"○ {display_name}: Not installed ({description})")

# Check module import
print_section("Module Import Check")

try:
    import electrical_schematics
    print("✓ electrical_schematics module importable")

    # Try importing key submodules
    submodules = [
        "electrical_schematics.models",
        "electrical_schematics.gui",
        "electrical_schematics.pdf",
        "electrical_schematics.simulation",
    ]

    for submod in submodules:
        try:
            __import__(submod)
            print(f"✓ {submod}")
        except ImportError as e:
            print(f"✗ {submod}: {e}")

except ImportError as e:
    print(f"✗ electrical_schematics module: {e}")
    print("\n  Fix: Run 'pip install -e .' from project directory")

# Check critical files
print_section("Critical Files Check")

base = Path("/home/liam-oreilly/claude.projects/electricalSchematics")
critical_files = [
    "electrical_schematics/main.py",
    "electrical_schematics/gui/main_window.py",
    "electrical_schematics/gui/pdf_viewer.py",
    "electrical_schematics/gui/interactive_panel.py",
    "electrical_schematics/pdf/auto_loader.py",
    "electrical_schematics/pdf/drawer_parser.py",
    "electrical_schematics/pdf/parts_list_parser.py",
    "electrical_schematics/simulation/interactive_simulator.py",
    "electrical_schematics/models/industrial_component.py",
    "pyproject.toml",
    "DRAWER.pdf",
    "QUICK_START.md",
]

missing_files = []

for file_path in critical_files:
    full_path = base / file_path
    if full_path.exists():
        size = full_path.stat().st_size
        print(f"✓ {file_path} ({size:,} bytes)")
    else:
        print(f"✗ {file_path} NOT FOUND")
        missing_files.append(file_path)

# Check example scripts
print_section("Example Scripts Check")

example_scripts = [
    "examples/analyze_drawer_diagram.py",
    "examples/interactive_simulation_test.py",
    "examples/visual_overlay_test.py",
]

for script in example_scripts:
    full_path = base / script
    if full_path.exists():
        print(f"✓ {script}")
    else:
        print(f"○ {script} (optional)")

# Check for test PDF files
print_section("Test PDF Files")

test_pdfs = [
    "DRAWER.pdf",
    "AO.pdf",
]

for pdf in test_pdfs:
    full_path = base / pdf
    if full_path.exists():
        size = full_path.stat().st_size / (1024 * 1024)  # MB
        print(f"✓ {pdf} ({size:.1f} MB)")
    else:
        print(f"○ {pdf} (optional test file)")

# Summary
print_header("INSTALLATION SUMMARY")

all_ok = True

if missing_deps:
    print(f"\n❌ MISSING DEPENDENCIES ({len(missing_deps)}):")
    for dep in missing_deps:
        print(f"   - {dep}")
    print("\n   Fix: pip install -e .")
    all_ok = False
else:
    print("\n✅ All required dependencies installed")

if outdated_deps:
    print(f"\n⚠ OUTDATED DEPENDENCIES ({len(outdated_deps)}):")
    for dep, current, minimum in outdated_deps:
        print(f"   - {dep}: {current} (need {minimum}+)")
    print("\n   Fix: pip install --upgrade -e .")
    all_ok = False

if missing_files:
    print(f"\n❌ MISSING FILES ({len(missing_files)}):")
    for file in missing_files:
        print(f"   - {file}")
    all_ok = False
else:
    print("\n✅ All critical files present")

# Final verdict
print("\n" + "=" * 60)
if all_ok:
    print("✅✅✅ INSTALLATION COMPLETE - READY TO RUN ✅✅✅")
    print("\nNext steps:")
    print("  1. Launch application: python -m electrical_schematics.main")
    print("  2. Run feature demo: python demo_all_features.py")
    print("  3. Read quick start: cat QUICK_START.md")
else:
    print("❌ INSTALLATION INCOMPLETE")
    print("\nPlease fix the issues above, then run this check again.")

print("=" * 60 + "\n")

# Return exit code
sys.exit(0 if all_ok else 1)
