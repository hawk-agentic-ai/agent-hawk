
# HAWK – Stage 3: GL Booking
*Complete End‑to‑End Technical Documentation (hawk‑3.md)*

> **Audience:** Engineering, Finance Ops, Controls & Audit  
> **Status:** Authoritative for Stage‑3 (GL Booking) after Stage‑2 “Hedge Inception” (hawk‑2) completion.  
> **Scope:** From Stage‑2 handoff to final GL line posting, with multi‑ledger support (IFRS/LOCAL), rules, validations, error handling, and ops runbook.

---

## 0. Executive Summary
Stage‑3 transforms **Stage‑2 hedge events** (booked & reconciled) into **accounting journal lines**. It enforces **rule‑based postings**, ensures **period control**, and provides **full traceability** from the original instruction and deals to the final ledger.  
Key mechanisms:
- **Selectors:** `v_stage2_ready_stage3` exposes only events that are truly ready (Booked + Completed and expected vs acked deals aligned).
- **Rules:** `gl_rules` describes posting logic (scope + DR/CR templates). Supports **multi‑ledger** fan‑out per event.
- **COA:** `gl_coa` validates accounts used by rules.
- **Period Control:** `gl_periods` gates posting to open periods only.
- **Final Ledger:** `gl_journal_lines` stores posted lines, with `export_status` for Stage‑4 handoff.

---

## 1. End‑to‑End Flow
```
FPM Instruction → Stage‑1A/1B checks → Stage‑2 Deal Booking & GL Package
          ↘(stage_2_status=Completed, gl_package_id, acked≥expected)
                           ↓ v_stage2_ready_stage3
                         Stage‑3 Selector
                           ↓
                Rule Matching (gl_rules)
                           ↓
           Amount Key Resolution (from Stage‑2 package)
                           ↓
       Insert into gl_journal_lines (IFRS + LOCAL fan‑out)
                           ↓
         stage_3_status update + audit trail + exports
```

**Inputs:**  
- `hedge_business_events` (HBE) – event header + stage statuses + `assigned_booking_model`  
- Stage‑2 outputs (rates, amounts, package id) – used to compute **amount keys** (see §4.3)  
- `v_stage2_ready_stage3` – selector of eligible events

**Outputs:**  
- `gl_journal_lines` (final DR/CR lines per ledger)  
- `audit_trail` entries (who/what/when)  
- `hedge_business_events.stage_3_status` + diagnostics fields

---

## 2. Data Model (Stage‑3 Core)

### 2.1 `gl_coa` – Chart of Accounts
**Purpose:** Validate account codes; hold optional segment defaults.  
**Key Columns:** `account_code (PK)`, `description`, `segments jsonb`, `active_flag boolean`

**DDL (reference):**
```sql
create table if not exists gl_coa (
  account_code text primary key,
  description  text,
  segments     jsonb,
  active_flag  boolean default true
);
```

**Seed (minimum used by current rules):**
```sql
insert into gl_coa (account_code, description) values
('15001000','Rate Differential (Hist vs Prev)'),
('15001100','CNY Onshore/Offshore Spread'),
('15002000','Proxy/NDF Position'),
('15002100','Embedded Spot Extraction'),
('15003000','USD Funding (Proxy)'),
('21001000','Investment Capital'),
('21001100','Investment Capital – CNY'),
('21001300','Investment Capital – Proxy'),
('33201001','CFH Reserve'),
('65091003','Net Interest / Accruals')
on conflict do nothing;
```

---

### 2.2 `gl_rules` – Posting Rulebook
**Purpose:** Centralize posting logic. Each row = rule with:  
- `scope jsonb` → matchers (event_type, posting_model, currency_type, nav_type, entity filters, ledger hints, etc.)  
- `lines jsonb` → array of DR/CR templates (ledger, account, amount key, optional segments)  
- `priority int`, `enabled bool`, `effective_from/to date`

