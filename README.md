# Synthetic Healthcare ABM Play Grading

A reproducible portfolio project for separating marketing activity from actual
account movement in a healthcare account-based marketing program.

> **Important:** All accounts, events, assignments, outcomes, and grades in this
> repository are synthetic. This project contains no Ambience Healthcare data,
> customer records, or findings about real healthcare organizations.

## Business problem

Marketing teams often report clicks, emails, meetings, and other activity.
Sales teams care more about whether target accounts moved forward.

This project addresses two questions:

1. Did the marketing play create more account advancement than would have
   happened without the play?
2. Where do Marketing and Sales disagree about an account's current stage?

## Run the project

From the project folder, run:

```bash
python3 generate_data.py
python3 run_grading.py
python3 verify_outputs.py
```

No additional packages are required. The project uses Python's standard library
and an in-memory SQLite database.

## Data flow

```text
Synthetic assumptions
        ↓
Six generated CSV files
        ↓
Account-level SQL calculations
        ↓
Treated-versus-holdout comparison
        ↓
One-sided permutation test
        ↓
Revised play grade
        ↓
Marketing–Sales disagreement queue
```

## Key definitions

### Account-based marketing

Account-based marketing, or ABM, treats an entire target organization as the
unit of analysis instead of treating every contact as an unrelated lead.

### Treated account

An account assigned to receive a marketing play.

### Holdout account

An account intentionally not given the play. The holdout group provides a
baseline for estimating what might have happened without the play.

### Advance

An account advances when its day-60 marketing stage is higher than its day-0
stage.

The stages are:

```text
0 = Unaware
1 = Aware
2 = Engaged
3 = Evaluating
4 = Opportunity
5 = Won
```

Advancement is binary in this prototype. Moving forward one stage and moving
forward three stages both count as one advancement.

### Advance rate

```text
Accounts that advanced ÷ total accounts in the group
```

### Lift

```text
Treated advance rate − holdout advance rate
```

A positive lift means treated accounts advanced more frequently than holdout
accounts. Lift alone does not prove that the marketing play caused the result.

### Buying roles

The number of distinct stakeholder roles engaging with a play, such as a
clinical leader, financial leader, IT leader, or operational leader.

### Permutation test

The permutation test repeatedly reshuffles the treated and holdout labels and
asks how often random assignment produces lift at least as large as the
observed lift.

The implementation uses 10,000 reshuffles and a fixed random seed so the
results are reproducible.

### P-value

The p-value measures how surprising the observed lift would be if the play had
no real effect.

This project uses `p < 0.10` as an exploratory significance condition. That
threshold is less strict than the commonly used `p < 0.05`, so it must be
explained honestly.

### Marketing–Sales disagreement

An account is flagged when Marketing's day-60 stage and Sales' recorded stage
differ by at least two stage positions.

A flag does not prove either team is wrong. It creates a queue for review.

## Original grading framework

The first synthetic run assigned grades using lift, buying-role coverage, and
activity.

| Grade | Original rule                                                                           |
| ----- | --------------------------------------------------------------------------------------- |
| A     | Lift is at least 15 percentage points and average buying roles are at least 2           |
| B     | Lift is at least 5 percentage points                                                    |
| C     | Treated activity is at least 1.5 times holdout activity, without sufficient advancement |
| D     | Neither sufficient movement nor sufficient activity                                     |

## Version 2 significance revision

After examining the baseline run, I added this rule:

> A play can retain an A or B only when its one-sided permutation p-value is
> below 0.10.

This is clearly labeled as a post-baseline exploratory revision. In a real
experiment, the threshold should be selected before examining the results.

Version 2 behaves as follows:

| Revised grade | Rule                                                                       |
| ------------- | -------------------------------------------------------------------------- |
| A             | Original grade A and `p < 0.10`                                            |
| B             | Original grade B and `p < 0.10`                                            |
| C             | Original grade C, or an original A/B that fails the significance condition |
| D             | Original grade D                                                           |

## Reproduced synthetic results

| Play                    |     Lift | Permutation p-value | Initial grade | Revised grade |
| ----------------------- | -------: | ------------------: | ------------: | ------------: |
| P1 Expansion            | +34.7 pp |               0.029 |             A |         **A** |
| P2 Displacement         |  +2.7 pp |               0.601 |             C |         **C** |
| P3 Native-EHR           | +12.0 pp |               0.229 |             B |         **C** |
| P4 Evaluation framework | +17.3 pp |               0.169 |             A |         **C** |

