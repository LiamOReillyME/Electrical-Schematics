# Auto-Placement Improvement - Immediate Action Plan

**Date**: 2026-01-28
**Target**: 40% → 80% accuracy
**Timeline**: 4-5 days (parallel execution)

---

## Critical Path: Day-by-Day

### Day 1: Ground Truth Creation (QA Agent)

**Task**: Create validated dataset of component positions

**Steps**:
1. Open DRAWER.pdf in PDF viewer with coordinate display
2. Navigate to schematic pages (pages 5-20)
3. For each component, record:
   - Device tag (e.g., "-K1", "+DG-M1")
   - Page number
   - X, Y coordinates (center of text)
4. Target: 50+ components
5. Save as `ground_truth.json`

**Output**:
```json
{
  "metadata": {
    "pdf_file": "DRAWER.pdf",
    "created_date": "2026-01-28",
    "verified_by": "QA Engineer"
  },
  "components": [
    {"tag": "-A1", "page": 5, "x": 208.0, "y": 634.8},
    {"tag": "-K1", "page": 5, "x": 910.1, "y": 436.7}
  ]
}
```

---

### Day 2: Tag Counting + Quick Wins

#### Backend Agent 1: Count Ground Truth Tags (2 hours)
```python
# count_ground_truth.py
import json

with open("ground_truth.json") as f:
    gt = json.load(f)

tags = [c["tag"] for c in gt["components"]]
print(f"Total components: {len(tags)}")
print(f"Unique tags: {len(set(tags))}")

# By type
by_prefix = {}
for tag in tags:
    prefix = tag[0:3]  # e.g., "-K", "+DG", "-A"
    by_prefix[prefix] = by_prefix.get(prefix, 0) + 1

print("\nDistribution by type:")
for prefix, count in sorted(by_prefix.items()):
    print(f"  {prefix}: {count}")
```

#### Backend Agent 2: Iterations 1-3 (12 hours)

**Iteration 1**: Fix pattern regex
```python
# In component_position_finder.py line 222
DEVICE_TAG_PATTERN = re.compile(
    r'^[+-][A-Z0-9]+(?:[-_.][A-Z0-9]+)*(?:[:.\/][A-Z0-9]+)?$',
    re.IGNORECASE
)
```

**Iteration 2**: Add fuzzy matching
```python
def _match_text_to_tag(self, text, tag_set, tag_variants):
    # ... existing code ...

    # Add fuzzy fallback
    from difflib import get_close_matches
    close = get_close_matches(text, tag_set, n=1, cutoff=0.85)
    if close:
        return close[0]

    return None
```

**Iteration 3**: Improve tag variants
```python
def _build_tag_variants(self, device_tags):
    variants = {}
    for tag in device_tags:
        # Original
        variants[tag] = tag

        # Without prefix: "+DG-M1" → "DG-M1"
        stripped = tag.lstrip("+-")
        variants[stripped] = tag

        # Without suffix: "-A1-X5:3" → "-A1"
        base = re.sub(r'[:/.]\S+$', '', tag)
        variants[base] = tag

        # Last part: "+DG-M1" → "M1"
        parts = base.split("-")
        if len(parts) > 1:
            variants[parts[-1]] = tag

        # Alternative separators
        for sep in ['_', '.']:
            alt = tag.replace('-', sep)
            variants[alt] = tag

    return variants
```

**Validation after each iteration**:
```bash
python validate_auto_placement.py
# Reports accuracy, precision, recall
```

---

### Day 3: Multi-Method Extraction

#### Backend Agent 2: Iterations 4-6 (18 hours)

**Iteration 4**: Add block-based extraction
```python
def _extract_from_blocks(self, page, tag_set, tag_variants):
    """Alternative extraction using block-level text."""
    text_blocks = page.get_text("blocks")

    positions = {}
    for block in text_blocks:
        if len(block) < 5:
            continue

        x0, y0, x1, y1, text, block_no, block_type = block

        # Search for tags in block text
        for tag in tag_set:
            if tag in text:
                position = ComponentPosition(
                    device_tag=tag,
                    x=(x0 + x1) / 2,
                    y=(y0 + y1) / 2,
                    width=x1 - x0,
                    height=y1 - y0,
                    page=page.number,
                    confidence=0.8,
                    match_type="block"
                )

                if tag not in positions:
                    positions[tag] = []
                positions[tag].append(position)

    return positions
```

**Iteration 5**: Implement voting logic
```python
def _merge_extraction_results(self, span_results, block_results):
    """Merge results from multiple extraction methods."""
    merged = {}

    for tag in all_tags:
        span_match = span_results.get(tag)
        block_match = block_results.get(tag)

        if span_match and block_match:
            # Both methods agree - high confidence
            if self._positions_close(span_match, block_match):
                span_match.confidence = 0.95
                merged[tag] = span_match
            else:
                # Disagreement - keep both as ambiguous
                merged[tag] = [span_match, block_match]
        elif span_match:
            # Only span found - medium confidence
            merged[tag] = span_match
        elif block_match:
            # Only block found - medium confidence
            merged[tag] = block_match

    return merged
```