**DDL (reference):**
```sql
create table if not exists gl_rules (
  rule_id       bigserial primary key,
  enabled       boolean not null default true,
  priority      int not null default 100,
  scope         jsonb not null,
  lines         jsonb not null,
  effective_from date,
  effective_to   date
);
create index if not exists gl_rules_priority_idx on gl_rules(priority);
```

**Rule Seeding (A‑COI, B‑COI, C‑COI, A‑RE):**
```sql
-- A-COI (Matched currencies e.g., HKD/AUD/EUR)
insert into gl_rules (enabled, priority, scope, lines, effective_from) values
(true, 10,
 '{"event_type":"Initiation","posting_model":"A-COI"}',
 '[
   {"ledger":"IFRS","drcr":"DR","account":"15001000","amount":"diff_base","segments":{"pc":"TMU"}},
   {"ledger":"IFRS","drcr":"CR","account":"21001000","amount":"diff_base","segments":{"pc":"TMU"}},
   {"ledger":"LOCAL","drcr":"DR","account":"15001000","amount":"diff_base_local","segments":{"pc":"TMU"}},
   {"ledger":"LOCAL","drcr":"CR","account":"21001000","amount":"diff_base_local","segments":{"pc":"TMU"}}
 ]'::jsonb, current_date);

-- B-COI (Mismatched CNY; onshore/offshore spread)
insert into gl_rules (enabled, priority, scope, lines, effective_from) values
(true, 20,
 '{"event_type":"Initiation","posting_model":"B-COI","currency_type":"CNY"}',
 '[
   {"ledger":"IFRS","drcr":"DR","account":"15001100","amount":"spread_base","segments":{"pc":"TREASURY_BU"}},
   {"ledger":"IFRS","drcr":"CR","account":"21001100","amount":"spread_base","segments":{"pc":"TREASURY_BU"}},
   {"ledger":"LOCAL","drcr":"DR","account":"15001100","amount":"spread_base_local","segments":{"pc":"TREASURY_BU"}},
   {"ledger":"LOCAL","drcr":"CR","account":"21001100","amount":"spread_base_local","segments":{"pc":"TREASURY_BU"}}
 ]'::jsonb, current_date);

-- C-COI (Proxy via NDF)
insert into gl_rules (enabled, priority, scope, lines, effective_from) values
(true, 30,
 '{"event_type":"Initiation","posting_model":"C-COI"}',
 '[
   {"ledger":"IFRS","drcr":"DR","account":"15002000","amount":"proxy_pv_base","segments":{"pc":"INSTC"}},
   {"ledger":"IFRS","drcr":"CR","account":"21001300","amount":"proxy_pv_base","segments":{"pc":"INSTC"}},
   {"ledger":"IFRS","drcr":"DR","account":"15002100","amount":"embedded_spot_base","segments":{"pc":"INSTC"}},
   {"ledger":"IFRS","drcr":"CR","account":"15003000","amount":"funding_base","segments":{"pc":"FUNDING_DESK"}},
   {"ledger":"LOCAL","drcr":"DR","account":"15002000","amount":"proxy_pv_local","segments":{"pc":"INSTC"}},
   {"ledger":"LOCAL","drcr":"CR","account":"21001300","amount":"proxy_pv_local","segments":{"pc":"INSTC"}}
 ]'::jsonb, current_date);

-- A-RE (Revenue matched)
insert into gl_rules (enabled, priority, scope, lines, effective_from) values
(true, 40,
 '{"event_type":"Initiation","posting_model":"A-RE"}',
 '[
   {"ledger":"IFRS","drcr":"DR","account":"33201001","amount":"re_adj_base","segments":{"pc":"UHDRE"}},
   {"ledger":"IFRS","drcr":"CR","account":"21001000","amount":"re_adj_base","segments":{"pc":"HDGRE"}},
   {"ledger":"LOCAL","drcr":"DR","account":"33201001","amount":"re_adj_local","segments":{"pc":"UHDRE"}},
   {"ledger":"LOCAL","drcr":"CR","account":"21001000","amount":"re_adj_local","segments":{"pc":"HDGRE"}}
 ]'::jsonb, current_date);
```

