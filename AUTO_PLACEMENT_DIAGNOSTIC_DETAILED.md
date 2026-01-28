# Auto-Placement Diagnostic Report: Multi-Page Tag Problem

**Date:** 2026-01-28
**Issue:** Auto-placement selecting wrong pages for device tags
**Severity:** HIGH

## Executive Summary

The auto-placement accuracy test revealed a critical issue: **device tags appear on multiple pages** throughout the PDF, and the algorithm is selecting the **wrong page** as the "best" match.

### Key Findings

1. **Tag Frequency:** Common tags like `-K1` appear on **67 different pages**
2. **Wrong Page Selection:** The "best" position is often on a different page than expected
3. **Root Cause:** The confidence-based selection doesn't account for page context
4. **Impact:** Visual overlays appear on wrong pages, confusing users

## Detailed Analysis

### Example: Tag `-K1`

When searching for `-K1` on page 9, the algorithm found it on **67 pages**:

```
Page  8: (215.3, 603.0) - SELECTED AS BEST (wrong!)
Page  9: (266.3, 433.0) - Expected location
Page  9: (487.4, 597.0) - Additional location
Page  9: (552.2, 597.0) - Additional location
... 63 more pages ...
```

The algorithm selected **page 8** as the best match instead of any of the matches on page 9.

### Test Results by Page

#### Page 9 (Principle of safety circuit)
- **-K1:** Found on 67 pages, selected page 8 (WRONG)
- **-K2:** Found on 14 pages, selected page 9 (CORRECT)
- **-K3:** Found on 6 pages, selected page 9 (CORRECT)
- **-U1:** Found on 5 pages, selected page 9 (CORRECT)

#### Page 10 (Block diagram)
- **-K1:** Found on 67 pages, selected page 8 (WRONG)
- **-K2:** Found on 14 pages, selected page 9 (WRONG)
- **-A1:** (test needed)
- **-M1:** (test needed)

Similar issues affect pages 15, 16, 19, 20, and 22.

## Root Cause

The `ComponentPositionFinder` class has a flaw in its multi-page handling:

```python
# From component_position_finder.py line 386
# Always store the best position as the primary
best = max(deduped, key=lambda p: p.confidence)
result.positions[tag] = best
```

### The Problem

1. **No Page Context:** The algorithm doesn't know which page the user is viewing
2. **Confidence Alone:** It selects the "best" position based on confidence score alone
3. **First Match Wins:** When multiple pages have confidence=1.0, the first one wins
4. **Page 8 Bias:** Since page 8 is scanned first, it's often selected as "best"

### Why This Happens

In DRAWER PDFs:
- **Cross-references:** Device tags appear multiple times for wiring references
- **Contact listings:** Relay contacts (e.g., `-K1.1`, `-K1.2`) are listed in tables
- **Block diagrams:** Components are shown in overview diagrams
- **Schematic pages:** Detailed circuit diagrams show the actual components

Example: `-K1` (main contactor relay) appears:
- Page 8: In the safety circuit principle diagram
- Page 9: In the block diagram
- Page 10: In connection tables
- Pages 14-22: In detailed schematics and terminal lists

All of these are "correct" locations, but only ONE is the right location for a given user context.

## Impact Assessment

### Severity: HIGH

**User Experience:**
- Visual overlays appear on wrong pages
- Component clicking doesn't work as expected
- Confusing when tracing circuits

**Functional Impact:**
- 4 out of 7 pages tested show wrong page selection
- Common components (-K1, -K2, -A1, -U1, -M1) are most affected
- Users lose trust in the auto-placement feature

**Workaround:**
- Users must manually adjust component positions
- Defeats the purpose of "auto" placement

## Proposed Solutions

### Solution 1: Page-Specific Search (Recommended)

Modify the API to require the target page number:

```python
def find_positions_on_page(
    self,
    device_tags: List[str],
    page_num: int  # Required: which page to search
) -> Dict[str, ComponentPosition]:
    """Find positions for tags on a SPECIFIC page only.

    Returns only matches found on the specified page.
    """
    # Search only the specified page
    # Return only positions on that page
```

**Pros:**
- Simple and deterministic
- User knows what page they're viewing
- No ambiguity

**Cons:**
- API change required
- Callers must know the page number

### Solution 2: Spatial Clustering

Use position clustering to identify the "main" location:

```python
def select_best_position_by_clustering(positions: List[ComponentPosition]):
    """Select position from largest spatial cluster."""
    # Group positions by proximity
    # Select from the cluster with most instances
    # This finds the "schematic region" vs "table/reference regions"
```

**Pros:**
- No API change
- Works automatically

**Cons:**
- Complex algorithm
- May still select wrong page
- Assumes "main" location has more instances

### Solution 3: Page Classification Priority

