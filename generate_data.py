"""
Generates SYNTHETIC account-based-marketing data for a portfolio exercise.

Nothing here is Ambience data, CRM data, or data about any real health system.
Account IDs are SYN-xxxx. The effect sizes below are ASSUMPTIONS written by the
author so the grading method can be demonstrated; the grades that come out are
a test of the method, not findings about any company.
"""
import csv
import os
import random

random.seed(42)
OUT = "data"
os.makedirs(OUT, exist_ok=True)

STAGES = ["Unaware", "Aware", "Engaged", "Evaluating", "Opportunity", "Won"]
ROLES = ["CMIO", "CNIO", "CIO", "CFO_RevCycle", "CMO", "AI_Governance"]

N_PER_ARCHETYPE = 40
N_TREATED = 25  # the remaining 15 per archetype are a stratified random holdout

# Assumed 60-day probability of advancing at least one stage with no play
# (base_p) and the extra probability the play adds (lift). Native-EHR and
# evaluation plays are deliberately built to generate lots of activity with
# little or no real movement, so the grading logic has something to catch.
ARCHETYPES = {
    "expansion":    dict(play_id="P1", ehr=["Epic"],                      base_p=0.20, lift=0.20, ev_mean=6, start=(1, 2)),
    "displacement": dict(play_id="P2", ehr=["Epic"],                      base_p=0.08, lift=0.10, ev_mean=5, start=(0, 2)),
    "ehr_native":   dict(play_id="P3", ehr=["Oracle", "athena"],          base_p=0.04, lift=0.01, ev_mean=9, start=(0, 1)),
    "net_new_eval": dict(play_id="P4", ehr=["Epic", "Oracle", "athena"],  base_p=0.18, lift=0.04, ev_mean=8, start=(1, 3)),
}

PLAYS = [
    ("P1", "Expansion: beyond-physician documentation and revenue capture", "expansion"),
    ("P2", "Displacement: coding-aware layer alongside incumbent scribe", "displacement"),
    ("P3", "Native-EHR: why a platform beyond the EHR vendor's scribe", "ehr_native"),
    ("P4", "Evaluation: pilot-measurement framework for governance review", "net_new_eval"),
]


def noisy_count(mean):
    return max(0, int(round(random.gauss(mean, mean ** 0.5))))


accounts, assignment, stage_rows, events, sales = [], [], [], [], []
acct_n = 0

for archetype, cfg in ARCHETYPES.items():
    ids = []
    for _ in range(N_PER_ARCHETYPE):
        acct_n += 1
        ids.append(f"SYN-{acct_n:04d}")
    random.shuffle(ids)
    treated_ids = set(ids[:N_TREATED])

    for account_id in ids:
        treated = account_id in treated_ids
        start = random.randint(*cfg["start"])
        p = cfg["base_p"] + (cfg["lift"] if treated else 0.0)
        advanced = random.random() < p

        stage0 = start
        stage30 = start
        stage60 = start
        if advanced:
            jump = 2 if random.random() < 0.2 else 1
            new_stage = min(5, start + jump)
            adv_day = random.randint(1, 60)
            stage60 = new_stage
            stage30 = new_stage if adv_day <= 30 else start

        accounts.append([account_id, archetype, random.choice(cfg["ehr"]),
                         random.choice(["250-500", "500-1000", "1000+"])])
        assignment.append([account_id, cfg["play_id"], "treated" if treated else "holdout"])
        stage_rows += [[account_id, 0, stage0], [account_id, 30, stage30], [account_id, 60, stage60]]

        # Engagement events: treated accounts get far more activity. Accounts that
        # truly advanced engage a broader buying committee (a consequence, not a cause).
        n_events = noisy_count(cfg["ev_mean"] if treated else 1.0)
        k_roles = random.randint(3, 5) if advanced else random.randint(1, 2)
        role_pool = random.sample(ROLES, k_roles)
        weights = [0.45, 0.25, 0.12, 0.18] if advanced else [0.60, 0.33, 0.06, 0.01]
        for _ in range(n_events):
            events.append([account_id, random.randint(0, 59),
                           random.choices(["open", "click", "webinar", "meeting"], weights)[0],
                           random.choice(role_pool)])

        # Sales' view of the same account at day 60; ~15% disagree by 2+ stages.
        shift = random.choices([-2, -1, 0, 1, 2], [0.07, 0.08, 0.70, 0.08, 0.07])[0]
        sales.append([account_id, max(0, min(5, stage60 + shift))])


def write(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


write("accounts.csv", ["account_id", "archetype", "ehr", "bed_band"], accounts)
write("plays.csv", ["play_id", "play_name", "target_archetype"], PLAYS)
write("assignment.csv", ["account_id", "play_id", "arm"], assignment)
write("stage_history.csv", ["account_id", "day", "stage"], stage_rows)
write("engagement_events.csv", ["account_id", "day", "event_type", "role"], events)
write("sales_view.csv", ["account_id", "sales_stage"], sales)

print(f"SYNTHETIC data written to ./{OUT}: {len(accounts)} accounts, {len(events)} events")
