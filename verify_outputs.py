"""Independently verify the synthetic ABM grading outputs."""

import csv
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
REVISED = ROOT / "outputs" / "revised"


def read_csv(path):
    """Read a CSV file and return its rows as dictionaries."""
    if not path.exists():
        raise AssertionError(f"Missing required file: {path}")
    with path.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def approximately_equal(actual, expected, tolerance=0.0006):
    """Allow for values rounded to three decimal places."""
    return abs(float(actual) - expected) <= tolerance


accounts = read_csv(DATA / "accounts.csv")
assignments = read_csv(DATA / "assignment.csv")
stages = read_csv(DATA / "stage_history.csv")
sales = read_csv(DATA / "sales_view.csv")
grades = read_csv(REVISED / "play_grades.csv")
flagged = read_csv(REVISED / "flagged_accounts.csv")

# Check 1: account count and uniqueness
account_ids = [row["account_id"] for row in accounts]

assert len(accounts) == 160, "Expected 160 accounts."
assert len(set(account_ids)) == 160, "Account IDs must be unique."

# Check 2: experimental assignment
arm_counts = defaultdict(Counter)

for row in assignments:
    arm_counts[row["play_id"]][row["arm"]] += 1

for play_id in ("P1", "P2", "P3", "P4"):
    assert arm_counts[play_id] == Counter(
        {"treated": 25, "holdout": 15}
    ), f"Unexpected assignment for {play_id}: {arm_counts[play_id]}"

# Check 3: independently recalculate advancement
stage_lookup = {
    (row["account_id"], int(row["day"])): int(row["stage"])
    for row in stages
}

advance_results = defaultdict(lambda: defaultdict(list))

for row in assignments:
    account_id = row["account_id"]
    advanced = int(
        stage_lookup[(account_id, 60)]
        > stage_lookup[(account_id, 0)]
    )
    advance_results[row["play_id"]][row["arm"]].append(advanced)

assert len(grades) == 4, "Expected one grade for each of four plays."

for row in grades:
    play_id = row["play_id"]
    treated = advance_results[play_id]["treated"]
    holdout = advance_results[play_id]["holdout"]

    treated_rate = sum(treated) / len(treated)
    holdout_rate = sum(holdout) / len(holdout)
    lift = treated_rate - holdout_rate

    assert approximately_equal(
        row["treated_advance_rate"], treated_rate
    ), f"Treated rate mismatch for {play_id}"

    assert approximately_equal(
        row["holdout_advance_rate"], holdout_rate
    ), f"Holdout rate mismatch for {play_id}"

    assert approximately_equal(
        row["lift"], lift
    ), f"Lift mismatch for {play_id}"

    p_value = float(row["permutation_p"])
    assert 0 <= p_value <= 1, f"Invalid p-value for {play_id}"

    expected_revised_grade = (
        row["grade"]
        if row["grade"] not in {"A", "B"} or p_value < 0.10
        else "C"
    )

    assert (
        row["revised_grade"] == expected_revised_grade
    ), f"Revised grade mismatch for {play_id}"

# Check 4: independently rebuild the disagreement queue
marketing_day_60 = {
    row["account_id"]: int(row["stage"])
    for row in stages
    if int(row["day"]) == 60
}

expected_flagged = {
    row["account_id"]
    for row in sales
    if abs(
        marketing_day_60[row["account_id"]]
        - int(row["sales_stage"])
    ) >= 2
}

saved_flagged = {row["account_id"] for row in flagged}

assert saved_flagged == expected_flagged, (
    "The saved disagreement queue does not match the raw data."
)

print("PASS: 160 unique synthetic accounts")
print("PASS: each play has 25 treated and 15 holdout accounts")
print("PASS: advance rates and lift match the raw stage data")
print("PASS: revised A/B grades require p < 0.10")
print(f"PASS: {len(saved_flagged)} disagreement records verified")
print("All independent verification checks passed.")