Prefer certain page types over others:

```python
PAGE_PRIORITY = {
    'Schematic diagram': 10,
    'Block diagram': 8,
    'Power feed AC': 10,
    'Contactor control': 10,
    'Cable diagram': 2,      # Lower priority
    'Device tag': 1,         # Lowest priority (just lists)
}
```

**Pros:**
- Uses existing page classification
- Intelligent heuristic

**Cons:**
- May still select wrong page within same type
- Requires maintaining priority rules

### Solution 4: Hybrid Approach (Best)

Combine multiple strategies:

1. **User-specified page preferred:** If caller specifies page, strongly prefer it
2. **Page type priority:** Weight positions by page type
3. **Spatial clustering:** Within a page, select main schematic region
4. **Confidence score:** Use as tie-breaker

```python
def find_positions(
    self,
    device_tags: List[str],
    preferred_page: Optional[int] = None,  # NEW: page user is viewing
    page_type_weights: Optional[Dict[str, float]] = None
) -> PositionFinderResult:
    """Find positions with intelligent multi-page handling."""
    # 1. Collect all positions
    # 2. Apply page type weights
    # 3. Boost positions on preferred_page
    # 4. Use spatial clustering within pages
    # 5. Select best using weighted score
```

**Pros:**
- Handles all use cases
- Falls back gracefully
- User can provide hints

**Cons:**
- More complex implementation
- More parameters to tune

## Recommended Action Plan

### Phase 1: Quick Fix (1-2 hours)
Implement **Solution 1** (page-specific search):
- Add `preferred_page` parameter to `find_positions()`
- When specified, strongly weight positions on that page (10x confidence boost)
- Update GUI to pass current page number

### Phase 2: Improved Heuristics (4-6 hours)
Implement **Solution 4** (hybrid approach):
- Add page type priority weights
- Implement spatial clustering within pages
- Test on all problematic pages

### Phase 3: Testing (2-3 hours)
- Update test suite to validate page selection
- Add test cases for multi-page components
- Verify with real user workflows

### Phase 4: Documentation (1 hour)
- Update API docs
- Add examples showing page parameter usage
- Document expected behavior for multi-page tags

**Total estimated effort:** 8-12 hours

## Test Case for Fix Validation

```python
def test_page_specific_selection():
    """Verify that preferred_page parameter works correctly."""
    finder = ComponentPositionFinder("DRAWER.pdf")

    # -K1 appears on 67 pages, but we want it from page 9
    result = finder.find_positions(["-K1"], preferred_page=8)  # 0-indexed

    assert result.positions["-K1"].page == 8, \
        "Should select position from preferred page"

    # Without preferred_page, it might select page 8 (wrong)
    result_no_pref = finder.find_positions(["-K1"])
    # This currently fails!
```

## Metrics for Success

After implementing the fix:

1. **Page Accuracy:** 95%+ of tags found on correct page when preferred_page specified
2. **User Satisfaction:** Visual overlays appear on correct pages
3. **Multi-page Support:** Tags appearing on multiple pages handled gracefully
4. **API Usability:** Clear documentation on how to use preferred_page parameter

## Appendix: Full Multi-Page Data

### Tag Frequency Analysis

| Tag | Pages Found | Most Common Page | Expected Page |
|-----|-------------|------------------|---------------|
| -K1 | 67 | Page 8 | Page 9 |
| -K2 | 14 | Page 9 | Page 9 |
| -K3 | 6 | Page 9 | Page 9 |
| -U1 | 5 | Page 9 | Page 9 |
| -A1 | (test needed) | | Page 10 |
| -M1 | (test needed) | | Page 10 |

### Cross-Reference Pattern

Many "false" matches are actually cross-references in connection tables:
- Format: `-K1` in a cell showing "connects to -K1"
- These are valid text matches but not the component location
- Should be de-prioritized or filtered

### Spatial Distribution

Common tags appear in distinct regions:
- **Title blocks:** Component lists (bottom of page)
- **Connection tables:** Terminal references (pages 28-40)
- **Block diagrams:** Overview layouts (pages 9-10)
- **Schematic diagrams:** Actual circuits (pages 14-22)

The "best" location depends on user intent!

## Conclusion

The auto-placement algorithm has a **critical flaw in multi-page tag handling**. While it successfully finds tags (100% tag accuracy), it often selects the **wrong page** as the "best" match. This explains the user-reported issues on pages 9, 10, 15, 16, 19, 20, and 22.

The recommended fix is a **hybrid approach** with a `preferred_page` parameter, allowing the GUI to specify which page the user is viewing. This provides deterministic behavior while maintaining backward compatibility.

**Estimated fix time:** 8-12 hours
**Priority:** HIGH (affects primary use case)
**Complexity:** MEDIUM (requires API change + algorithm improvement)