**Rule Matching Algorithm (high level):**
1. Fetch candidates with `enabled=true` within `effective_from/to` window.  
2. **Scope match** (strict equals for provided keys; ignore missing keys).  
3. Sort by `priority asc`; choose first match.  
4. Expand `lines` with amounts and segments (see §4.4).

---

### 2.3 `gl_periods` – Period Control
**Purpose:** Prevent posting to closed months.  
**DDL (reference) + seed current month:**
```sql
create table if not exists gl_periods (
  period_id  text primary key,    -- e.g., '2025-09'
  start_date date not null,
  end_date   date not null,
  is_open    boolean not null default true
);

insert into gl_periods(period_id, start_date, end_date, is_open)
select to_char(date_trunc('month', now()), 'YYYY-MM'),
       date_trunc('month', now())::date,
       (date_trunc('month', now()) + interval '1 month - 1 day')::date,
       true
on conflict (period_id) do nothing;
```

**Trigger Guard (recommended):**
```sql
create or replace function _guard_period_open() returns trigger as $$
begin
  perform 1 from gl_periods p where p.period_id = new.period_id and p.is_open = true;
  if not found then
    raise exception 'GL period % is closed — posting blocked', new.period_id;
  end if;
  return new;
end; $$ language plpgsql;

drop trigger if exists trg_gljl_guard_period on gl_journal_lines;
create trigger trg_gljl_guard_period
  before insert or update on gl_journal_lines
  for each row execute function _guard_period_open();
```

---

### 2.4 `gl_journal_lines` – Final Journal Lines
**Purpose:** The canonical, immutable journal store for Stage‑3.  
**Key Columns:**  
- Identity: `(journal_id, line_no) PK`, `ledger`, `accounting_date`, `period_id`  
- Amounts: `dr_amt`, `cr_amt`, `base_ccy`, `txn_ccy`, `fx_rate`  
- Attribution: `segments jsonb`, `source_refs jsonb` (`event_id`, `instruction_id`, `gl_package_id`, `be_code`, etc.)  
- Lifecycle: `post_status` (POSTED/ERROR), `export_status` (PENDING/EXPORTED)

**Integrity checks (recommended):**
```sql
alter table gl_journal_lines
  add constraint chk_gljl_one_side_positive
  check (
    (dr_amt > 0 and cr_amt = 0) or
    (cr_amt > 0 and dr_amt = 0)
  );
create index if not exists gl_jl_export_idx
  on gl_journal_lines (export_status, ledger, accounting_date);
```

**Export View (for Stage‑4 pickup):**
```sql
create or replace view v_gl_export_ready as
select ledger, accounting_date, period_id,
       journal_id, line_no, account_code,
       dr_amt, cr_amt, base_ccy, txn_ccy, fx_rate,
       segments, source_refs
from gl_journal_lines
where post_status = 'POSTED'
  and export_status = 'PENDING'
  and accounting_date <= current_date;
```

---

## 3. Stage‑2 → Stage‑3 Selector
### 3.1 `v_stage2_ready_stage3`
**Definition (reference pattern):**
```sql
-- Your implementation may join expected vs. acked views and filter statuses.
select h.event_id, h.assigned_booking_model, h.final_hedge_portfolio,
       h.gl_package_id, h.stage_2_completion_time
from hedge_business_events h
join v_event_expected_deals e using (event_id)
join v_event_acked_deals   a using (event_id)
where a.acked_deals >= e.expected_deals
  and h.stage_2_status = 'Completed'
  and h.event_status   = 'Booked';
```

**Diagnostics:**
```sql
select * from v_stage2_ready_stage3;
select * from v_event_expected_deals where event_id='<E>';
select * from v_event_acked_deals    where event_id='<E>';
```

---

## 4. Posting Engine (Service Logic)

### 4.1 Event Selection
- Poll `v_stage2_ready_stage3` (batch window configurable).
- For each event, fetch HBE + Stage‑2 package facts.

