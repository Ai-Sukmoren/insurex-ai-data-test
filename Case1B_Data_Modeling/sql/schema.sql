-- =====================================================================
-- InsureX - Agent KPI Validation : Schema (SQLite / ANSI-style SQL)
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. agent : master data of sales agents
-- ---------------------------------------------------------------------
CREATE TABLE agent (
    agent_id              INTEGER      PRIMARY KEY,
    agent_code            VARCHAR(20)  NOT NULL UNIQUE,
    agent_name            VARCHAR(200) NOT NULL,
    hire_date             DATE         NOT NULL,
    termination_date      DATE,                              -- NULL = still active
    current_contract_type VARCHAR(20)  NOT NULL
        CHECK (current_contract_type IN ('SALARY', 'COMMISSION')),
    created_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- 2. policy : transactions - every policy sold by an agent
-- ---------------------------------------------------------------------
CREATE TABLE policy (
    policy_id      INTEGER       PRIMARY KEY,
    policy_no      VARCHAR(30)   NOT NULL UNIQUE,
    agent_id       INTEGER       NOT NULL REFERENCES agent(agent_id),
    product_type   VARCHAR(20)   NOT NULL,                   -- e.g. LIFE, PA, HEALTH
    issue_date     DATE          NOT NULL,                   -- date the policy became new business
    premium_amount DECIMAL(12,2) NOT NULL CHECK (premium_amount >= 0),
    policy_status  VARCHAR(20)   NOT NULL DEFAULT 'ACTIVE'
        CHECK (policy_status IN ('ACTIVE', 'CANCELLED', 'LAPSED')),
    created_at     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_policy_agent_issue ON policy (agent_id, issue_date);

-- ---------------------------------------------------------------------
-- 3. kpi_rule : the validation thresholds, versioned by date.
--    The KPI "has been changed" once already - keeping rules as data
--    means the next change is an INSERT, not a code change, and old
--    months stay evaluated under the rule that applied at the time.
-- ---------------------------------------------------------------------
CREATE TABLE kpi_rule (
    rule_id              INTEGER       PRIMARY KEY,
    rule_name            VARCHAR(100)  NOT NULL,
    min_total_premium    DECIMAL(12,2) NOT NULL,   -- pass if total premium  >  this
    min_new_policy_count INTEGER       NOT NULL,   -- pass if new policies   >  this
    consecutive_months   INTEGER       NOT NULL,   -- streak length that triggers a contract change
    effective_from       DATE          NOT NULL,
    effective_to         DATE                      -- exclusive; NULL = current rule
);

-- ---------------------------------------------------------------------
-- 4. agent_monthly_kpi : ONE ROW PER AGENT PER MONTH (core tracking table)
--    Stores the measured values, the pass/fail result, the running
--    streaks, and the contract decision taken for that month.
-- ---------------------------------------------------------------------
CREATE TABLE agent_monthly_kpi (
    agent_id               INTEGER       NOT NULL REFERENCES agent(agent_id),
    kpi_month              DATE          NOT NULL,   -- first day of month, e.g. 2026-03-01
    rule_id                INTEGER       NOT NULL REFERENCES kpi_rule(rule_id),

    -- measured performance
    total_premium          DECIMAL(12,2) NOT NULL DEFAULT 0,
    new_policy_count       INTEGER       NOT NULL DEFAULT 0,

    -- validation result
    is_premium_pass        BOOLEAN       NOT NULL,   -- total_premium    > min_total_premium
    is_policy_pass         BOOLEAN       NOT NULL,   -- new_policy_count > min_new_policy_count
    is_pass                BOOLEAN       NOT NULL,   -- both of the above

    -- streak tracking (reset to 0 when the opposite result happens)
    consecutive_pass       INTEGER       NOT NULL,
    consecutive_fail       INTEGER       NOT NULL,

    -- contract decision
    contract_type_before   VARCHAR(20)   NOT NULL,   -- contract in force during this month
    contract_action        VARCHAR(20)   NOT NULL
        CHECK (contract_action IN ('NONE', 'TO_COMMISSION', 'TO_SALARY')),
    contract_type_after    VARCHAR(20)   NOT NULL,   -- contract from next month onwards

    calculated_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (agent_id, kpi_month)                -- re-running a month fails loudly instead of duplicating
);
CREATE INDEX ix_kpi_month ON agent_monthly_kpi (kpi_month);

-- ---------------------------------------------------------------------
-- 5. agent_contract_history : full audit trail of contract periods
-- ---------------------------------------------------------------------
CREATE TABLE agent_contract_history (
    contract_id       INTEGER      PRIMARY KEY,
    agent_id          INTEGER      NOT NULL REFERENCES agent(agent_id),
    contract_type     VARCHAR(20)  NOT NULL CHECK (contract_type IN ('SALARY', 'COMMISSION')),
    effective_from    DATE         NOT NULL,
    effective_to      DATE,                     -- exclusive; NULL = current contract
    change_reason     VARCHAR(50)  NOT NULL,    -- INITIAL / FAIL_3_CONSECUTIVE / PASS_3_CONSECUTIVE / MANUAL
    trigger_kpi_month DATE,                     -- the KPI month that caused the change
    FOREIGN KEY (agent_id, trigger_kpi_month) REFERENCES agent_monthly_kpi (agent_id, kpi_month)
);
CREATE INDEX ix_contract_agent ON agent_contract_history (agent_id, effective_from);
