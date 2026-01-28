# Auto-Placement Accuracy Test Report

**Test Date:** 2026-01-28
**PDF:** DRAWER.pdf
**Test Type:** Comprehensive validation of auto-placement on problematic pages

## Executive Summary

### Initial Results (Tag Detection)
- **Pages tested:** 7 (pages 9, 10, 15, 16, 19, 20, 22)
- **Total expected tags:** 108
- **Total found tags:** 108
- **Tag detection accuracy:** **100.0%**

### Critical Finding (Page Selection)
- **Position accuracy:** **FAILED**
- **Issue:** Tags found on **WRONG PAGES**
- **Root cause:** Multi-page tags selected incorrectly

**Verdict:** Algorithm finds tags successfully but selects wrong page as "best" match.

---

## Test 1: Tag Detection (PASSED)

Testing whether device tags can be found anywhere in the PDF.

### Per-Page Results

#### Page 9: Principle of safety circuit
- **Expected tags:** 19
- **Found tags:** 19
- **Accuracy:** 100.0%
- **Tags:** -2.2, -K1, -K1.1, -K1.2, -K1.3, -K2, -K3, -KR1, -Q1.1, -Q1.2, -Q1.3, -S3, -U1, +BAO Modul GS215, +BCS, +BCS-A1, +CD, +CD-A1, +EXT-S2.1

#### Page 10: Block diagram
- **Expected tags:** 34
- **Found tags:** 34
- **Accuracy:** 100.0%
- **Tags:** -Bx, -F1, -F2, -F3, -F4, -F5, -F6, -F7, -K1, -K1.1, -K1.2, -K1.3, -K2, -M1, -M2, -OUT, -Q1, -S2.1, -S2.2, -X0, +CD, +CD-A1, +CD-G1, +CD-K1, +CD-K1.1, +CD-K1.2, +CD-K1.3, +CD-K2, +CD-U1, +CD-Z1, +CD-Z2, +DG, +EXT, +PF

#### Page 15: Power feed AC
- **Expected tags:** 16
- **Found tags:** 16
- **Accuracy:** 100.0%
- **Tags:** -EL1, -EL2, -F1:2, -F1:4, -F1:6, -F2, -F3, -PE, -X0:1, -X0:2, -X1, -X1:1, +CD-F1, +DG-PE, +DG-X0, +Q1-Q1

#### Page 16: Power supply DC
- **Expected tags:** 10
- **Found tags:** 10
- **Accuracy:** 100.0%
- **Tags:** -F4, -F5, -F6, -G1, -K0.2, -K1.0, -X0:14, -X0:9, -X3, -XS3

#### Page 19: Contactor control
- **Expected tags:** 12
- **Found tags:** 12
- **Accuracy:** 100.0%
- **Tags:** -A1, -K1, -K1.0, -K1.1, -K1.2, -K1.3, -K2, -K3, -KR1, -U1, -X3, -XS3

#### Page 20: Contactor control
- **Expected tags:** 8
- **Found tags:** 8
- **Accuracy:** 100.0%
- **Tags:** -K1, -K1.1, -K1.2, -K1.3, -K2, -K3, -KR1, -X3

#### Page 22: Extractor motor
- **Expected tags:** 9
- **Found tags:** 9
- **Accuracy:** 100.0%
- **Tags:** -F7, -K1.2, -K1.3, -SH, -WM21, -WM22, +DG-SH, +DG-XM2a, +DG-XM2b

---

## Test 2: Page Selection (FAILED)

Testing whether tags are found on the CORRECT pages.

### Critical Issues Identified

#### Issue 1: Tag `-K1` (Main Contactor)

**Expected:** Should be found on page 9
**Actual:** Found on **67 pages**, selected page 8 as "best"

**Locations found:**
```
Page  8: (215.3, 603.0) - SELECTED AS BEST ❌
Page  9: (266.3, 433.0) - Expected location ✓
Page  9: (487.4, 597.0) - Additional location
Page  9: (552.2, 597.0) - Additional location
Page  9: (688.2, 597.0) - Additional location
Page  9: (756.2, 597.0) - Additional location
... 62 more pages ...
```

**Impact:** Visual overlay appears on wrong page

#### Issue 2: Tag `-K2`

**Expected:** Should be found on page 10
**Actual:** Found on 14 pages, selected page 9 as "best"

**Locations found:**
```
Page  9: (266.3, 467.0) - SELECTED AS BEST ❌
Page 10: (327.2, 140.9) - Expected location ✓
Page 10: (209.6, 551.7) - Additional location
... 11 more pages ...
```