### 4.2 Rule Selection
- Build a `rule_context`:
  ```json
  {
    "event_type":"Initiation",
    "posting_model":"A-COI",
    "currency_type":"HKD",
    "nav_type":"COI",
    "entity_id":"ENT001"
  }
  ```
- Query `gl_rules` with `enabled=true`, `effective_from/to` covering `accounting_date`.
- **Scope match**: keys present in scope must equal the context; missing keys are treated as wildcards.
- Select **lowest priority**.

### 4.3 Amount Key Resolution (from Stage‑2 package)
- **A‑COI**: `diff_base`, `diff_base_local` — base‑ccy impact between historical vs current rate.  
- **B‑COI**: `spread_base`, `spread_base_local` — base‑ccy onshore/offshore spread.  
- **C‑COI**: `proxy_pv_base`, `proxy_pv_local`, `embedded_spot_base`, `funding_base`.  
- **A‑RE**: `re_adj_base`, `re_adj_local` — revenue adjustment.  

**Validation:**
```sql
-- pseudo
if any required amount key in rule.lines.amount is missing:
  fail "missing_amount_key"
```

### 4.4 Journal Line Expansion
For each line template in `gl_rules.lines`:
1. Resolve `amount` by key (set either `dr_amt` or `cr_amt`).  
2. Set `ledger`, `account_code` (must exist in `gl_coa`).  
3. Set `accounting_date`, `period_id`, `base_ccy`, `txn_ccy`, `fx_rate`.  
4. Merge `segments` (rule default + payload overrides).  
5. Write to `gl_journal_lines` with `export_status='PENDING'`.

**Insertion template:**
```sql
insert into gl_journal_lines
(journal_id, line_no, ledger, accounting_date, period_id,
 account_code, dr_amt, cr_amt, base_ccy, txn_ccy, fx_rate,
 segments, source_refs, post_status, export_status)
values (...);
```

### 4.5 Multi‑Ledger Fan‑Out
- A single rule can include multiple ledgers in `lines`.  
- Posting engine creates one row per **(journal, ledger, line)**.  
- `journal_id` is commonly `event_id` (or `{event_id}-{ledger}` if you want strict uniqueness per ledger).

---

## 5. Worked Examples

### 5.1 A‑COI (Matched) – HKD example
**Context:** 10M HKD; historical vs current rate causes 150k SGD impact (`diff_base`).  
**Rule hit:** scope `{event_type:"Initiation", posting_model:"A-COI"}`  
**Lines produced:**
- IFRS DR 15001000 150,000; IFRS CR 21001000 150,000  
- LOCAL DR 15001000 145,000; LOCAL CR 21001000 145,000

**Posting (illustrative):**
```sql
-- journal_id can be the event_id
insert into gl_journal_lines
(journal_id, line_no, ledger, accounting_date, period_id,
 account_code, dr_amt, cr_amt, base_ccy, txn_ccy, fx_rate,
 segments, source_refs, post_status, export_status)
values
('EVT_HKD_0001', 1, 'IFRS', date '2025-09-11', '2025-09','15001000',150000,0,'SGD','HKD',null,'{"pc":"TMU"}','{"event_id":"EVT_HKD_0001","gl_package_id":"PKG-..."}','POSTED','PENDING'),
('EVT_HKD_0001', 2, 'IFRS', date '2025-09-11', '2025-09','21001000',0,150000,'SGD','HKD',null,'{"pc":"TMU"}','{"event_id":"EVT_HKD_0001"}','POSTED','PENDING'),
('EVT_HKD_0001', 3, 'LOCAL',date '2025-09-11', '2025-09','15001000',145000,0,'SGD','HKD',null,'{"pc":"TMU"}','{"event_id":"EVT_HKD_0001"}','POSTED','PENDING'),
('EVT_HKD_0001', 4, 'LOCAL',date '2025-09-11', '2025-09','21001000',0,145000,'SGD','HKD',null,'{"pc":"TMU"}','{"event_id":"EVT_HKD_0001"}','POSTED','PENDING');
```

