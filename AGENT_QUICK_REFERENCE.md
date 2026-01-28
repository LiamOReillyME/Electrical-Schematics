# Agent Quick Reference Card

**Mission**: Improve auto-placement accuracy from 40% to 80%+ in 4-5 days

---

## QA Agent: Ground Truth Creation

### Your Mission
Create validated dataset of component positions for scientific measurement.

### What You Do
1. Open `DRAWER.pdf` in PDF viewer with coordinates
2. Navigate to schematic pages (5-20)
3. Record 50+ component positions:
   - Tag (e.g., "-K1")
   - Page number
   - X, Y coordinates (center of text)
4. Save as `ground_truth.json`

### JSON Format
```json
{
  "metadata": {
    "pdf_file": "DRAWER.pdf",
    "created_date": "2026-01-28",
    "verified_by": "Your Name"
  },
  "components": [
    {"tag": "-A1", "page": 5, "x": 208.0, "y": 634.8, "tolerance": 50.0},
    {"tag": "-K1", "page": 5, "x": 910.1, "y": 436.7, "tolerance": 50.0}
  ]
}
```

### Time Estimate
8 hours (50 components × 10 min each)

### When Done
Notify Backend Agents: "Ground truth ready with N components"

### Ongoing Work
After each Backend iteration, run:
```bash
python validate_auto_placement.py --iteration N --report detailed
```

Report accuracy to Backend Agent 2.

---

## Backend Agent 1: Tag Counting

### Your Mission
Analyze ground truth dataset to understand scope and distribution.

### What You Do
1. Wait for `ground_truth.json` from QA
2. Create `count_ground_truth.py`:
```python
import json

with open("ground_truth.json") as f:
    gt = json.load(f)

tags = [c["tag"] for c in gt["components"]]
print(f"Total: {len(tags)}, Unique: {len(set(tags))}")

# Distribution by prefix
by_prefix = {}
for tag in tags:
    prefix = tag[0:3]
    by_prefix[prefix] = by_prefix.get(prefix, 0) + 1

for prefix, count in sorted(by_prefix.items()):
    print(f"{prefix}: {count}")
```

3. Create `ground_truth_stats.md` with findings
4. Identify any patterns or gaps

### Time Estimate
2-4 hours

### When Done
Notify Backend Agent 2: "Tag count complete. N total, M unique."

---

## Backend Agent 2: Iterative Improvements

### Your Mission
Improve `component_position_finder.py` through 15 iterations, validating each.

### What You Do

#### Iterations 1-3: Pattern Matching (Day 2)

**Iteration 1**: Fix regex pattern
```python
# File: electrical_schematics/pdf/component_position_finder.py
# Line: 222

# OLD:
DEVICE_TAG_PATTERN = re.compile(r'^[+-][A-Z0-9]+(?:-[A-Z0-9]+)?(?::\S+)?$')

# NEW:
DEVICE_TAG_PATTERN = re.compile(
    r'^[+-][A-Z0-9]+(?:[-_.][A-Z0-9]+)*(?:[:.\/][A-Z0-9]+)?$',
    re.IGNORECASE
)
```

**Iteration 2**: Add fuzzy matching
```python
# In _match_text_to_tag() method, add at end before return None:

from difflib import get_close_matches
close = get_close_matches(text, tag_set, n=1, cutoff=0.85)
if close:
    return close[0]
```

**Iteration 3**: Improve tag variants
```python
# In _build_tag_variants() method, add:

# Alternative separators
for sep in ['_', '.']:
    alt = tag.replace('-', sep)
    variants[alt] = tag

# Without suffix
base = re.sub(r'[:/.]\S+$', '', tag)
variants[base] = tag
variants[base.lstrip("+-")] = tag
```

#### Iterations 4-6: Multi-Method Extraction (Day 3)

**Iteration 4**: Add block-based extraction
```python
def _extract_from_blocks(self, page, tag_set, tag_variants):
    """Extract using block-level text."""
    text_blocks = page.get_text("blocks")
    positions = {}

    for block in text_blocks:
        if len(block) < 5:
            continue
        x0, y0, x1, y1, text, _, _ = block

        for tag in tag_set:
            if tag in text:
                pos = ComponentPosition(
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
                positions[tag].append(pos)

    return positions
```

**Iteration 5**: Implement voting
```python
def _merge_extraction_results(self, span_results, block_results):
    """Merge results with voting."""
    merged = {}

    all_tags = set(span_results.keys()) | set(block_results.keys())

    for tag in all_tags:
        span = span_results.get(tag)
        block = block_results.get(tag)

        if span and block:
            # Both methods agree
            if self._positions_close([span, block]):
                span.confidence = 0.95
                merged[tag] = span
            else:
                merged[tag] = [span, block]
        elif span:
            merged[tag] = span
        elif block:
            merged[tag] = block

    return merged
```