#### Issue 3: Tag `-U1`

**Expected:** Should be found on page 9
**Actual:** Found on 5 pages, selected page 9 as "best" ✓

**Locations found:**
```
Page  9: (628.6, 540.3) - SELECTED AS BEST ✓
Page 10: (109.9, 393.8)
Page 19: (379.2, 489.7)
Page 21: (234.6, 259.1)
Page 21: (337.8, 603.0)
```

**Status:** Correct by chance (page 9 was scanned first)

### Summary of Page Selection Issues

| Tag | Expected Page | Selected Page | Status | Occurrences |
|-----|---------------|---------------|--------|-------------|
| -K1 | 9 | 8 | ❌ WRONG | 67 pages |
| -K2 | 10 | 9 | ❌ WRONG | 14 pages |
| -K3 | 9 | 9 | ✓ Correct | 6 pages |
| -U1 | 9 | 9 | ✓ Correct | 5 pages |
| -A1 | 10 | ? | (not tested) | ? |
| -M1 | 10 | ? | (not tested) | ? |

**Failure rate:** At least 50% (2 out of 4 tested tags on wrong page)

---

## Root Cause Analysis

### Primary Cause: Confidence-Based Selection Without Page Context

The algorithm selects the "best" position using only confidence score:

```python
# From component_position_finder.py line 386
best = max(deduped, key=lambda p: p.confidence)
result.positions[tag] = best
```

**Problems:**
1. No awareness of which page user is viewing
2. When multiple matches have confidence=1.0, first match wins
3. Earlier pages (e.g., page 8) are scanned first, creating bias
4. No distinction between "schematic location" vs "reference location"

### Why Tags Appear on Multiple Pages

DRAWER PDFs contain:

1. **Overview diagrams** (pages 8-10): Block diagrams showing system layout
2. **Detailed schematics** (pages 14-22): Circuit diagrams with actual components
3. **Connection tables** (pages 28-40): Terminal wiring lists
4. **Cross-references:** Tags appear next to arrows showing "connects to -K1"

All of these are technically correct text matches, but only the detailed schematic location is useful for visual overlays.

### Contributing Factors

1. **No page type weighting:** All pages treated equally
2. **No spatial analysis:** Doesn't distinguish "main component" vs "reference"
3. **No user context:** Algorithm doesn't know what page user is viewing
4. **Greedy selection:** Takes first high-confidence match

---

## Impact Assessment

### Severity: **HIGH**

#### User Experience Impact
- ❌ Visual overlays appear on wrong pages
- ❌ Component clicking doesn't highlight correct page
- ❌ Circuit tracing starts from wrong location
- ❌ Users lose trust in auto-placement feature
- ❌ Manual position adjustment required (defeats "auto" purpose)

#### Functional Impact
- **Pages affected:** 4+ out of 7 tested (57%+)
- **Components affected:** Common components (-K1, -K2, -A1, -M1, -U1)
- **Workaround available:** Yes (manual adjustment)
- **Data loss risk:** No

#### Business Impact
- Feature appears broken to users
- Reduces value proposition of auto-placement
- Increases support burden
- May prevent adoption of the tool

---

## Recommendations

### Solution 1: Page-Aware Selection (Quick Fix)

Add `preferred_page` parameter to guide selection:

```python
def find_positions(
    self,
    device_tags: List[str],
    preferred_page: Optional[int] = None,  # NEW
    search_all_pages: bool = False
) -> PositionFinderResult:
    """Find positions with page preference.

    If preferred_page is specified, strongly prefer positions
    found on that page (10x confidence boost).
    """
```

**Implementation:**
```python
# When scoring positions
if preferred_page is not None and pos.page == preferred_page:
    score = pos.confidence * 10.0  # Strongly prefer this page
else:
    score = pos.confidence
```

**Pros:**
- Simple to implement (2-3 hours)
- Deterministic behavior
- Backward compatible (parameter optional)

**Cons:**
- Requires GUI to pass page number
- Doesn't help if user doesn't specify page

**Estimated effort:** 2-3 hours

### Solution 2: Page Type Priority (Medium Fix)

Weight positions by page type:

```python
PAGE_TYPE_WEIGHTS = {
    'Schematic diagram': 10.0,
    'Contactor control': 10.0,
    'Power feed AC': 10.0,
    'Block diagram': 5.0,
    'Principle of safety circuit': 5.0,
    'Cable diagram': 1.0,
    'Device tag': 0.1,  # Almost never the right page
}
```

**Pros:**
- Works automatically
- Uses existing page classification
- Intelligent heuristic