### 5.2 B‑COI (CNY Mismatched) – Spread example
- Amount keys: `spread_base` / `spread_base_local`  
- Accounts: 15001100 vs 21001100  
- Same DR/CR pattern as A‑COI but amounts derived from onshore/offshore rate differential.

### 5.3 C‑COI (Proxy via NDF)
- Amount keys: `proxy_pv_*`, `embedded_spot_*`, `funding_*`  
- Multiple IFRS legs (PV, embedded spot, funding) + LOCAL PV lines.

### 5.4 A‑RE (Revenue Matched)
- Amount keys: `re_adj_base` / `re_adj_local`  
- Reserve vs Capital posting as per rule.

> **Note:** Extend the same pattern for Rollover, Termination, Early_Termination with additional rules (new scopes & amounts: unwind PV, recycle reserves, recognize P&L, etc.).

---

## 6. Validations & Controls

### 6.1 Pre‑Posting Validations
- Selector readiness: event exists in `v_stage2_ready_stage3`
- Rule availability: at least one `gl_rules` row matches
- Amount keys presence for chosen rule
- COA check: `account_code` exists & `active_flag=true`
- Period open: `gl_periods.is_open` for `period_id`

### 6.2 Posting Integrity
- One‑side‑positive DR/CR check
- Balanced journal (sum DR = sum CR per (journal_id, ledger))
- Source traceability (`source_refs` must include `event_id` at minimum)

### 6.3 Post‑Posting Updates
- `hedge_business_events.stage_3_status = 'Completed'`
- `last_stage_3_update = now()`
- `audit_trail` entry with action `POSTED`

---

## 7. Error Handling & Retry

### 7.1 Error Classes
- `NO_RULE_MATCH`
- `MISSING_AMOUNT_KEY`
- `ACCOUNT_NOT_FOUND`
- `PERIOD_CLOSED`
- `INSERT_FAILED` (constraint, FK, etc.)

### 7.2 Event Feedback (HBE fields)
- `stage_3_status` → `Failed`
- `stage_3_error_code` / `stage_3_error_msg`
- `stage_3_attempts += 1`

### 7.3 Retry Policy
- Max attempts configurable (default 3).  
- On retry, re‑evaluate rule (versioning via `effective_from/to`).  
- Auto‑unblock if period becomes open or rules are fixed.

**Ops SQL:**
```sql
update hedge_business_events
set stage_3_status='Pending', stage_3_error_code=null, stage_3_error_msg=null
where event_id in (select event_id from hedge_business_events where stage_3_status='Failed');
```

---

## 8. Dify Agent Integration (Optional)

### 8.1 Contract (service call, no direct table writes)
- Input: `event_id`
- Service does: select → rule match → amount compute → insert lines → update status
- Output: `journal_id`, count(lines), any warnings

### 8.2 Guardrails
- Agent must never write directly to `gl_journal_lines` without service validation.
- If you introduce a queue later, use a stored procedure (idempotent) to enqueue.

---

## 9. Ops Runbook

### 9.1 Daily
- Verify selector non‑empty:
  ```sql
  select count(*) from v_stage2_ready_stage3;
  ```
- Check failed events:
  ```sql
  select event_id, stage_3_error_code, stage_3_error_msg
  from hedge_business_events
  where stage_3_status='Failed';
  ```
- Export handoff:
  ```sql
  select * from v_gl_export_ready order by accounting_date, ledger, journal_id;
  ```

### 9.2 Period Close
- Close old periods:
  ```sql
  update gl_periods set is_open=false where end_date < date_trunc('month', now())::date;
  ```
- Open new period seeds (see §2.3).

### 9.3 Audits
- Reproduce postings for an event:
  ```sql
  select * from gl_journal_lines where source_refs->>'event_id' = '<E>';
  ```
- Rule in force on date:
  ```sql
  select * from gl_rules
  where enabled = true
    and (effective_from is null or effective_from <= current_date)
    and (effective_to   is null or effective_to   >= current_date);
  ```

---