Only P1 retains an A after applying the significance condition.

P3 and P4 show apparent positive lift, but the experiment does not provide
enough statistical evidence for them to retain A or B grades.

These results test the grading method. They are not findings about Ambience
Healthcare or any real healthcare organization.

P4 is only a synthetic framework example. It is not assigned to a real account
and must not be presented as evidence of a real customer relationship.

## Independent validation

`verify_outputs.py` independently rebuilds the important results from the raw
CSV files. It verifies:

- 160 unique synthetic accounts.
- 25 treated and 15 holdout accounts for each play.
- Advance rates and lift against the raw stage-history data.
- The revised `p < 0.10` rule for all A and B grades.
- The 16-record Marketing–Sales disagreement queue.

Expected final message:

```text
All independent verification checks passed.
```

This separate validation reduces the risk that an error in the main grading
workflow silently produces convincing but incorrect output.

## Repository structure

```text
.
├── generate_data.py
├── grade_plays.sql
├── run_grading.py
├── verify_outputs.py
├── README.md
├── data/
│   ├── accounts.csv
│   ├── assignment.csv
│   ├── engagement_events.csv
│   ├── plays.csv
│   ├── sales_view.csv
│   └── stage_history.csv
├── outputs/
│   ├── baseline/
│   ├── reference/
│   └── revised/
└── docs/
    └── claim_verification.md
```

## What each important file does

| File                    | Purpose                                                                                                                                   |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `generate_data.py`      | Creates the reproducible synthetic accounts, assignments, events, and stage records                                                       |
| `grade_plays.sql`       | Builds account-level metrics, compares treated and holdout groups, applies the original grading rules, and identifies stage disagreements |
| `run_grading.py`        | Loads the CSV files into SQLite, runs the SQL, calculates permutation p-values, applies the revised rule, and exports results             |
| `verify_outputs.py`     | Independently recalculates important results and stops with an error if an assertion fails                                                |
| `claim_verification.md` | Records which external organization claims are verified, unverified, revised, or removed                                                  |

## Main assumptions
Each synthetic account is assigned to exactly one play and exactly one experimental arm: treated or holdout.

- Stage numbers represent a meaningful progression.
- Day 0 and day 60 are comparable observation points.
- Treated and holdout accounts are assigned fairly.
- Accounts do not receive hidden treatments that contaminate the holdout.
- Events and stages are recorded consistently.
- Each account is counted once within its play and experimental arm.
- A two-stage Marketing–Sales difference is large enough to require review.

## Main limitations
Because four plays are each tested at α = 0.10 without a multiple-testing correction, approximately 4 × 0.10 = 0.4 false-positive results are expected on average when none of the plays has a real effect.

- The dataset is synthetic and reflects authored assumptions.
- Each play has only 40 accounts, so statistical power is limited.
- The p-values are simulated estimates rather than exact analytical values.
- The `p < 0.10` rule was added after the baseline run.
- Multiple plays are tested, but no multiple-testing correction is applied.
- Binary advancement ignores how many stages an account moved.
- The framework measures association unless assignment and experiment controls
  support a causal interpretation.
- Marketing and Sales may use different legitimate stage definitions.
- Activity metrics can indicate interest without proving commercial progress.

## What production use would require

Before using the framework with real CRM data, I would need:

- Stage-change timestamps.
- Sales' official stage definitions.
- Stable account identifiers.
- Role-level contact and engagement data.
- Marketing-play exposure timestamps.
- A pre-registered assignment and grading plan.
- Minimum sample-size and power calculations.
- Checks for missing data, duplicates, contamination, and late-arriving events.
- Access controls for healthcare and customer information.
- Monitoring for data drift and pipeline failures.

## Interview summary

> I built a synthetic ABM measurement framework that compares treated accounts
> with holdout accounts using stage advancement rather than activity alone.
> SQL creates reproducible account-level and play-level metrics. Python runs a
> one-sided permutation test and applies a revised significance gate. A separate
> verification script rebuilds the important calculations from the raw files.
> The project also identifies large Marketing–Sales stage disagreements for
> human review. The data demonstrate the method only and do not make claims
> about Ambience or real healthcare organizations.