**Iteration 6**: Integrate multi-method
```python
def _extract_positions_from_page(self, page_num, tag_set, tag_variants):
    """Extract using multiple methods."""
    page = self.doc[page_num]

    # Two methods
    span_positions = self._extract_from_spans(page, tag_set, tag_variants)
    block_positions = self._extract_from_blocks(page, tag_set, tag_variants)

    # Merge with voting
    return self._merge_extraction_results(span_positions, block_positions)
```

#### Iterations 7-15: Optimization & Edge Cases (Day 4-5)

Focus on:
- Handle rotated pages
- Improve bbox calculation
- Add caching
- Fix edge cases from QA reports
- Performance tuning

### Validation After Each Iteration

```bash
python validate_auto_placement.py --iteration N --report detailed
```

Check output:
- Position Accuracy: X%
- Precision: Y%
- Recall: Z%

If accuracy < 75%: Analyze failures, adjust approach
If accuracy ≥ 80%: SUCCESS! Proceed to final testing

### Time Estimate
- 3-4 iterations per day
- 4-6 hours per iteration
- Total: 60-90 hours over 4-5 days

### Communication
After each iteration:
1. Commit changes
2. Run validation
3. Report: "Iteration N: Accuracy X%, Changes: [...]"
4. If accuracy plateaus, escalate to architect

---

## File Reference

### Main Code File
```
electrical_schematics/pdf/component_position_finder.py
```
Lines to modify:
- 222: DEVICE_TAG_PATTERN
- 453-484: _build_tag_variants()
- 572-612: _match_text_to_tag()
- Add new methods: _extract_from_blocks(), _merge_extraction_results()

### Test File
```
tests/test_component_position_finder.py
```
Run tests after each change:
```bash
pytest tests/test_component_position_finder.py -v
```

### Validation Files
```
ground_truth.json              ← QA creates
validate_auto_placement.py     ← Run after each iteration
ground_truth_stats.md          ← Backend Agent 1 creates
iteration_logs/                ← Backend Agent 2 documents changes
```

---

## Decision Tree

### Accuracy < 70%
→ Focus on pattern matching (Iterations 1-3)
→ Check QA report for NOT_FOUND patterns

### Accuracy 70-75%
→ Add multi-method extraction (Iterations 4-6)
→ Check for PDF structure issues

### Accuracy 75-80%
→ Fine-tune confidence thresholds
→ Fix edge cases from QA reports

### Accuracy ≥ 80%
→ SUCCESS! Final testing and merge

### Accuracy plateaus
→ Escalate to architect
→ May need different approach

---

## Communication Templates

### QA → Backend
```
✅ Ground truth complete
- File: ground_truth.json
- Components: 52 verified
- Pages: 5-20
- Distribution: 8 -A, 12 -K, 5 +DG, ...

Backend agents: Proceed with analysis and iterations.
```

### Backend 1 → Backend 2
```
✅ Tag count complete
- Total components: 52
- Unique tags: 48
- Most common: -K (12), +DG (10), -A (8)
- File: ground_truth_stats.md

Backend Agent 2: Ready for iterations.
```

### Backend 2 → QA (After Each Iteration)
```
🔄 Iteration N complete
- Changes: [brief description]
- Files modified: component_position_finder.py lines X-Y
- Tests: All passing (176+)
- Ready for validation

QA: Please run validate_auto_placement.py --iteration N
```

### QA → Backend 2 (Validation Result)
```
📊 Iteration N validation
- Accuracy: X% (target: 80%)
- Precision: Y%
- Recall: Z%
- Status: [✅ On track | ⚠️ Below target | ❌ Issues]

Common failures:
- [List top 3 failure patterns]

Recommendation: [Next steps]
```

---

## Troubleshooting

### "Ground truth file not found"
→ QA: Ensure `ground_truth.json` is in repo root
→ Backend: Check file path in validation script

### "All tests failing"
→ Revert last change
→ Run `pytest tests/ -v` to see details
→ Fix syntax/import errors

### "Accuracy went DOWN"
→ Check what changed in last iteration
→ Revert if needed
→ Try different approach

### "Performance too slow"
→ Add caching
→ Profile with `python -m cProfile`
→ Optimize hot paths

### "Stuck at X% accuracy"
→ Analyze QA validation report
→ Identify systematic failure patterns
→ Escalate to architect if blocked

---

## Success Checklist

After 15 iterations, verify:
- [ ] Position accuracy ≥ 80%
- [ ] Precision ≥ 85%
- [ ] Recall ≥ 75%
- [ ] All 176+ tests passing
- [ ] Performance < 5% slower
- [ ] Code reviewed by architect
- [ ] Documentation updated

If all checked: READY TO MERGE! 🎉

---

**Remember**: Validate after EVERY iteration. Don't wait until the end!

---

*Keep this reference handy during the 4-5 day sprint.*