## 10. Troubleshooting

### Symptom: Selector empty
- Check HBE: `stage_2_status='Completed' AND event_status='Booked'`
- Check expected vs acked counts
- Ensure `gl_package_id` is present

### Symptom: `PERIOD_CLOSED`
- Confirm `period_id` and `gl_periods.is_open=true`

### Symptom: `NO_RULE_MATCH`
- Inspect `assigned_booking_model`, `event_type`, `currency_type`, `nav_type`
- Verify `gl_rules.scope` alignment and `priority`

### Symptom: Unbalanced journal
- Ensure all rule lines have amounts & correct DR/CR orientation

---

## 11. Roadmap / Extensions
- Maker/Checker batches with approvals
- Multi‑GAAP ledger mapping (`gl_ledger_map`)
- Accruals & reversals (daily vs monthly flags in rules)
- Automated rollback tool for partial postings
- Stage‑4 export adapters (SAP/Oracle/Workday)

---

## 12. Appendix – Quick Start Seed Pack

### 12.1 COA / Rules / Periods
Use the SQL in §2.1, §2.2, §2.3 to seed minimum viable data.

### 12.2 Minimal Smoke Event (if needed)
*(Only if you don’t yet have Stage‑2 outputs in dev)*
```sql
-- Insert or ensure an instruction compatible with your checks
insert into hedge_instructions (instruction_id, msg_uid, instruction_type, instruction_date,
  exposure_currency, hedge_amount_order, hedge_method, hedging_instrument_hint,
  value_date, instruction_status, created_by, created_date)
values ('INS_SMK3','MSG_SMK3','I', current_date,
  'HKD', 10000000, 'Matched', 'FXFWD',
  current_date, 'Approved', 'seed', now())
on conflict (instruction_id) do nothing;

-- Insert HBE row that simulates Stage‑2 completion (bypass for smoke only)
insert into hedge_business_events (
  event_id, instruction_id, entity_id, business_event_type, nav_type, currency_type,
  hedging_instrument, accounting_method, notional_amount, trade_date, value_date,
  event_status, gl_posting_status, stage_2_status, stage_2_completion_time,
  assigned_booking_model, gl_package_id
) values (
  'EVT_SMK3','INS_SMK3','ENT001','Initiation','COI','HKD',
  'FXFWD','A-COI',10000000,current_date,current_date,
  'Booked','Pending','Completed', now(),
  'A-COI','PKG-SMOKE-3'
) on conflict (event_id) do nothing;
```

### 12.3 Manual Post (demo only)
```sql
-- Assume diff_base = 150000; diff_base_local = 145000
insert into gl_journal_lines
(journal_id, line_no, ledger, accounting_date, period_id,
 account_code, dr_amt, cr_amt, base_ccy, txn_ccy, fx_rate,
 segments, source_refs, post_status, export_status)
values
('EVT_SMK3', 1, 'IFRS', current_date, to_char(current_date,'YYYY-MM'),
 '15001000',150000,0,'SGD','HKD',null,'{"pc":"TMU"}','{"event_id":"EVT_SMK3","gl_package_id":"PKG-SMOKE-3"}','POSTED','PENDING'),
('EVT_SMK3', 2, 'IFRS', current_date, to_char(current_date,'YYYY-MM'),
 '21001000',0,150000,'SGD','HKD',null,'{"pc":"TMU"}','{"event_id":"EVT_SMK3"}','POSTED','PENDING'),
('EVT_SMK3', 3, 'LOCAL',current_date, to_char(current_date,'YYYY-MM'),
 '15001000',145000,0,'SGD','HKD',null,'{"pc":"TMU"}','{"event_id":"EVT_SMK3"}','POSTED','PENDING'),
('EVT_SMK3', 4, 'LOCAL',current_date, to_char(current_date,'YYYY-MM'),
 '21001000',0,145000,'SGD','HKD',null,'{"pc":"TMU"}','{"event_id":"EVT_SMK3"}','POSTED','PENDING');
```

---

**End of hawk‑3.md**