**Iteration 6**: Integrate multi-method extraction
```python
def _extract_positions_from_page(self, page_num, tag_set, tag_variants):
    """Extract using multiple methods and vote."""
    page = self.doc[page_num]

    # Method 1: Span-based (current approach)
    span_positions = self._extract_from_spans(page, tag_set, tag_variants)

    # Method 2: Block-based (new approach)
    block_positions = self._extract_from_blocks(page, tag_set, tag_variants)

    # Merge with voting
    return self._merge_extraction_results(span_positions, block_positions)
```

---

### Day 4-5: Validation & Optimization

#### Backend Agent 2: Iterations 7-15 (48 hours)

**Iterations 7-9**: Edge case handling
- Handle rotated pages
- Handle multi-line tags
- Handle tags with special characters

**Iterations 10-12**: Performance optimization
- Add caching
- Profile hot paths
- Optimize deduplication

**Iterations 13-15**: Final tuning
- Adjust confidence thresholds
- Fine-tune tolerance values
- Comprehensive testing

#### QA Agent: Continuous Validation

After each iteration:
```bash
cd /home/liam-oreilly/claude.projects/electricalSchematics
python validate_auto_placement.py

# Output:
# Iteration: 7
# Position Accuracy: 76% (38/50)
# Precision: 90%
# Recall: 76%
# F1 Score: 0.82
#
# Failures:
#   Not Found: 12 components
#   Wrong Position: 0 components
```

---

## Quick Reference: File Locations

```
/home/liam-oreilly/claude.projects/electricalSchematics/
├── electrical_schematics/pdf/
│   └── component_position_finder.py  ← MAIN FILE TO MODIFY
├── ground_truth.json                  ← QA CREATES THIS
├── validate_auto_placement.py         ← QA RUNS THIS
├── count_ground_truth.py              ← BACKEND 1 CREATES THIS
└── AUTO_PLACEMENT_ARCHITECTURE.md     ← FULL DESIGN DOC
```

---

## Success Criteria

**After Day 5, we must have**:
- ✅ Position accuracy ≥ 80% (validated with ground_truth.json)
- ✅ Precision ≥ 85%
- ✅ Recall ≥ 75%
- ✅ All 176+ existing tests pass
- ✅ Performance impact < 5% (< 1 second slower)

---

## Communication Protocol

**Daily Updates** (async in Slack/chat):
```
QA Agent (Day 1):
  "Ground truth complete. 52 components verified in DRAWER.pdf.
   File: ground_truth.json
   Distribution: 8 -A, 12 -K, 5 +DG, etc."

Backend Agent 1 (Day 2):
  "Tag count complete. 52 total, 48 unique.
   File: ground_truth_stats.md"

Backend Agent 2 (Day 2 PM):
  "Iteration 3 complete. Accuracy: 68% → 72%.
   Changes: Improved tag variants.
   Next: Add block-based extraction."

QA Agent (Day 2 PM):
  "Validated iteration 3. Accuracy confirmed 72%.
   Failures: 15 not found (pattern mismatch).
   Recommendation: Fix regex first."
```

---

## Rollback Plan

**If accuracy < 80% after iteration 10**:
1. Stop iterating
2. Analyze failure patterns
3. Escalate to architect
4. Pivot strategy if needed

**If tests start failing**:
1. Revert last change
2. Fix tests first
3. Resume iterations

**If performance degrades > 10%**:
1. Profile to find bottleneck
2. Add caching/optimization
3. May need to reduce extraction methods

---

## Tools & Commands

**Validate accuracy**:
```bash
python validate_auto_placement.py
```

**Run tests**:
```bash
pytest tests/test_component_position_finder.py -v
```

**Profile performance**:
```bash
python -m cProfile -o profile.stats validate_auto_placement.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

**View ground truth**:
```bash
cat ground_truth.json | jq '.components[] | select(.page == 5)'
```

---

## Risk Mitigation

**Risk**: QA takes longer than 1 day for ground truth
**Mitigation**: Backend agents can start with subset (first 20 components)

**Risk**: Accuracy stuck at 70-75%
**Mitigation**: Switch to multi-method extraction earlier (iteration 4 instead of 7)

**Risk**: Backend agents block each other
**Mitigation**: Work on separate branches, merge frequently

---

## Next Steps After 80% Accuracy

Once we hit 80%:
1. Merge to main branch
2. Deploy to production
3. Monitor user feedback
4. Plan next sprint (90% target)

---

**READY TO START**: QA Agent begins ground truth creation immediately!