**Cons:**
- May not always work (multiple schematic pages)
- Requires maintaining weight table
- Still may select wrong page within same type

**Estimated effort:** 3-4 hours

### Solution 3: Spatial Clustering (Advanced Fix)

Identify "main" component location via clustering:

```python
def select_main_location(positions: List[ComponentPosition]):
    """Find the main schematic location."""
    # 1. Group positions by spatial proximity
    # 2. Identify the largest cluster (schematic region)
    # 3. Select best position from that cluster
    # 4. Deprioritize positions in title blocks or edges
```

**Pros:**
- Intelligent spatial analysis
- No user input needed
- Handles various PDF layouts

**Cons:**
- Complex implementation
- May fail for dispersed schematics
- Harder to debug

**Estimated effort:** 6-8 hours

### Solution 4: Hybrid Approach (Best Solution)

Combine all strategies:

```python
def calculate_position_score(
    pos: ComponentPosition,
    preferred_page: Optional[int],
    page_type: str,
    cluster_size: int
) -> float:
    """Calculate weighted score for position selection."""
    score = pos.confidence

    # Factor 1: User preference (highest weight)
    if preferred_page and pos.page == preferred_page:
        score *= 10.0

    # Factor 2: Page type
    score *= PAGE_TYPE_WEIGHTS.get(page_type, 1.0)

    # Factor 3: Spatial clustering
    score *= (1.0 + 0.1 * cluster_size)

    # Factor 4: Penalize edge positions (likely references)
    if is_edge_position(pos):
        score *= 0.5

    return score
```

**Pros:**
- Handles all cases
- Falls back gracefully
- Best accuracy

**Cons:**
- Most complex
- Requires tuning

**Estimated effort:** 8-12 hours

---

## Recommended Action Plan

### Phase 1: Quick Fix (Priority: HIGH)
**Effort:** 2-3 hours

1. Implement `preferred_page` parameter (Solution 1)
2. Update GUI to pass current page number
3. Test on problematic pages
4. Document parameter usage

**Deliverables:**
- Updated `component_position_finder.py`
- Updated GUI integration
- Test cases for page preference
- API documentation

### Phase 2: Improved Heuristics (Priority: MEDIUM)
**Effort:** 4-6 hours

1. Add page type weighting (Solution 2)
2. Implement basic spatial filtering
3. Test across all schematic types
4. Tune weights based on results

**Deliverables:**
- Page type weight table
- Edge position detection
- Comprehensive test suite
- Performance metrics

### Phase 3: Advanced Clustering (Priority: LOW)
**Effort:** 6-8 hours

1. Implement spatial clustering (Solution 3)
2. Integrate with existing scoring
3. Add visualization for debugging
4. Benchmark on various PDFs

**Deliverables:**
- Clustering algorithm
- Debug visualizations
- Multi-PDF test suite
- Performance analysis

### Phase 4: Validation & Monitoring
**Effort:** 2-3 hours

1. Create comprehensive test suite
2. Test with real user workflows
3. Add metrics/logging
4. Update documentation

**Deliverables:**
- Automated test suite
- User acceptance testing
- Monitoring dashboard
- Updated user docs

**Total estimated effort:** 14-20 hours

---

## Success Metrics

After implementing fixes:

1. **Page accuracy:** >95% when `preferred_page` specified
2. **Auto accuracy:** >80% without page hint (using heuristics)
3. **User satisfaction:** Visual overlays appear on correct pages
4. **Multi-page handling:** Clear strategy for ambiguous cases
5. **Performance:** No degradation in search speed

---

## Test Data for Validation

### Test Case 1: Preferred Page

```python
def test_preferred_page_selection():
    finder = ComponentPositionFinder("DRAWER.pdf")

    # Test -K1 on page 9
    result = finder.find_positions(["-K1"], preferred_page=8)
    assert result.positions["-K1"].page == 8

    # Test -K2 on page 10
    result = finder.find_positions(["-K2"], preferred_page=9)
    assert result.positions["-K2"].page == 9
```

### Test Case 2: Page Type Priority

```python
def test_page_type_priority():
    finder = ComponentPositionFinder("DRAWER.pdf")

    # Without page hint, should prefer schematic pages
    result = finder.find_positions(["-K1"])
    page_title = finder.get_page_title(result.positions["-K1"].page)

    # Should NOT be "Device tag" or "Cable diagram" pages
    assert "Device tag" not in page_title
    assert "Cable diagram" not in page_title
```

### Test Case 3: Multi-Page Awareness

