-- =====================================================================
-- Monthly KPI job - run once per month, in month order, after month-end.
-- Parameter  :kpi_month  = first day of the month to evaluate ('2026-03-01')
-- =====================================================================

-- Step 1: evaluate every active agent for the month and record the result
INSERT INTO agent_monthly_kpi (
    agent_id, kpi_month, rule_id,
    total_premium, new_policy_count,
    is_premium_pass, is_policy_pass, is_pass,
    consecutive_pass, consecutive_fail,
    contract_type_before, contract_action, contract_type_after
)
WITH
m AS (
    SELECT DATE(:kpi_month) AS kpi_month,
           DATE(:kpi_month, '+1 month') AS next_month,
           DATE(:kpi_month, '-1 month') AS prev_month
),
rule AS (
    SELECT r.* FROM kpi_rule r, m
    WHERE r.effective_from <= m.kpi_month
      AND (r.effective_to IS NULL OR r.effective_to > m.kpi_month)
),
-- every agent employed during the month gets a row, even with zero sales
active_agent AS (
    SELECT a.agent_id FROM agent a, m
    WHERE a.hire_date < m.next_month
      AND (a.termination_date IS NULL OR a.termination_date >= m.kpi_month)
),
sales AS (
    SELECT p.agent_id,
           SUM(p.premium_amount) AS total_premium,
           COUNT(*)              AS new_policy_count
    FROM policy p, m
    WHERE p.issue_date >= m.kpi_month
      AND p.issue_date <  m.next_month
      AND p.policy_status <> 'CANCELLED'
    GROUP BY p.agent_id
),
-- contract in force during the month (covers agents hired mid-month)
contract_now AS (
    SELECT h.agent_id, h.contract_type
    FROM agent_contract_history h, m
    WHERE h.effective_from < m.next_month
      AND (h.effective_to IS NULL OR h.effective_to > m.kpi_month)
),
prev AS (
    SELECT k.agent_id, k.consecutive_pass, k.consecutive_fail
    FROM agent_monthly_kpi k, m
    WHERE k.kpi_month = m.prev_month
),
evaluated AS (
    SELECT aa.agent_id, m.kpi_month, rule.rule_id, rule.consecutive_months,
           COALESCE(s.total_premium, 0)    AS total_premium,
           COALESCE(s.new_policy_count, 0) AS new_policy_count,
           COALESCE(s.total_premium, 0)    > rule.min_total_premium    AS is_premium_pass,
           COALESCE(s.new_policy_count, 0) > rule.min_new_policy_count AS is_policy_pass,
           c.contract_type AS contract_type_before,
           COALESCE(p.consecutive_pass, 0) AS prev_pass,
           COALESCE(p.consecutive_fail, 0) AS prev_fail
    FROM active_agent aa
    CROSS JOIN m
    CROSS JOIN rule
    JOIN contract_now c ON c.agent_id = aa.agent_id
    LEFT JOIN sales   s ON s.agent_id = aa.agent_id
    LEFT JOIN prev    p ON p.agent_id = aa.agent_id
),
streaks AS (
    SELECT e.*,
           (is_premium_pass AND is_policy_pass)                          AS is_pass,
           CASE WHEN is_premium_pass AND is_policy_pass THEN prev_pass + 1 ELSE 0 END AS consecutive_pass,
           CASE WHEN is_premium_pass AND is_policy_pass THEN 0 ELSE prev_fail + 1 END AS consecutive_fail
    FROM evaluated e
),
decided AS (
    SELECT s.*,
           CASE
               WHEN contract_type_before = 'SALARY'     AND consecutive_fail >= consecutive_months THEN 'TO_COMMISSION'
               WHEN contract_type_before = 'COMMISSION' AND consecutive_pass >= consecutive_months THEN 'TO_SALARY'
               ELSE 'NONE'
           END AS contract_action
    FROM streaks s
)
SELECT agent_id, kpi_month, rule_id,
       total_premium, new_policy_count,
       is_premium_pass, is_policy_pass, is_pass,
       consecutive_pass, consecutive_fail,
       contract_type_before, contract_action,
       CASE contract_action
           WHEN 'TO_COMMISSION' THEN 'COMMISSION'
           WHEN 'TO_SALARY'     THEN 'SALARY'
           ELSE contract_type_before
       END AS contract_type_after
FROM decided;

-- Step 2: close the current contract of agents whose contract changes
UPDATE agent_contract_history
SET effective_to = DATE(:kpi_month, '+1 month')
WHERE effective_to IS NULL
  AND agent_id IN (SELECT agent_id FROM agent_monthly_kpi
                   WHERE kpi_month = DATE(:kpi_month) AND contract_action <> 'NONE');

-- Step 3: open the new contract, effective from the first day of next month
INSERT INTO agent_contract_history (agent_id, contract_type, effective_from, change_reason, trigger_kpi_month)
SELECT agent_id,
       contract_type_after,
       DATE(:kpi_month, '+1 month'),
       CASE contract_action WHEN 'TO_COMMISSION' THEN 'FAIL_3_CONSECUTIVE' ELSE 'PASS_3_CONSECUTIVE' END,
       kpi_month
FROM agent_monthly_kpi
WHERE kpi_month = DATE(:kpi_month) AND contract_action <> 'NONE';

-- Step 4: keep the denormalised current contract on agent in sync
UPDATE agent
SET current_contract_type = (SELECT k.contract_type_after FROM agent_monthly_kpi k
                             WHERE k.agent_id = agent.agent_id AND k.kpi_month = DATE(:kpi_month)),
    updated_at = CURRENT_TIMESTAMP
WHERE agent_id IN (SELECT agent_id FROM agent_monthly_kpi
                   WHERE kpi_month = DATE(:kpi_month) AND contract_action <> 'NONE');
