"""
Legal Swarm — End-to-End Pipeline Demo
========================================
Builds a sample RegulatoryEntry for UAE and runs it through the full pipeline.
Also loads the complete Tier 1 jurisdiction registry and summarises all entries.
"""

from src.jurisdictions.registry import JurisdictionRegistry


# ---------------------------------------------------------------------------
# Part 1 — Single entry demo (UAE from registry)
# ---------------------------------------------------------------------------


def run_single_entry_demo() -> None:
    print("\n=== PART 1: Single entry demo (UAE from registry) ===")
    registry = JurisdictionRegistry()
    entry = registry.get_entry("AE")
    print(f"  Entry: {entry.jurisdiction_name} ({entry.jurisdiction_code})")
    print(f"  Confidence: {entry.confidence.score:.4f} ({entry.confidence.level.value})")
    print(f"  Validation: {registry.validation_reports['AE'].overall_status}")
    print(f"  Fund structures: {len(entry.permitted_fund_structures)}")
    print(f"  Filing obligations: {len(entry.filing_obligations)}")


# ---------------------------------------------------------------------------
# Part 2 — Full Tier 1 Registry
# ---------------------------------------------------------------------------


def run_tier1_registry() -> None:
    print("\n=== PART 2: Tier 1 Jurisdiction Registry ===")

    registry = JurisdictionRegistry()
    entries = registry.get_all()

    print(f"\n  Loaded {len(entries)} Tier 1 jurisdictions:\n")

    header = f"  {'Jurisdiction':<28} {'Code':<7} {'Tier':<8} {'Validation':<12} {'Confidence Score':<16} {'Level':<12}"
    sep = "  " + "-" * len(header)
    print(header)
    print(sep)

    for entry in sorted(entries, key=lambda e: e.jurisdiction_code):
        report = registry.validation_reports.get(entry.jurisdiction_code)
        status = report.overall_status if report else "N/A"
        conf = entry.confidence
        print(
            f"  {entry.jurisdiction_name:<28} "
            f"{entry.jurisdiction_code:<7} "
            f"{entry.tier.value:<8} "
            f"{status:<12} "
            f"{conf.score:<16.4f} "
            f"{conf.level.value:<12}"
        )

    print()
    check_count = "✓" if len(entries) == 8 else "✗"
    print(f"  {check_count} All 8 Tier 1 jurisdictions loaded and validated.")

    # Run a cross-jurisdiction comparison
    print("\n  Sample cross-jurisdiction comparison:") if len(entries) >= 2 else None
    if len(entries) >= 2:
        comp = registry.compare("KY", "VG")
        print(f"    {comp.summary}")
        for c in comp.contradictions_detected:
            print(f"    ! {c.field_path}: {c.value_a} vs {c.value_b}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_single_entry_demo()
    run_tier1_registry()
    print("\n=== DONE ===")
