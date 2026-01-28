#!/usr/bin/env python3
"""Validate auto-placement results against ground truth tag counts.

This script compares the results of the auto-placement feature against the
ground truth established by count_device_tags.py.

Usage:
    python validate_auto_placement.py <placement_results.json>

Where placement_results.json contains auto-placement output in format:
{
    "device_tag": {
        "page": int,
        "x": float,
        "y": float,
        "confidence": float
    },
    ...
}
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class AutoPlacementValidator:
    """Validate auto-placement results against ground truth."""

    def __init__(self, ground_truth_path: Path):
        """Initialize validator with ground truth data.

        Args:
            ground_truth_path: Path to TAG_COUNT_REPORT.json
        """
        self.ground_truth_path = Path(ground_truth_path)
        self.ground_truth = self._load_ground_truth()

    def _load_ground_truth(self) -> Dict:
        """Load ground truth data from JSON report."""
        if not self.ground_truth_path.exists():
            raise FileNotFoundError(f"Ground truth not found: {self.ground_truth_path}")

        with open(self.ground_truth_path) as f:
            return json.load(f)

    def validate(self, placement_results: Dict) -> Dict:
        """Validate placement results against ground truth.

        Args:
            placement_results: Dictionary of auto-placement results

        Returns:
            Validation report dictionary
        """
        gt = self.ground_truth
        gt_tags = set(gt["parts_list"])
        gt_total = gt["total_tag_occurrences"]
        gt_by_page = gt["tags_with_counts"]

        # Extract placed tags
        placed_tags = set(placement_results.keys())
        placement_count = len(placement_results)

        # Calculate metrics
        missing_tags = gt_tags - placed_tags
        extra_tags = placed_tags - gt_tags
        matched_tags = gt_tags & placed_tags

        # Check multi-page components
        multi_page_results = {}
        for tag, positions in placement_results.items():
            if tag in gt["multi_page_tags"]:
                gt_pages = set(gt["multi_page_tags"][tag]["pages"])
                placed_pages = set()

                # Handle both single position and list of positions
                if isinstance(positions, dict):
                    placed_pages.add(positions["page"])
                elif isinstance(positions, list):
                    placed_pages = {p["page"] for p in positions}

                multi_page_results[tag] = {
                    "ground_truth_pages": sorted(gt_pages),
                    "placed_pages": sorted(placed_pages),
                    "missing_pages": sorted(gt_pages - placed_pages),
                    "extra_pages": sorted(placed_pages - gt_pages),
                }

        # Calculate position accuracy for matched tags
        position_accuracy = {}
        for tag in matched_tags:
            if tag not in gt_by_page:
                continue

            gt_positions = gt_by_page[tag]["positions"]
            placed_pos = placement_results[tag]

            # Compare best position
            if isinstance(placed_pos, dict):
                placed_x = placed_pos.get("x", 0)
                placed_y = placed_pos.get("y", 0)
                placed_page = placed_pos.get("page", -1)

                # Find closest ground truth position on same page
                min_dist = float('inf')
                for gt_pos in gt_positions:
                    if gt_pos["page"] == placed_page:
                        dist = ((placed_x - gt_pos["center_x"])**2 +
                               (placed_y - gt_pos["center_y"])**2)**0.5
                        min_dist = min(min_dist, dist)

                if min_dist < float('inf'):
                    position_accuracy[tag] = {
                        "distance": min_dist,
                        "page": placed_page,
                        "within_50pt": min_dist <= 50.0,
                        "within_100pt": min_dist <= 100.0,
                    }

        # Build validation report
        report = {
            "validation_summary": {
                "ground_truth_tags": len(gt_tags),
                "ground_truth_occurrences": gt_total,
                "placed_tags": len(placed_tags),
                "placement_count": placement_count,
                "matched_tags": len(matched_tags),
                "missing_tags": len(missing_tags),
                "extra_tags": len(extra_tags),
                "match_percentage": (len(matched_tags) / len(gt_tags) * 100) if gt_tags else 0,
            },
            "missing_tags": sorted(missing_tags),
            "extra_tags": sorted(extra_tags),
            "multi_page_validation": multi_page_results,
            "position_accuracy": position_accuracy,
        }

        # Calculate overall position accuracy metrics
        if position_accuracy:
            distances = [p["distance"] for p in position_accuracy.values()]
            within_50 = sum(1 for p in position_accuracy.values() if p["within_50pt"])
            within_100 = sum(1 for p in position_accuracy.values() if p["within_100pt"])

            report["position_metrics"] = {
                "tags_with_position_data": len(position_accuracy),
                "average_distance": sum(distances) / len(distances),
                "median_distance": sorted(distances)[len(distances) // 2],
                "max_distance": max(distances),
                "within_50pt": within_50,
                "within_100pt": within_100,
                "within_50pt_percentage": (within_50 / len(position_accuracy) * 100),
                "within_100pt_percentage": (within_100 / len(position_accuracy) * 100),
            }

        return report

    def print_report(self, report: Dict):
        """Print validation report in human-readable format.

        Args:
            report: Validation report from validate()
        """
        print("\n" + "="*70)
        print("AUTO-PLACEMENT VALIDATION REPORT")
        print("="*70)

        summary = report["validation_summary"]
        print("\nSUMMARY")
        print("-" * 70)
        print(f"Ground Truth Tags:        {summary['ground_truth_tags']}")
        print(f"Ground Truth Occurrences: {summary['ground_truth_occurrences']}")
        print(f"Placed Tags:              {summary['placed_tags']}")
        print(f"Placement Count:          {summary['placement_count']}")
        print(f"Matched Tags:             {summary['matched_tags']}")
        print(f"Missing Tags:             {summary['missing_tags']}")
        print(f"Extra Tags:               {summary['extra_tags']}")
        print(f"Match Percentage:         {summary['match_percentage']:.1f}%")

        if report.get("missing_tags"):
            print("\nMISSING TAGS (not placed)")
            print("-" * 70)
            for tag in report["missing_tags"]:
                print(f"  {tag}")

        if report.get("extra_tags"):
            print("\nEXTRA TAGS (not in ground truth)")
            print("-" * 70)
            for tag in report["extra_tags"]:
                print(f"  {tag}")

        if report.get("position_metrics"):
            print("\nPOSITION ACCURACY")
            print("-" * 70)
            pm = report["position_metrics"]
            print(f"Tags Validated:           {pm['tags_with_position_data']}")
            print(f"Average Distance:         {pm['average_distance']:.1f} pt")
            print(f"Median Distance:          {pm['median_distance']:.1f} pt")
            print(f"Max Distance:             {pm['max_distance']:.1f} pt")
            print(f"Within 50pt:              {pm['within_50pt']} ({pm['within_50pt_percentage']:.1f}%)")
            print(f"Within 100pt:             {pm['within_100pt']} ({pm['within_100pt_percentage']:.1f}%)")

        if report.get("multi_page_validation"):
            print("\nMULTI-PAGE COMPONENT VALIDATION")
            print("-" * 70)
            for tag, data in sorted(report["multi_page_validation"].items()):
                gt_pages = data["ground_truth_pages"]
                placed_pages = data["placed_pages"]
                missing = data["missing_pages"]

                status = "OK" if not missing else "INCOMPLETE"
                print(f"  {tag:10s} [{status}]")
                print(f"    Ground Truth: {gt_pages}")
                print(f"    Placed:       {placed_pages}")
                if missing:
                    print(f"    Missing:      {missing}")

        print("\n" + "="*70)

        # Overall assessment
        if summary["match_percentage"] == 100 and not summary["extra_tags"]:
            print("RESULT: PASS - All tags correctly placed")
        elif summary["match_percentage"] >= 90:
            print("RESULT: PARTIAL - Most tags placed with minor issues")
        else:
            print("RESULT: FAIL - Significant placement issues detected")

        print("="*70 + "\n")


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python validate_auto_placement.py <placement_results.json>")
        print("\nExample placement_results.json format:")
        print("""{
    "-K1": {"page": 7, "x": 215.3, "y": 603.0, "confidence": 1.0},
    "-A1": {"page": 7, "x": 39.3, "y": 55.1, "confidence": 1.0},
    ...
}""")
        return 1

    placement_file = Path(sys.argv[1])
    if not placement_file.exists():
        print(f"ERROR: Placement results file not found: {placement_file}")
        return 1

    # Load placement results
    with open(placement_file) as f:
        placement_results = json.load(f)

    # Load ground truth
    ground_truth_path = Path(__file__).parent / "TAG_COUNT_REPORT.json"

    # Validate
    validator = AutoPlacementValidator(ground_truth_path)
    report = validator.validate(placement_results)

    # Print report
    validator.print_report(report)

    # Save detailed report
    report_output = placement_file.parent / f"{placement_file.stem}_validation.json"
    with open(report_output, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Detailed validation report saved to: {report_output}\n")

    # Return exit code based on result
    if report["validation_summary"]["match_percentage"] == 100:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
