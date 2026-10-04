"""Business descriptions for the data dictionary (structure itself is read from the database)."""

TABLE_DOCS = {
    "agent": ("1 row / agent", "Agent master data and current contract (denormalised for quick lookup)"),
    "policy": ("1 row / policy", "Source sales transactions the KPI is calculated from"),
    "kpi_rule": ("1 row / rule version", "Thresholds stored as data with effective dates. The KPI has already changed once, so the "
                                         "next change is an INSERT, and past months stay judged by the rule in force at the time"),
    "agent_monthly_kpi": ("1 row / agent / month", "CORE TRACKING TABLE: measured values, pass/fail per condition, running "
                                                   "streaks and the contract decision"),
    "agent_contract_history": ("1 row / contract period", "Audit trail of every contract change with reason and trigger month"),
}

COLUMN_DOCS = {
    "agent": {
        "agent_id": "Surrogate key", "agent_code": "Business agent code", "agent_name": "Agent name",
        "hire_date": "Start date", "termination_date": "NULL = still active",
        "current_contract_type": "SALARY / COMMISSION (kept in sync by the monthly job)",
        "created_at": "Audit timestamp", "updated_at": "Audit timestamp",
    },
    "policy": {
        "policy_id": "Surrogate key", "policy_no": "Policy number", "agent_id": "Selling agent",
        "product_type": "LIFE / PA / HEALTH …", "issue_date": "Date the policy became new business",
        "premium_amount": "Premium of the policy", "policy_status": "ACTIVE / CANCELLED / LAPSED (cancelled excluded from KPI)",
        "created_at": "Audit timestamp",
    },
    "kpi_rule": {
        "rule_id": "Rule key", "rule_name": "e.g. Sales KPI 2026",
        "min_total_premium": "Pass if total premium > this (15,000)",
        "min_new_policy_count": "Pass if new policies > this (5)",
        "consecutive_months": "Streak length that triggers a contract change (3)",
        "effective_from": "Rule valid from", "effective_to": "Rule valid to (exclusive); NULL = current",
    },
    "agent_monthly_kpi": {
        "agent_id": "Agent evaluated", "kpi_month": "First day of the evaluated month",
        "rule_id": "Rule used for this month", "total_premium": "Sum of new-policy premium in the month",
        "new_policy_count": "Number of new policies in the month", "is_premium_pass": "total_premium > 15,000",
        "is_policy_pass": "new_policy_count > 5", "is_pass": "Both conditions passed",
        "consecutive_pass": "Months passed in a row (0 after a fail)",
        "consecutive_fail": "Months failed in a row (0 after a pass)",
        "contract_type_before": "Contract in force during the month",
        "contract_action": "NONE / TO_COMMISSION / TO_SALARY", "contract_type_after": "Contract from next month",
        "calculated_at": "When the job ran",
    },
    "agent_contract_history": {
        "contract_id": "Contract period key", "agent_id": "Agent", "contract_type": "SALARY / COMMISSION",
        "effective_from": "Start of the period", "effective_to": "End (exclusive); NULL = current contract",
        "change_reason": "INITIAL / FAIL_3_CONSECUTIVE / PASS_3_CONSECUTIVE / MANUAL",
        "trigger_kpi_month": "KPI month that caused the change",
    },
}
