-- =====================================================================
-- Reporting view: the latest KPI position of every agent.
-- Answers "who is at risk of losing the salary contract, and how soon?"
-- =====================================================================
CREATE VIEW v_agent_kpi_status AS
SELECT a.agent_code,
       a.agent_name,
       a.current_contract_type,
       k.kpi_month                                   AS last_kpi_month,
       k.total_premium,
       k.new_policy_count,
       CASE WHEN k.is_pass THEN 'PASS' ELSE 'FAIL' END AS last_result,
       k.consecutive_pass,
       k.consecutive_fail,
       CASE a.current_contract_type
           WHEN 'SALARY' THEN r.consecutive_months - k.consecutive_fail
           ELSE               r.consecutive_months - k.consecutive_pass
       END                                           AS months_to_change,
       CASE
           WHEN a.current_contract_type = 'SALARY'     AND k.consecutive_fail > 0 THEN 'AT RISK'
           WHEN a.current_contract_type = 'COMMISSION' AND k.consecutive_pass > 0 THEN 'RECOVERING'
           ELSE 'STABLE'
       END                                           AS status
FROM agent a
JOIN agent_monthly_kpi k
  ON k.agent_id = a.agent_id
 AND k.kpi_month = (SELECT MAX(kpi_month) FROM agent_monthly_kpi WHERE agent_id = a.agent_id)
JOIN kpi_rule r ON r.rule_id = k.rule_id;