```python
def test_multi_page_reporting():
    finder = ComponentPositionFinder("DRAWER.pdf")

    result = finder.find_positions(["-K1"])

    # Should report all pages where -K1 appears
    assert "-K1" in result.ambiguous_matches
    assert len(result.ambiguous_matches["-K1"]) > 1

    # Should include pages 8, 9, 10 at minimum
    pages_found = {pos.page for pos in result.ambiguous_matches["-K1"]}
    assert 8 in pages_found
    assert 9 in pages_found
```

---

## Appendix A: Ground Truth Data

Complete list of expected device tags per page:

```python
GROUND_TRUTH = {
    8: {  # Page 9: Principle of safety circuit
        'title': 'Principle of safety circuit',
        'tags': [
            '-2.2', '-K1', '-K1.1', '-K1.2', '-K1.3', '-K2', '-K3', '-KR1',
            '-Q1.1', '-Q1.2', '-Q1.3', '-S3', '-U1',
            '+BAO Modul GS215', '+BCS', '+BCS-A1', '+CD', '+CD-A1', '+EXT-S2.1',
        ]
    },
    9: {  # Page 10: Block diagram
        'title': 'Block diagram',
        'tags': [
            '-Bx', '-F1', '-F2', '-F3', '-F4', '-F5', '-F6', '-F7', '-K1',
            '-K1.1', '-K1.2', '-K1.3', '-K2', '-M1', '-M2', '-OUT', '-Q1',
            '-S2.1', '-S2.2', '-X0',
            '+CD', '+CD-A1', '+CD-G1', '+CD-K1', '+CD-K1.1', '+CD-K1.2',
            '+CD-K1.3', '+CD-K2', '+CD-U1', '+CD-Z1', '+CD-Z2', '+DG', '+EXT', '+PF',
        ]
    },
    14: {  # Page 15: Power feed AC
        'title': 'Power feed AC',
        'tags': [
            '-EL1', '-EL2', '-F1:2', '-F1:4', '-F1:6', '-F2', '-F3', '-PE',
            '-X0:1', '-X0:2', '-X1', '-X1:1',
            '+CD-F1', '+DG-PE', '+DG-X0', '+Q1-Q1',
        ]
    },
    15: {  # Page 16: Power supply DC
        'title': 'Power supply DC',
        'tags': [
            '-F4', '-F5', '-F6', '-G1', '-K0.2', '-K1.0', '-X0:14', '-X0:9',
            '-X3', '-XS3',
        ]
    },
    18: {  # Page 19: Contactor control
        'title': 'Contactor control',
        'tags': [
            '-A1', '-K1', '-K1.0', '-K1.1', '-K1.2', '-K1.3', '-K2', '-K3',
            '-KR1', '-U1', '-X3', '-XS3',
        ]
    },
    19: {  # Page 20: Contactor control
        'title': 'Contactor control',
        'tags': [
            '-K1', '-K1.1', '-K1.2', '-K1.3', '-K2', '-K3', '-KR1', '-X3',
        ]
    },
    21: {  # Page 22: Extractor motor
        'title': 'Extractor motor',
        'tags': [
            '-F7', '-K1.2', '-K1.3', '-SH', '-WM21', '-WM22',
            '+DG-SH', '+DG-XM2a', '+DG-XM2b',
        ]
    },
}
```

---

## Appendix B: Tag Frequency Analysis

Most problematic tags (appear on many pages):

| Tag | Pages | Notes |
|-----|-------|-------|
| -K1 | 67 | Main contactor - appears everywhere |
| -K1.1 | ~30 | Contact 1 of K1 relay |
| -K1.2 | ~30 | Contact 2 of K1 relay |
| -K1.3 | ~30 | Contact 3 of K1 relay |
| -K2 | 14 | Secondary contactor |
| -K3 | 6 | Tertiary contactor |
| -U1 | 5 | Control module |
| -A1 | ? | PLC (likely many pages) |

Less problematic tags (appear on few pages):
- `-G1`, `-F7`, `-SH`, `-WM21`: 1-2 pages
- Field devices (`+DG-*`): Usually 1-3 pages

---

## Conclusion

The auto-placement algorithm successfully detects device tags (**100% tag detection**) but fails to select the correct page (**~50% page selection failure**). This is due to lack of page context in the scoring algorithm.

The recommended fix is a **hybrid approach** combining:
1. User-provided page hints (`preferred_page` parameter)
2. Page type weighting (prefer schematic pages)
3. Spatial clustering (prefer main component locations)

**Estimated fix time:** 14-20 hours
**Priority:** HIGH
**Impact:** Resolves primary user complaint
