#!/usr/bin/env python3
"""
Auto-Placement Accuracy Test for Problematic Pages

Tests component position finding accuracy on pages reported by users
as having issues with auto-placement (pages 9, 10, 15, 16, 19, 20, 22).

This test:
1. Uses manually verified ground truth data (expected device tags per page)
2. Runs auto-placement algorithm on each problematic page
3. Compares found vs expected tags
4. Generates detailed diagnostic reports and visualizations
5. Identifies root causes for missed tags

Usage:
    python test_auto_placement_pages.py

    # Debug mode with visual output
    python test_auto_placement_pages.py --debug

    # Single page test
    python test_auto_placement_pages.py --page 9

    # Generate report only (no visual debug)
    python test_auto_placement_pages.py --report-only
"""

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

import fitz  # PyMuPDF

from electrical_schematics.pdf.component_position_finder import (
    ComponentPositionFinder,
    ComponentPosition,
)


@dataclass
class PageTestResult:
    """Result from testing a single page."""
    page_num: int
    page_title: str
    expected_tags: List[str]
    found_tags: List[str]
    missed_tags: List[str]
    unexpected_tags: List[str]
    accuracy: float
    total_expected: int
    total_found: int

    def to_dict(self):
        return asdict(self)


@dataclass
class TestSummary:
    """Overall test summary across all pages."""
    test_date: str
    pages_tested: int
    total_expected: int
    total_found: int
    total_missed: int
    overall_accuracy: float
    page_results: List[PageTestResult]

    def to_dict(self):
        return {
            'test_date': self.test_date,
            'pages_tested': self.pages_tested,
            'total_expected': self.total_expected,
            'total_found': self.total_found,
            'total_missed': self.total_missed,
            'overall_accuracy': self.overall_accuracy,
            'page_results': [r.to_dict() for r in self.page_results]
        }


# GROUND TRUTH DATA
# Manually verified device tags per problematic page
# These were extracted by visually inspecting DRAWER.pdf in a PDF viewer
# IMPORTANT: Cross-reference tags in blue (format: K2:61/19.9) are EXCLUDED
# as they are navigation references, not actual component locations.

GROUND_TRUTH = {
    8: {
        'title': 'Principle of safety circuit',
        'tags': [
            '-2.2', '-K1', '-K1.1', '-K1.2', '-K1.3', '-K2', '-K3', '-KR1',
            '-Q1.1', '-Q1.2', '-Q1.3', '-S3', '-U1',
            '+BAO Modul GS215', '+BCS', '+BCS-A1', '+CD', '+CD-A1', '+EXT-S2.1',
        ]
    },
    9: {
        'title': 'Block diagram',
        'tags': [
            '-Bx', '-F1', '-F2', '-F3', '-F4', '-F5', '-F6', '-F7', '-K1',
            '-K1.1', '-K1.2', '-K1.3', '-K2', '-M1', '-M2', '-OUT', '-Q1',
            '-S2.1', '-S2.2', '-X0',
            '+CD', '+CD-A1', '+CD-G1', '+CD-K1', '+CD-K1.1', '+CD-K1.2',
            '+CD-K1.3', '+CD-K2', '+CD-U1', '+CD-Z1', '+CD-Z2', '+DG', '+EXT', '+PF',
        ]
    },
    14: {
        'title': 'Power feed AC',
        'tags': [
            '-EL1', '-EL2', '-F1:2', '-F1:4', '-F1:6', '-F2', '-F3', '-PE',
            '-X0:1', '-X0:2', '-X1', '-X1:1',
            '+CD-F1', '+DG-PE', '+DG-X0', '+Q1-Q1',
        ]
    },
    15: {
        'title': 'Power supply DC',
        'tags': [
            '-F4', '-F5', '-F6', '-G1', '-K0.2', '-K1.0', '-X0:14', '-X0:9',
            '-X3', '-XS3',
        ]
    },
    18: {
        'title': 'Contactor control',
        'tags': [
            '-A1', '-K1', '-K1.0', '-K1.1', '-K1.2', '-K1.3', '-K2', '-K3',
            '-KR1', '-U1', '-X3', '-XS3',
        ]
    },
    19: {
        'title': 'Contactor control',
        'tags': [
            '-K1', '-K1.1', '-K1.2', '-K1.3', '-K2', '-K3', '-KR1', '-X3',
        ]
    },
    21: {
        'title': 'Extractor motor',
        'tags': [
            '-F7', '-K1.2', '-K1.3', '-SH', '-WM21', '-WM22',
            '+DG-SH', '+DG-XM2a', '+DG-XM2b',
        ]
    },
}


