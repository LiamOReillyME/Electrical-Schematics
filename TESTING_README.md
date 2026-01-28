# Auto-Placement Testing Documentation

This directory contains comprehensive tests for validating the auto-placement feature on problematic PDF pages.

## Problem Statement

Users reported that auto-placement was not working correctly on pages 9, 10, 15, 16, 19, 20, and 22 of DRAWER.pdf. This test suite was created to:

1. Identify the root cause of the problem
2. Provide concrete data for backend engineers to fix the issue
3. Enable regression testing after the fix
4. Serve as validation for future auto-placement improvements

## Test Results Summary

### ✅ Tag Detection: 100% Success
All 108 expected device tags were successfully found.

### ❌ Page Selection: ~50% Failure
Tags were found but on the **WRONG PAGES**. The algorithm selected the first high-confidence match instead of considering page context.

**Root Cause:** Multi-page tags (e.g., `-K1` appears on 67 pages) are not handled with page awareness. The algorithm selects page 8 when the user expects page 9.

## Test Files

### Core Test Suite

#### `test_auto_placement_pages.py` - Main Test Script
Comprehensive validation of auto-placement accuracy.

**What it tests:**
- Whether expected tags are found anywhere in PDF
- Ground truth validation against manually verified data
- Root cause analysis for missed tags
- Per-page accuracy reporting

**Usage:**
```bash
# Run all problematic pages
python test_auto_placement_pages.py

# Test specific page (1-indexed)
python test_auto_placement_pages.py --page 9

# Generate debug visualizations
python test_auto_placement_pages.py --debug
```

**Output:**
- Console: Per-page results and summary
- `AUTO_PLACEMENT_ACCURACY_TEST.md`: Detailed report
- `auto_placement_test_results.json`: Machine-readable results
- `placement_test_debug/`: Debug images (if --debug used)

#### `test_position_accuracy.py` - Page Selection Validator
Tests that tags are found on the CORRECT pages (not just somewhere).

**What it tests:**
- Whether tags are on expected pages
- Multi-page component detection
- Discovery of all tags on each page

**Usage:**
```bash
python test_position_accuracy.py
```

**Output:**
- Console: Position validation results
- `position_accuracy_issues.json`: Issues found (if any)

### Helper Tools

#### `extract_tags_batch.py` - Ground Truth Generator
Non-interactive tool for extracting device tags from PDF pages.

**What it does:**
- Automatically extracts all device tags from problematic pages
- Generates ground truth data in Python dictionary format
- Provides per-page summary statistics

**Usage:**
```bash
python extract_tags_batch.py > ground_truth_output.txt
```

#### `collect_ground_truth.py` - Interactive Collector
Interactive helper for manual ground truth verification.

**What it does:**
- Displays potential tags found on each page
- Allows manual review and editing
- Generates Python code for GROUND_TRUTH dictionary

**Usage:**
```bash
# Interactive mode (requires user input)
python collect_ground_truth.py

# Analyze specific page
python collect_ground_truth.py --page 9
```

**Note:** This tool requires interactive input and won't work in non-interactive environments.

## Test Reports

### `AUTO_PLACEMENT_ACCURACY_TEST.md` - Main Report
**Size:** 16KB | **Audience:** All stakeholders

Comprehensive test report with:
- Test 1: Tag detection results (100% pass)
- Test 2: Page selection results (50% failure)
- Root cause analysis with examples
- Impact assessment (user experience, functional, business)
- 4 proposed solutions with pros/cons
- Recommended action plan with effort estimates
- Success metrics and validation test cases
- Appendices with ground truth data and tag frequency analysis

**Start here for understanding the problem.**

### `AUTO_PLACEMENT_DIAGNOSTIC_DETAILED.md` - Technical Deep-Dive
**Size:** 9.3KB | **Audience:** Backend engineers

Detailed technical analysis including:
- Example walkthrough (-K1 on 67 pages)
- Algorithm flaw explanation with code snippets
- Why tags appear on multiple pages (DRAWER format specifics)
- Proposed solutions with implementation examples
- Test case for fix validation
- Tag frequency data and cross-reference patterns

**Best for implementation guidance.**

### `AUTO_PLACEMENT_TEST_SUMMARY.md` - Quick Reference
**Size:** 9.6KB | **Audience:** All stakeholders

Quick reference guide with:
- List of all test deliverables
- Test results summary
- Key findings
- Recommendations (immediate, medium-term, long-term)
- How to use tests (for backend engineers, QA, product managers)
- Quick command reference

