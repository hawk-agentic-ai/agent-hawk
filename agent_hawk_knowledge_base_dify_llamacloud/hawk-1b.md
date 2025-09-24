# 🦅 HAWK Stage 1B – Allocation & Business Event Processing

> **Stage Scope**: Convert approved **Stage 1A** utilization outcomes and/or direct instructions into **entity‑level allocations** and **hedge business events (HBEs)** that are ready for execution in **Stage 2 (MX Booking)**.  
> **Audience**: Dify Agents, Backend Engineers, Ops Controllers, Auditors.

---

## 1) Overview & Stage Boundaries

**What Stage 1B does**  
- Classifies the incoming instruction into a concrete **Business Event Type** (Inception for existing hedge, Rollover, Termination, etc.).  
- **Allocates** the requested hedge notionals across eligible entities/jurisdictions using configured **waterfalls, buffers, and CAR constraints**.  
- Emits **hedge_business_events** rows with full lineage, status, and model hints for **Stage 2**.  

**Boundaries**  
```json
{
  "input":  "Instruction or Stage 1A pass/partial output",
  "process": "Classify event → Compute capacity → Allocate across entities → Persist HBEs",
  "output": "hedge_business_events[*] = Approved/Pending for Stage 2, with entity-level amounts and metadata",
  "does_not_do": ["Book deals (that is Stage 2)", "GL posting (Stage 3)"]
}
```

**Links**  
- Next: **[Stage 2 – Hedge Inception](hawk-2.md)**  
- Then: **[Stage 3 – GL Booking](hawk-3.md)**  
- Shared glossary & rules: **[hawk-master.md](hawk-master.md)**  
- Config maps (BE codes, GL maps, schemas): **[hawk-ref.md](hawk-ref.md)**

---

## 2) Entry Conditions & Routing

### 2.1 Instruction Types & Routing (Decision Table)

| Instruction | Scenario Hint | Route | Notes |
|---|---|---|---|
| `U` (Utilization) | New hedge feasibility | Usually 1A → if booking required, continue in 1B | 1A pass/partial flows into 1B allocation |
| `I` (Inception) | **Existing hedge** creation/expansion | 1B | For “new hedge” *first‑time* inception, 1A → 1B |
| `R` (Rollover) | Extend/replace maturing hedge | 1B | Re-allocate based on latest capacity & rules |
| `T` (Termination) | Close (partial/full) | 1B | Reclaims capacity and emits close HBEs |

**New vs Existing Hedge Detection**
```python
def is_new_hedge(instruction) -> bool:
    # Treat as "new" if no prior HBE exists for (entity_scope, exposure_currency, hedge_method) in an open lifecycle
    return not hbe_exists_open(
        entity_scope=instruction.entity_scope, 
        currency=instruction.exposure_currency, 
        hedge_method=instruction.hedge_method
    )
```
- `I` with `is_new_hedge == True` → 1A (pre‑util) then 1B
- Otherwise, goes straight to 1B

---

## 3) Data Model & Key Tables

### 3.1 Operational Tables
| Table | Purpose | Notable Fields |
|---|---|---|
| `hedge_instructions` | Raw instructions + orchestration state | `msg_uid`, `instruction_type`, `entity_scope`, `exposure_currency`, `hedge_amount_order`, `check_status` |
| `allocation_engine` | Per-entity capacity and allocation results | `allocation_id`, `entity_id`, `available_amount_for_hedging`, `allocated_amount`, `sequence` |
| `hedge_business_events` | The canonical events emitted to Stage 2 | `event_id`, `instruction_id`, `entity_id`, `business_event_type`, `nav_type`, `hedging_instrument`, `event_status`, `assigned_booking_model`, `stage_2_status` |
| `position_nav_master` | Positions/NAV per entity/currency | `entity_id`, `currency_code`, `sfx_position`, `nav_amount`, `hedged_position` |
| `audit_trail` | Actions, timestamps, actors | `trace_id`, `action`, `message`, `created_at`, `actor` |
| `error_log` | Data/business/system errors | `trace_id`, `error_code`, `error_detail`, `severity` |