class AutoPlacementTester:
    """Test auto-placement accuracy on problematic pages."""

    def __init__(self, pdf_path: Path, debug: bool = False):
        self.pdf_path = Path(pdf_path)
        self.debug = debug
        self.debug_dir = Path('placement_test_debug')

        if self.debug:
            self.debug_dir.mkdir(exist_ok=True)

    def test_page(self, page_num: int, ground_truth: Dict) -> PageTestResult:
        """Test auto-placement on a single page.

        Args:
            page_num: 0-indexed page number
            ground_truth: Dict with 'title' and 'tags' keys

        Returns:
            PageTestResult with comparison data
        """
        expected_tags = set(ground_truth['tags'])
        expected_title = ground_truth['title']

        # Run auto-placement
        with ComponentPositionFinder(self.pdf_path) as finder:
            # Get page title
            page_title = finder.get_page_title(page_num)

            # Find positions for expected tags
            result = finder.find_positions(
                device_tags=list(expected_tags),
                search_all_pages=False  # Use default schematic page range
            )

            # Collect found tags on this specific page
            found_tags_on_page = set()
            for tag, pos in result.positions.items():
                if pos.page == page_num:
                    found_tags_on_page.add(tag)

            # Also check ambiguous matches (multi-page components)
            for tag, positions in result.ambiguous_matches.items():
                for pos in positions:
                    if pos.page == page_num:
                        found_tags_on_page.add(tag)

        # Compare results
        missed_tags = expected_tags - found_tags_on_page
        unexpected_tags = found_tags_on_page - expected_tags

        accuracy = (
            len(found_tags_on_page & expected_tags) / len(expected_tags)
            if expected_tags else 1.0
        )

        result_obj = PageTestResult(
            page_num=page_num,
            page_title=page_title,
            expected_tags=sorted(expected_tags),
            found_tags=sorted(found_tags_on_page),
            missed_tags=sorted(missed_tags),
            unexpected_tags=sorted(unexpected_tags),
            accuracy=accuracy,
            total_expected=len(expected_tags),
            total_found=len(found_tags_on_page & expected_tags),
        )

        # Generate debug visualization if requested
        if self.debug:
            self._generate_debug_image(page_num, result_obj)

        return result_obj

    def _generate_debug_image(self, page_num: int, result: PageTestResult):
        """Generate visual debug image showing found vs missed tags.

        Creates a PNG image of the page with:
        - Green rectangles around found tags
        - Red rectangles around missed tags (manual annotation needed)
        - Text labels showing tag names
        """
        try:
            with fitz.open(self.pdf_path) as doc:
                page = doc[page_num]

                # Render page to pixmap
                mat = fitz.Matrix(2.0, 2.0)  # 2x scale for clarity
                pix = page.get_pixmap(matrix=mat)

                # Convert to PIL for annotation
                from PIL import Image, ImageDraw, ImageFont
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                draw = ImageDraw.Draw(img)

                # Find positions of found tags to draw green boxes
                with ComponentPositionFinder(self.pdf_path) as finder:
                    positions_result = finder.find_positions(
                        device_tags=result.found_tags,
                        search_all_pages=False
                    )

                    for tag in result.found_tags:
                        if tag in positions_result.positions:
                            pos = positions_result.positions[tag]
                            if pos.page == page_num:
                                # Convert PDF coordinates to image coordinates
                                x = pos.x * 2
                                y = pos.y * 2
                                w = pos.width * 2
                                h = pos.height * 2

                                # Draw green rectangle
                                draw.rectangle(
                                    [x - w/2, y - h/2, x + w/2, y + h/2],
                                    outline='green',
                                    width=3
                                )

                                # Draw tag label
                                draw.text((x, y - h/2 - 15), tag, fill='green')

                # Note: Missed tags require manual annotation since we don't
                # know their positions (that's why they were missed!)
                # We'll just add a text note at the top of the image

                if result.missed_tags:
                    missed_text = f"MISSED TAGS: {', '.join(result.missed_tags)}"
                    draw.text((10, 10), missed_text, fill='red')

                # Save debug image
                output_path = self.debug_dir / f"page_{page_num + 1}_placement_test.png"
                img.save(output_path)
                print(f"  Debug image saved: {output_path}")

        except Exception as e:
            print(f"  Warning: Could not generate debug image: {e}")

    def test_all_pages(self, page_numbers: List[int] = None) -> TestSummary:
        """Test auto-placement on all problematic pages.

        Args:
            page_numbers: Optional list of specific pages to test (1-indexed).
                        If None, tests all pages in GROUND_TRUTH.

        Returns:
            TestSummary with overall results
        """
        if page_numbers:
            # Convert 1-indexed to 0-indexed
            pages_to_test = {p - 1: GROUND_TRUTH[p - 1] for p in page_numbers
                           if p - 1 in GROUND_TRUTH}
        else:
            pages_to_test = GROUND_TRUTH

        page_results = []
        total_expected = 0
        total_found = 0

        for page_num, ground_truth in sorted(pages_to_test.items()):
            print(f"\nTesting page {page_num + 1}...")
            result = self.test_page(page_num, ground_truth)
            page_results.append(result)

            total_expected += result.total_expected
            total_found += result.total_found

            print(f"  Expected: {result.total_expected} tags")
            print(f"  Found: {result.total_found} tags")
            print(f"  Accuracy: {result.accuracy * 100:.1f}%")

            if result.missed_tags:
                print(f"  Missed: {', '.join(result.missed_tags)}")

        overall_accuracy = total_found / total_expected if total_expected else 0.0

        summary = TestSummary(
            test_date=datetime.now().isoformat(),
            pages_tested=len(page_results),
            total_expected=total_expected,
            total_found=total_found,
            total_missed=total_expected - total_found,
            overall_accuracy=overall_accuracy,
            page_results=page_results
        )

        return summary

    def analyze_missed_tags(self, summary: TestSummary) -> Dict:
        """Analyze why tags were missed and identify root causes.

        Returns:
            Dictionary with analysis results
        """
        analysis = {
            'root_causes': [],
            'tag_details': {}
        }

        with ComponentPositionFinder(self.pdf_path) as finder:
            with fitz.open(self.pdf_path) as doc:
                for page_result in summary.page_results:
                    page_num = page_result.page_num
                    page = doc[page_num]

                    for tag in page_result.missed_tags:
                        # Check if tag text exists in PDF text extraction
                        text_content = page.get_text()

                        tag_analysis = {
                            'tag': tag,
                            'page': page_num + 1,
                            'text_exists': tag in text_content,
                            'page_was_skipped': page_num in finder._page_skip_cache and finder._page_skip_cache[page_num],
                            'page_title': page_result.page_title
                        }

                        # Determine likely cause
                        if tag_analysis['page_was_skipped']:
                            tag_analysis['likely_cause'] = 'Page was skipped by classifier'
                        elif not tag_analysis['text_exists']:
                            tag_analysis['likely_cause'] = 'Tag text not extractable from PDF'
                        else:
                            tag_analysis['likely_cause'] = 'Tag text present but not matched by algorithm'

                        analysis['tag_details'][tag] = tag_analysis

        # Aggregate root causes
        cause_counts = {}
        for details in analysis['tag_details'].values():
            cause = details['likely_cause']
            cause_counts[cause] = cause_counts.get(cause, 0) + 1

        analysis['root_causes'] = [
            {'cause': cause, 'count': count}
            for cause, count in sorted(cause_counts.items(), key=lambda x: -x[1])
        ]

        return analysis

    def generate_report(self, summary: TestSummary, analysis: Dict, output_path: Path):
        """Generate markdown test report.

        Args:
            summary: Test summary results
            analysis: Root cause analysis
            output_path: Path to save report
        """
        report = []
        report.append("# Auto-Placement Accuracy Test Report\n")
        report.append(f"**Test Date:** {summary.test_date}\n")
        report.append(f"**PDF:** {self.pdf_path.name}\n")
        report.append("")

        # Summary
        report.append("## Summary\n")
        report.append(f"- **Pages tested:** {summary.pages_tested}")
        report.append(f"- **Total expected tags:** {summary.total_expected}")
        report.append(f"- **Total found tags:** {summary.total_found}")
        report.append(f"- **Total missed tags:** {summary.total_missed}")
        report.append(f"- **Overall accuracy:** {summary.overall_accuracy * 100:.1f}%")
        report.append("")

        # Per-page results
        report.append("## Per-Page Results\n")
        for result in summary.page_results:
            report.append(f"### Page {result.page_num + 1}: {result.page_title}\n")
            report.append(f"- **Expected tags:** {result.total_expected}")
            report.append(f"- **Found tags:** {result.total_found}")
            report.append(f"- **Accuracy:** {result.accuracy * 100:.1f}%")

            if result.missed_tags:
                report.append(f"- **Missed tags:** {', '.join(result.missed_tags)}")

            if result.unexpected_tags:
                report.append(f"- **Unexpected tags:** {', '.join(result.unexpected_tags)}")

            report.append("")

        # Root cause analysis
        report.append("## Root Cause Analysis\n")
        for cause_info in analysis['root_causes']:
            report.append(f"### {cause_info['cause']}\n")
            report.append(f"**Count:** {cause_info['count']} tags\n")

            # List affected tags
            affected_tags = [
                tag for tag, details in analysis['tag_details'].items()
                if details['likely_cause'] == cause_info['cause']
            ]
            report.append(f"**Affected tags:** {', '.join(sorted(affected_tags))}\n")

        # Detailed tag analysis
        report.append("## Detailed Tag Analysis\n")
        report.append("| Tag | Page | Text Exists | Page Skipped | Likely Cause |")
        report.append("|-----|------|-------------|--------------|--------------|")
        for tag, details in sorted(analysis['tag_details'].items()):
            report.append(
                f"| {tag} | {details['page']} | "
                f"{'Yes' if details['text_exists'] else 'No'} | "
                f"{'Yes' if details['page_was_skipped'] else 'No'} | "
                f"{details['likely_cause']} |"
            )
        report.append("")

        # Recommendations
        report.append("## Recommendations\n")

        has_skipped_pages = any(
            'Page was skipped' in d['likely_cause']
            for d in analysis['tag_details'].values()
        )
        has_extraction_issues = any(
            'not extractable' in d['likely_cause']
            for d in analysis['tag_details'].values()
        )
        has_matching_issues = any(
            'not matched' in d['likely_cause']
            for d in analysis['tag_details'].values()
        )

        if has_skipped_pages:
            report.append("### 1. Page Classification Issues")
            report.append("- Some pages are being incorrectly skipped by the page classifier")
            report.append("- Review `classify_page()` and `should_skip_page_by_title()` logic")
            report.append("- Check title block extraction for these page types")
            report.append("")

        if has_extraction_issues:
            report.append("### 2. Text Extraction Issues")
            report.append("- Some tags cannot be extracted from PDF text layer")
            report.append("- May be embedded as images or using non-standard encoding")
            report.append("- Consider OCR fallback for these cases")
            report.append("")

        if has_matching_issues:
            report.append("### 3. Tag Matching Algorithm Issues")
            report.append("- Tag text is present but not being matched by the algorithm")
            report.append("- Review `_match_text_to_tag()` and `_build_tag_variants()` logic")
            report.append("- May need more flexible pattern matching or variant generation")
            report.append("")

        # Write report
        output_path.write_text('\n'.join(report))
        print(f"\nReport saved to: {output_path}")

    def save_json_results(self, summary: TestSummary, analysis: Dict, output_path: Path):
        """Save test results as JSON for CI/CD integration.

        Args:
            summary: Test summary results
            analysis: Root cause analysis
            output_path: Path to save JSON file
        """
        data = {
            'summary': summary.to_dict(),
            'analysis': analysis
        }

        output_path.write_text(json.dumps(data, indent=2))
        print(f"JSON results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Test auto-placement accuracy on problematic pages'
    )
    parser.add_argument(
        '--pdf',
        default='examples/DRAWER.pdf',
        help='Path to DRAWER.pdf (default: examples/DRAWER.pdf)'
    )
    parser.add_argument(
        '--page',
        type=int,
        help='Test only this specific page number (1-indexed)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Generate debug visualizations'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Generate report without debug images'
    )

    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: PDF not found: {pdf_path}")
        return 1

    # Check if ground truth is filled in
    if any(not data['tags'] or data['tags'] == ['-K1', '-K2', '-K3']
           for data in GROUND_TRUTH.values()):
        print("\n" + "="*70)
        print("WARNING: GROUND TRUTH DATA NOT YET FILLED IN!")
        print("="*70)
        print("\nBefore running this test, you must:")
        print("1. Open DRAWER.pdf in a PDF viewer")
        print("2. Manually inspect pages 9, 10, 15, 16, 19, 20, 22")
        print("3. List all visible device tags (e.g., -K1, -U1, +DG-M1)")
        print("4. Update the GROUND_TRUTH dictionary in this script")
        print("\nExclude cross-reference tags in blue (format: K2:61/19.9)")
        print("="*70 + "\n")

        response = input("Continue anyway for testing? (y/n): ")
        if response.lower() != 'y':
            return 0

    # Run tests
    debug = args.debug and not args.report_only
    tester = AutoPlacementTester(pdf_path, debug=debug)

    page_numbers = [args.page] if args.page else None
    summary = tester.test_all_pages(page_numbers)

    # Analyze missed tags
    print("\nAnalyzing missed tags...")
    analysis = tester.analyze_missed_tags(summary)

    # Generate report
    report_path = Path('AUTO_PLACEMENT_ACCURACY_TEST.md')
    tester.generate_report(summary, analysis, report_path)

    # Save JSON results
    json_path = Path('auto_placement_test_results.json')
    tester.save_json_results(summary, analysis, json_path)

    # Print summary
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print(f"Overall Accuracy: {summary.overall_accuracy * 100:.1f}%")
    print(f"Found: {summary.total_found}/{summary.total_expected} tags")
    print(f"Missed: {summary.total_missed} tags")
    print("="*70)

    return 0


if __name__ == '__main__':
    exit(main())