**Use for quick lookup and command examples.**

## Test Data

### `auto_placement_test_results.json`
Machine-readable test results for CI/CD integration.

**Format:**
```json
{
  "summary": {
    "test_date": "2026-01-28T16:51:24.030762",
    "pages_tested": 7,
    "total_expected": 108,
    "total_found": 108,
    "overall_accuracy": 1.0,
    "page_results": [...]
  },
  "analysis": {
    "root_causes": [...],
    "tag_details": {...}
  }
}
```

### `position_accuracy_issues.json` (generated if issues found)
Detailed issue tracking for position validation failures.

**Format:**
```json
[
  {
    "tag": "-K1",
    "expected_page": 9,
    "found_page": 8,
    "type": "wrong_page",
    "severity": "high"
  }
]
```

## Quick Start

### For First-Time Users

1. **Understand the problem:**
   ```bash
   cat AUTO_PLACEMENT_TEST_SUMMARY.md
   ```

2. **Run the tests:**
   ```bash
   python test_auto_placement_pages.py
   python test_position_accuracy.py
   ```

3. **Review detailed results:**
   ```bash
   cat AUTO_PLACEMENT_ACCURACY_TEST.md
   ```

### For Backend Engineers Implementing Fix

1. **Read technical details:**
   ```bash
   cat AUTO_PLACEMENT_DIAGNOSTIC_DETAILED.md
   ```

2. **Run tests to see current behavior:**
   ```bash
   python test_position_accuracy.py 2>&1 | grep "WARNING"
   ```

3. **Implement fix** (see Solutions in reports)

4. **Validate fix:**
   ```bash
   python test_auto_placement_pages.py
   python test_position_accuracy.py
   # Should show >95% page accuracy
   ```

### For QA Engineers

1. **Add to CI/CD pipeline:**
   ```yaml
   test:
     script:
       - python test_auto_placement_pages.py
       - python test_position_accuracy.py
   ```

2. **Run regression tests:**
   ```bash
   python test_auto_placement_pages.py
   # Check auto_placement_test_results.json
   ```

3. **User acceptance testing:**
   - Open GUI to problematic page
   - Click "Auto-place components"
   - Verify overlays on correct page

## Ground Truth Data

The test suite uses manually verified ground truth data for 7 problematic pages:

| Page | Title | Tags | Panel (-) | Field (+) |
|------|-------|------|-----------|-----------|
| 9 | Principle of safety circuit | 19 | 13 | 6 |
| 10 | Block diagram | 34 | 20 | 14 |
| 15 | Power feed AC | 16 | 12 | 4 |
| 16 | Power supply DC | 10 | 10 | 0 |
| 19 | Contactor control | 12 | 12 | 0 |
| 20 | Contactor control | 8 | 8 | 0 |
| 22 | Extractor motor | 9 | 6 | 3 |
| **Total** | | **108** | **81** | **27** |

Ground truth was extracted using:
1. Automatic extraction via `extract_tags_batch.py`
2. Manual verification (visual inspection of PDF)
3. Exclusion of cross-reference tags (blue navigation text)

## Key Findings

### Tag Frequency Analysis

**Most problematic tags** (appear on many pages):
- `-K1`: 67 pages - Main contactor, appears everywhere
- `-K2`: 14 pages - Secondary contactor
- `-K3`: 6 pages - Tertiary contactor
- `-U1`: 5 pages - Control module

**Least problematic tags** (appear on few pages):
- `-F7`, `-SH`, `-WM21`: 1-2 pages each
- Field devices (`+DG-*`): Usually 1-3 pages

**Insight:** Common components have the worst accuracy because they appear in multiple contexts (overview diagrams, schematics, connection tables, cross-references).

### Why Tags Appear Multiple Times

In DRAWER-format PDFs:
1. **Overview diagrams** (pages 8-10): System architecture block diagrams
2. **Detailed schematics** (pages 14-22): Component-level circuit diagrams
3. **Connection tables** (pages 28-40): Terminal wiring lists
4. **Cross-references**: "Connects to -K1" annotations throughout

All are technically correct text matches, but only the detailed schematic location is useful for visual overlays.

## Recommended Solution

### Phase 1: Quick Fix (2-3 hours)
Add `preferred_page` parameter to `find_positions()`:

```python
result = finder.find_positions(
    device_tags=["-K1", "-K2"],
    preferred_page=8  # User viewing page 9 (0-indexed)
)
```

When `preferred_page` is specified, positions on that page get a 10x confidence boost.