### 3.2 Configuration Tables
| Table | Purpose |
|---|---|
| `waterfall_logic_configuration` | Allocation ordering/priorities (entity types, tags, weights) |
| `buffer_configuration` | Buffer % by entity/currency |
| `threshold_configuration` | Global/desk thresholds (e.g., USD PB deposit) |
| `currency_configuration` | Supported currencies, flags (matched/mismatched/proxy), min lot size |
| `hedging_framework` | Allowed hedge method(s) per entity/currency (e.g., COH/MT) |
| `instruction_event_config` | Maps instruction + context → BE code candidates/model hints |

---

## 4) Event Classification (1B)

### 4.1 Event Types
- **Inception (Existing)** – create/expand hedge where lifecycle already exists (e.g., same entity/currency/method).  
- **Rollover** – replace maturing exposures (close‑open pattern).  
- **Termination** – reduce/close existing exposures (partial/full).  

### 4.2 Classifier (Pseudocode)
```python
def classify_business_event(instr) -> str:
    if instr.instruction_type == 'R':
        return 'ROLLOVER'
    if instr.instruction_type == 'T':
        return 'TERMINATION'
    # instruction_type == 'I' (inception)
    return 'INCEPTION_EXISTING' if not is_new_hedge(instr) else 'INCEPTION_NEW'
```

### 4.3 NAV Type & Instrument Hints
- `nav_type`: `COI` (capital/others investment) vs `RE` (revenue/earnings) per `hedging_framework`
- `instrument`: `FX_SWAP` / `NDF` (proxy flows) per `currency_configuration`

---

## 5) Allocation Engine

### 5.1 Capacity Calculation
Uses the **Stage 1A base** per-entity formula; 1B re-runs it with current snapshots to compute *allocable* capacity:
```python
def capacity_available(entity, currency) -> float:
    sfx_to_close = entity.sfx_position - entity.car_distribution
    return sfx_to_close + entity.manual_overlay - entity.buffer_amount - entity.hedged_position
```

### 5.2 Waterfall Ordering
- Sort eligible entities with `waterfall_logic_configuration` (e.g., priority by **entity_type→tag→weight**; tie‑break by **largest unhedged** then **oldest exposure**).

```sql
-- Example: get ordered entity candidates for a currency
SELECT e.entity_id, e.entity_type, cap.available_amount_for_hedging, wf.rank_weight
FROM entity_master e
JOIN allocation_engine cap ON cap.entity_id = e.entity_id
JOIN waterfall_logic_configuration wf ON wf.entity_type = e.entity_type
WHERE cap.currency_code = :ccy AND cap.available_amount_for_hedging > 0
ORDER BY wf.rank_weight DESC, cap.available_amount_for_hedging DESC;
```

### 5.3 Allocation Loop (Rounding & Lots)
```python
def allocate(request_amount, candidates, min_lot):
    allocated = []
    remaining = request_amount
    for c in candidates:
        take = min(c.available, remaining)
        # round to min lot
        take = (take // min_lot) * min_lot
        if take > 0:
            allocated.append((c.entity_id, take))
            remaining -= take
        if remaining <= 0:
            break
    return allocated, remaining
```

### 5.4 Partial/Residual Logic
- If **remaining > 0** after loop → **Partial** outcome.  
- Optionally **back‑fill** small residuals to the **top entity** if policy allows (toggle via `system_configuration` flag).

---

## 6) Persisting HBEs & Stage‑2 Readiness

### 6.1 Create HBEs
```sql
INSERT INTO hedge_business_events (
  event_id, instruction_id, business_event_type, nav_type, hedging_instrument,
  entity_id, exposure_currency, notional_amount, event_status, stage_2_status,
  assigned_booking_model, portfolio_routing, created_date
)
VALUES (
  :event_id, :instruction_id, :event_type, :nav_type, :instrument,
  :entity_id, :ccy, :allocated_amount, 'Approved', 'Pending',
  NULL, NULL, CURRENT_TIMESTAMP
);
```

### 6.2 Mark Instruction
```sql
UPDATE hedge_instructions
SET check_status = CASE
    WHEN :remaining = 0 THEN 'Allocated_Pass'
    WHEN :remaining < :requested THEN 'Allocated_Partial'
    ELSE 'Allocated_Fail'
  END,
  allocated_amount = :requested - :remaining,
  not_allocated_amount = :remaining,
  updated_at = CURRENT_TIMESTAMP
WHERE msg_uid = :msg_uid;
```

