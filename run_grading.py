"""Loads the SYNTHETIC CSVs into SQLite, runs grade_plays.sql, checks the SQL
against an independent Python calculation, and adds a permutation test."""
import csv
import os
import random
import re
import sqlite3
from collections import defaultdict

DATA = "data"
random.seed(7)


def convert(v):
    try:
        return int(v)
    except ValueError:
        return v


def load_table(conn, name):
    with open(os.path.join(DATA, f"{name}.csv")) as f:
        rows = list(csv.reader(f))
    header, body = rows[0], [[convert(v) for v in r] for r in rows[1:]]
    conn.execute(f"CREATE TABLE {name} ({', '.join(header)})")
    conn.executemany(f"INSERT INTO {name} VALUES ({', '.join('?' * len(header))})", body)


def parse_sql(path):
    text = open(path).read()
    parts = re.split(r"^-- name: (\w+)\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def permutation_p(rows, observed, n=10000):
    """One-sided p: how often does shuffling treated/holdout labels give a lift this big?"""
    outcomes = [r[1] for r in rows]
    n_t = sum(1 for r in rows if r[0] == "treated")
    hits = 0
    for _ in range(n):
        random.shuffle(outcomes)
        lift = sum(outcomes[:n_t]) / n_t - sum(outcomes[n_t:]) / (len(outcomes) - n_t)
        if lift >= observed - 1e-12:
            hits += 1
    return hits / n


conn = sqlite3.connect(":memory:")
for t in ["accounts", "plays", "assignment", "stage_history", "engagement_events", "sales_view"]:
    load_table(conn, t)

q = parse_sql("grade_plays.sql")
conn.executescript(q["views"])

cur = conn.execute(q["play_grades"])
cols = [c[0] for c in cur.description]
grades = [dict(zip(cols, r)) for r in cur.fetchall()]

# Independent check: recompute each lift in plain Python from the raw rows.
by_play = defaultdict(list)
for play_id, arm, adv in conn.execute(q["account_level_rows"]):
    by_play[play_id].append((arm, adv))

for g in grades:
    rows = by_play[g["play_id"]]
    t = [a for arm, a in rows if arm == "treated"]
    h = [a for arm, a in rows if arm == "holdout"]
    py_lift = sum(t) / len(t) - sum(h) / len(h)
    assert abs(round(py_lift, 3) - g["lift"]) < 1e-9, (g["play_id"], py_lift, g["lift"])
    assert len(t) == g["treated_n"] and len(h) == g["holdout_n"]
    g["permutation_p"] = permutation_p(rows, py_lift)
    # Revision after baseline run: A and B also require permutation p < 0.10.
    g["revised_grade"] = g["grade"] if g["grade"] not in {"A", "B"} or g["permutation_p"] < 0.10 else "C"

print("SQL lifts match the independent Python recomputation for all plays.\n")
os.makedirs("outputs/revised", exist_ok=True)

with open("outputs/revised/play_grades.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(grades[0].keys()))
    w.writeheader()
    w.writerows(grades)

cur = conn.execute(q["misalignment"])
mcols = [c[0] for c in cur.description]
mis = [dict(zip(mcols, r)) for r in cur.fetchall()]
with open("outputs/revised/flagged_accounts.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=mcols)
    w.writeheader()
    w.writerows(mis)

print("Grading framework v2: A/B require permutation p < 0.10.\n")
print(f"{'play':<4} {'treated':>7} {'holdout':>7} {'t_rate':>7} {'h_rate':>7} {'lift':>7} {'roles':>6} {'clicks':>7} {'p':>7} {'initial':>8} {'v2':>4}")

for g in grades:
    print(f"{g['play_id']:<4} {g['treated_n']:>7} {g['holdout_n']:>7} {g['treated_advance_rate']:>7} "
          f"{g['holdout_advance_rate']:>7} {g['lift']:>7} {g['avg_roles_engaged']:>6} "
          f"{g['avg_clicks_per_treated_account']:>7} {g['permutation_p']:>7.3f} "
          f"{g['grade']:>8} {g['revised_grade']:>4}")
print(f"\nAccounts flagged for marketing/sales stage disagreement (gap >= 2): {len(mis)} of 160")