### Phase 2: Page Type Weighting (4-6 hours)
Prefer schematic pages over reference pages:

```python
PAGE_WEIGHTS = {
    'Schematic diagram': 10.0,
    'Block diagram': 5.0,
    'Cable diagram': 1.0,
    'Device tag': 0.1
}
```

### Phase 3: Spatial Clustering (6-8 hours)
Identify "main" component location via position clustering, distinguishing schematic regions from reference tables.

**Total estimated effort:** 12-17 hours

## Success Metrics

After implementing fixes:
1. **Page accuracy:** >95% when `preferred_page` specified
2. **Auto accuracy:** >80% without page hint (using heuristics)
3. **User satisfaction:** Visual overlays on correct pages
4. **Multi-page handling:** Clear strategy for ambiguous cases

## CI/CD Integration

### Automated Testing

Add to your CI pipeline:

```yaml
test_auto_placement:
  stage: test
  script:
    - python test_auto_placement_pages.py --report-only
    - python test_position_accuracy.py
  artifacts:
    paths:
      - AUTO_PLACEMENT_ACCURACY_TEST.md
      - auto_placement_test_results.json
      - position_accuracy_issues.json
    reports:
      junit: test-results.xml
```

### Quality Gates

Set quality thresholds:

```yaml
quality_gate:
  - tag_detection_accuracy >= 95%
  - page_selection_accuracy >= 90%
  - critical_components_accuracy >= 95%
```

## Troubleshooting

### Test Fails with "PDF not found"
```bash
# Ensure DRAWER.pdf is in examples/ directory
ls examples/DRAWER.pdf

# Or specify path explicitly
python test_auto_placement_pages.py --pdf /path/to/DRAWER.pdf
```

### Test Runs but Shows 0% Accuracy
Check that ground truth data is filled in (not placeholder values).

### Want to Test Different Pages
Edit `GROUND_TRUTH` dictionary in `test_auto_placement_pages.py` or use `extract_tags_batch.py` to generate new ground truth.

### Need Debug Visualizations
```bash
python test_auto_placement_pages.py --debug
# Check placement_test_debug/ directory for images
```

## Contributing

### Adding New Test Pages

1. **Extract tags:**
   ```bash
   python extract_tags_batch.py
   ```

2. **Manually verify** by opening PDF in viewer

3. **Update ground truth** in `test_auto_placement_pages.py`:
   ```python
   GROUND_TRUTH = {
       # ... existing entries ...
       23: {
           'title': 'New Page Title',
           'tags': ['-X1', '-X2', '+Field-Tag']
       }
   }
   ```

4. **Run tests:**
   ```bash
   python test_auto_placement_pages.py --page 24  # 1-indexed
   ```

### Adding New Test Cases

See test scripts for examples. Each test should:
- Have clear documentation
- Use ground truth data for validation
- Generate actionable reports
- Be reproducible

## File Locations

All test files are in the project root:

```
/home/liam-oreilly/claude.projects/electricalSchematics/
├── test_auto_placement_pages.py          # Main test suite
├── test_position_accuracy.py             # Page selection validator
├── extract_tags_batch.py                 # Ground truth generator
├── collect_ground_truth.py               # Interactive collector
├── AUTO_PLACEMENT_ACCURACY_TEST.md       # Main report (16KB)
├── AUTO_PLACEMENT_DIAGNOSTIC_DETAILED.md # Technical deep-dive (9.3KB)
├── AUTO_PLACEMENT_TEST_SUMMARY.md        # Quick reference (9.6KB)
├── auto_placement_test_results.json      # Machine-readable results
├── position_accuracy_issues.json         # Issues found (if any)
└── placement_test_debug/                 # Debug images (if generated)
```

## References

- **Component Position Finder:** `electrical_schematics/pdf/component_position_finder.py`
- **DRAWER Format Docs:** `electrical_schematics/pdf/README_DRAWER.md`
- **Project Documentation:** `CLAUDE.md`

## Questions?

For questions about:
- **Test methodology:** See `AUTO_PLACEMENT_ACCURACY_TEST.md`
- **Technical implementation:** See `AUTO_PLACEMENT_DIAGNOSTIC_DETAILED.md`
- **Quick commands:** See `AUTO_PLACEMENT_TEST_SUMMARY.md`
- **Code details:** Review test script docstrings and inline comments

---

**Test Suite Version:** 1.0
**Last Updated:** 2026-01-28
**Status:** ✅ Complete and validated
**Issue:** ❌ Root cause identified (multi-page selection without context)
**Priority:** 🔴 HIGH