### 6.3 Idempotency & Re‑runs
- **Idempotency key** = `msg_uid` (and optionally a `source_id`).  
- Re‑running the same `msg_uid` → **no duplicate HBEs**; create a **superseding version** only if **input hash differs**.

```sql
-- Guard against duplicates
SELECT 1 FROM hedge_business_events WHERE instruction_id = :instruction_id LIMIT 1;
```

---

## 7) Validation Matrix (Field‑Level)

| Field | `U` | `I` | `R` | `T` | Rules |
|---|:--:|:--:|:--:|:--:|---|
| `msg_uid` | ✔ | ✔ | ✔ | ✔ | Alphanumeric ≤ 50; idempotent key |
| `instruction_type` | ✔ | ✔ | ✔ | ✔ | One of [U,I,R,T] |
| `entity_scope` | ✔ | ✔ | ✔ | ✔ | Branch/Subsidiary/Associate or group |
| `exposure_currency` | ✔ | ✔ | ✔ | ✔ | ISO‑3; must exist in `currency_configuration` |
| `hedge_method` | – | ✔ | ✔ | ✔ | Allowed by `hedging_framework` |
| `hedge_amount_order` | ✔ | ✔ | ✔ | ✔ | > 0; respects `min_lot_size` |
| `value_date` | – | ✔ | ✔ | ✔ | ≥ trade date; holidays checked |
| `rollover_ref` | – | – | ✔ | – | Must match open HBE(s) |
| `terminate_ref` | – | – | – | ✔ | Must match open HBE(s) |

**Cross‑checks**
- Currency **supported** and **enabled**.  
- Entity has **buffer** & **waterfall** configs.  
- **Thresholds** (e.g., USD PB) recalculated post‑allocation.  
- **Rates snapshot** is not stale (> policy window).

---

## 8) Error Handling & Recovery

### 8.1 Error Classes
- **SYSTEM**: database connectivity, config service down, rate service down.  
- **DATA**: missing/invalid fields, unknown entity, unsupported currency.  
- **BUSINESS**: capacity=0, thresholds exceeded, references not open (rollover/termination).

### 8.2 Response Shapes
```json
// PASS
{"status":"Pass","allocated_amount":10000000,"not_allocated_amount":0,"hbes_created":3,"can_proceed":true}

// PARTIAL
{"status":"Partial","allocated_amount":7000000,"not_allocated_amount":3000000,"hbes_created":2,"can_proceed":true}

// FAIL
{"status":"Fail","reason":"USD PB threshold exceeded","allocated_amount":0,"not_allocated_amount":10000000,"can_proceed":false}
```

### 8.3 Retry & Hold Queues
- **Auto‑retry** for SYSTEM up to N times with backoff.  
- **On‑Hold** for BUSINESS/DATA with explicit reason; operator override supported.  

---

## 9) Handoff to Stage 2 (Contract)

### 9.1 Selection Query (Stage 2 Intake)
```sql
SELECT hbe.event_id, hbe.business_event_type, hbe.entity_id,
       hbe.exposure_currency, hbe.nav_type, hbe.hedging_instrument,
       hbe.notional_amount
FROM hedge_business_events hbe
WHERE hbe.event_status = 'Approved'
  AND hbe.stage_2_status = 'Pending'
ORDER BY hbe.created_date ASC;
```

### 9.2 Required Fields for Stage 2
```json
{
  "event_id": "EVT20250911-0007",
  "business_event_type": "ROLLOVER|TERMINATION|INCEPTION_*",
  "nav_type": "COI|RE",
  "exposure_currency": "HKD|AUD|EUR|CNY|KRW|TWD",
  "hedging_instrument": "FX_SWAP|NDF",
  "notional_amount": 10000000,
  "entity_id": "SUBS-001"
}
```

---

## 10) Examples

### 10.1 Inception (Existing) – Request
```json
{
  "msg_uid": "HAWK-1B-1001",
  "instruction_type": "I",
  "entity_scope": "GROUP-APAC",
  "exposure_currency": "HKD",
  "hedge_method": "COH",
  "hedge_amount_order": 10000000
}
```

