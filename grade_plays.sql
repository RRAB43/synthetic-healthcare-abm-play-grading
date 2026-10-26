-- SYNTHETIC DATA ONLY. Grading logic for account-based plays.
-- Unit of analysis is the account, not the lead. A stage "advance" means the
-- account's day-60 stage is higher than its day-0 stage.
-- Stages: 0 Unaware, 1 Aware, 2 Engaged, 3 Evaluating, 4 Opportunity, 5 Won.
-- Thresholds below are illustrative; in a real program, set them BEFORE the play runs.

-- name: views
CREATE VIEW account_level AS
WITH s0 AS (SELECT account_id, stage FROM stage_history WHERE day = 0),
     s60 AS (SELECT account_id, stage FROM stage_history WHERE day = 60),
     ev AS (
       SELECT account_id,
              COUNT(*)                          AS events,
              SUM(event_type = 'click')         AS clicks,
              SUM(event_type = 'meeting')       AS meetings,
              COUNT(DISTINCT role)              AS roles_engaged
       FROM engagement_events
       GROUP BY account_id)
SELECT a.account_id, a.archetype, asg.play_id, asg.arm,
       s0.stage  AS stage_d0,
       s60.stage AS stage_d60,
       CASE WHEN s60.stage > s0.stage THEN 1 ELSE 0 END AS advanced,
       COALESCE(ev.events, 0)        AS events,
       COALESCE(ev.clicks, 0)        AS clicks,
       COALESCE(ev.meetings, 0)      AS meetings,
       COALESCE(ev.roles_engaged, 0) AS roles_engaged
FROM accounts a
JOIN assignment asg ON asg.account_id = a.account_id
JOIN s0  ON s0.account_id  = a.account_id
JOIN s60 ON s60.account_id = a.account_id
LEFT JOIN ev ON ev.account_id = a.account_id;

-- name: play_grades
-- Grade rules:
--   A: stage-advance lift >= 15 pts vs holdout AND avg buying roles engaged >= 2
--   B: lift >= 5 pts
--   C: lift < 5 pts but treated accounts show >= 1.5x the holdout's activity (activity only)
--   D: otherwise
WITH arm AS (
  SELECT play_id, arm,
         COUNT(*)           AS n,
         AVG(advanced)      AS advance_rate,
         AVG(roles_engaged) AS avg_roles,
         AVG(events)        AS avg_events,
         AVG(clicks)        AS avg_clicks
  FROM account_level
  GROUP BY play_id, arm),
paired AS (
  SELECT t.play_id,
         t.n AS treated_n, h.n AS holdout_n,
         t.advance_rate AS treated_rate, h.advance_rate AS holdout_rate,
         t.advance_rate - h.advance_rate AS lift,
         t.avg_roles,
         t.avg_events AS treated_events, h.avg_events AS holdout_events,
         t.avg_clicks AS treated_clicks
  FROM arm t
  JOIN arm h ON h.play_id = t.play_id AND h.arm = 'holdout'
  WHERE t.arm = 'treated')
SELECT p.play_id,
       pl.play_name,
       p.treated_n, p.holdout_n,
       ROUND(p.treated_rate, 3)   AS treated_advance_rate,
       ROUND(p.holdout_rate, 3)   AS holdout_advance_rate,
       ROUND(p.lift, 3)           AS lift,
       ROUND(p.avg_roles, 2)      AS avg_roles_engaged,
       ROUND(p.treated_clicks, 2) AS avg_clicks_per_treated_account,
       CASE WHEN p.lift >= 0.15 AND p.avg_roles >= 2 THEN 'A'
            WHEN p.lift >= 0.05 THEN 'B'
            WHEN p.treated_events >= 1.5 * p.holdout_events THEN 'C'
            ELSE 'D' END AS grade
FROM paired p
JOIN plays pl ON pl.play_id = p.play_id
ORDER BY p.play_id;

-- name: misalignment
-- Accounts where marketing's day-60 stage and sales' stage differ by 2+ stages.
SELECT a.account_id, a.archetype,
       s60.stage       AS marketing_stage,
       sv.sales_stage  AS sales_stage,
       ABS(s60.stage - sv.sales_stage) AS gap
FROM accounts a
JOIN stage_history s60 ON s60.account_id = a.account_id AND s60.day = 60
JOIN sales_view sv     ON sv.account_id = a.account_id
WHERE ABS(s60.stage - sv.sales_stage) >= 2
ORDER BY gap DESC, a.archetype, a.account_id;

-- name: account_level_rows
SELECT play_id, arm, advanced FROM account_level;