**Result (Simplified)**
```json
{
  "status": "Pass",
  "allocated_amount": 10000000,
  "not_allocated_amount": 0,
  "hbes_created": 3,
  "hbes": [
    {"event_id":"EVT-001","entity_id":"HK-SUB1","ccy":"HKD","amount":6000000,"event_type":"INCEPTION_EXISTING"},
    {"event_id":"EVT-002","entity_id":"HK-SUB2","ccy":"HKD","amount":3000000,"event_type":"INCEPTION_EXISTING"},
    {"event_id":"EVT-003","entity_id":"HK-BRANCH","ccy":"HKD","amount":1000000,"event_type":"INCEPTION_EXISTING"}
  ]
}
```

### 10.2 Rollover – Request
```json
{
  "msg_uid": "HAWK-1B-2001",
  "instruction_type": "R",
  "entity_scope": "GROUP-APAC",
  "exposure_currency": "AUD",
  "hedge_method": "COH",
  "hedge_amount_order": 5000000,
  "rollover_ref": ["EVT-OLD-11","EVT-OLD-12"]
}
```

**Result (Partial)**
```json
{"status":"Partial","allocated_amount":4000000,"not_allocated_amount":1000000,"hbes_created":2}
```

### 10.3 Termination – Request
```json
{
  "msg_uid": "HAWK-1B-3001",
  "instruction_type": "T",
  "entity_scope": "GROUP-APAC",
  "exposure_currency": "CNY",
  "hedge_method": "COH",
  "hedge_amount_order": 12000000,
  "terminate_ref": ["EVT-OPEN-101","EVT-OPEN-102"]
}
```

**Result (Fail – References Closed)**
```json
{
  "status":"Fail",
  "reason":"Reference EVT-OPEN-101 not in open state",
  "allocated_amount":0,
  "not_allocated_amount":12000000,
  "can_proceed":false
}
```

---

## 11) APIs (for Dify / Orchestration)

- `POST /stage1b/validate` → returns validation issues/warnings.  
- `POST /stage1b/allocate` → executes capacity + waterfall + persist HBEs.  
- `GET  /stage1b/status?msg_uid=` → orchestration status, exception queue ref.  

**Payload Schema (excerpt)**
```json
{
  "msg_uid": "string (<=50)",
  "instruction_type": "U|I|R|T",
  "entity_scope": "string",
  "exposure_currency": "ISO-3",
  "hedge_method": "COH|MT",
  "hedge_amount_order": "number",
  "value_date": "YYYY-MM-DD",
  "rollover_ref": ["EVT-..."],
  "terminate_ref": ["EVT-..."]
}
```

---

## 12) Audit, Controls & KPIs

- **Traceability**: `trace_id` on all actions, link `instruction_id` → `event_id`(*)  
- **Maker/Checker (Optional)**: 4‑eyes approval before HBE release.  
- **KPIs**: time‑to‑allocate, partial ratio, exception rate, top capacity constraints.  
- **Replayability**: deterministic allocation with config snapshot hashes.

---

## 13) Appendix – SQL Helpers

### 13.1 Snapshot Rates/Configs
```sql
SELECT * FROM currency_configuration WHERE currency_code = :ccy AND status = 'Active';
SELECT * FROM buffer_configuration WHERE entity_id IN (:entities) AND currency_code = :ccy AND status='Active';
SELECT * FROM waterfall_logic_configuration WHERE status='Active';
```

### 13.2 Remaining Capacity by Entity
```sql
SELECT e.entity_id,
       (pnm.sfx_position - pnm.car_distribution
        + COALESCE(pnm.manual_overlay,0)
        - COALESCE(pnm.buffer_amount,0)
        - COALESCE(pnm.hedged_position,0)) AS available_amount_for_hedging
FROM entity_master e
JOIN position_nav_master pnm ON pnm.entity_id = e.entity_id AND pnm.currency_code = :ccy;
```

### 13.3 Final Allocation Result
```sql
SELECT allocation_id, entity_id, currency_code, allocated_amount, sequence
FROM allocation_engine
WHERE msg_uid = :msg_uid
ORDER BY sequence ASC;
```

---

## 14) Cross‑Refs
- **[hawk-1a.md](hawk-1a.md)** – Pre‑Utilization (formulas, thresholds, buffers)  
- **[hawk-2.md](hawk-2.md)** – Stage 2 booking contract and model assignment  
- **[hawk-3.md](hawk-3.md)** – GL mapping & narratives (after Stage 2)  
- **[hawk-ref.md](hawk-ref.md)** – BE codes, portfolios, schema dictionary  
- **[hawk-master.md](hawk-master.md)** – Lifecycle, glossary, diagrams
