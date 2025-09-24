# 🦅 HAWK Stage 1A – Pre-Utilization Check

## 1. Overview & Scope

**Definition:**  
Stage 1A = **“Pre-trade utilization check – Applicable for New Hedges”**

**Purpose:**  
- Validate feasibility of hedge requests before booking.  
- Prevents invalid or excess hedge instructions from proceeding.  

**Stage Boundaries:**  
- **Input:** Hedge instruction (‘U’ Utilization, ‘I’ Inception – new only).  
- **Output:** Utilization result (Pass/Partial/Fail) or Inception acknowledgment.  

**Stage Links:**  
- Next stage for new hedges → [Stage 1B – Allocation](hawk-1b.md)  
- Eventual booking → [Stage 2 – Hedge Inception](hawk-2.md)  
- Accounting → [Stage 3 – GL Booking](hawk-3.md)  
- Shared glossary/rules → [hawk-master.md](hawk-master.md)  
- BE codes/configs → [hawk-ref.md](hawk-ref.md)  

---

## 2. Entry Conditions & Routing

### Instruction Routing Decision Matrix

| Instruction Type | Scenario | Stage | Rationale |
|------------------|----------|-------|-----------|
| **‘U’ (Utilization)** | All | Stage 1A | Pre-flight feasibility check |
| **‘I’ (Inception)** | New hedge creation | Stage 1A | First-time hedge setup |
| **‘I’ (Inception)** | Existing hedge | Stage 1B | Existing hedge event |
| **‘R’ (Rollover)** | All | Stage 1B | Modification |
| **‘T’ (Termination)** | All | Stage 1B | Closure |

### New Hedge Detection Logic (Python Pseudocode)

```python
def determine_stage_routing(instruction):
    if instruction.instruction_type == 'U':
        return 'STAGE_1A'
    elif instruction.instruction_type == 'I':
        is_new = check_new_hedge_criteria(
            exposure_currency=instruction.exposure_currency,
            entity_scope=instruction.entity_scope,
            hedge_method=instruction.hedge_method
        )
        return 'STAGE_1A' if is_new else 'STAGE_1B'
    else:
        return 'STAGE_1B'
```

---

## 3. Core Objectives & Formula

**Primary Objectives:**  
- Optimize swap execution (aggregate SFX vs entity positions).  
- Respect CAR hedge lens (entity adequacy).  
- Apply hedge accounting rules (reduce MTM of naked swaps).  

**Formula:**

```
Unhedged Position = SFX Position - CAR Amount
                  + Manual Overlay
                  - (SFX Position × Buffer/100)
                  - Hedged Position
```

---

## 4. Database Design

### Core Processing Tables

| Table Name | Purpose | Key Fields |
|------------|---------|------------|
| hedge_instructions | Store incoming instructions | msg_uid, instruction_type, exposure_currency, hedge_amount_order, check_status |
| entity_master | Entity hierarchy | entity_id, entity_type, parent_entity_id |
| position_nav_master | NAVs & SFX positions | entity_id, currency_code, sfx_position, nav_amount |
| allocation_engine | Results & waterfall | allocation_id, entity_id, available_amount_for_hedging |

### Config / Rules Tables

- **threshold_configuration** – USD PB deposit limits  
- **buffer_configuration** – entity-level buffer %  
- **waterfall_logic_configuration** – allocation priority rules  
- **currency_configuration** – currency settings, FX rates  
- **hedging_framework** – framework per entity/currency  

### Audit & Monitoring

- **audit_trail** – full process logs  
- **system_configuration** – runtime params  
- **car_master** – capital adequacy ratios  

---

## 5. Step-by-Step Processing Flow

### Phase 1: Instruction Reception & Setup

```python
def stage1a_main_flow(instruction):
    setup_result = initialize_stage1a_processing(instruction)
    if not setup_result['success']:
        return send_error_response(setup_result['error'])

    validation_result = execute_field_validation(instruction)
    if not validation_result['success']:
        return send_validation_error_response(validation_result)

    preutil_result = execute_pre_utilization_check(instruction)
    return route_based_on_instruction_type(instruction, preutil_result)
```

- Generate **HAWK Trace ID** (TRC{YYYYMMDD}{HHMMSS}{Rand})  
- Insert into `hedge_instructions`  
- Create audit log entry  
- Validate system readiness  

---

### Phase 2: Field Validation

**Validation Steps:**
1. Required fields check  
2. Format validation (patterns, lengths)  
3. Business rules (hedge method allowed?)  
4. Cross-reference checks (entity, framework, buffer)  

**Validation Matrix (Excerpt):**

| Field | Utilization (U) | Inception (I) | Rollover (R) | Termination (T) | Rules |
|-------|-----------------|---------------|--------------|-----------------|-------|
| MSG_UID | ✔ | ✔ | ✔ | ✔ | Alphanumeric, max 50 |
| Instruction | ✔ | ✔ | ✔ | ✔ | One of [U, I, R, T] |
| Exposure_Currency | ✔ | ✔ | ✔ | ✔ | 3-letter ISO |
| Order_ID | – | ✔ | ✔ | ✔ | Required except Utilization |
| Hedge_Method | – | ✔ | ✔ | ✔ | Must be MT or COH |

---

### Phase 3: Pre-Utilization Check

**Available Amount Calculation:**

```python
def calculate_entity_available_amount(sfx_position, car_distribution,
                                      manual_overlay, buffer_amount, hedged_position):
    sfx_to_close = sfx_position - car_distribution
    return sfx_to_close + manual_overlay - buffer_amount - hedged_position
```

- Aggregates across entities  
- Applies buffer config & CAR distribution  
- Adjusts for manual overlay  

**USD PB Threshold Check:**

```python
usd_equivalent = convert_currency_to_usd(hedge_amount, exposure_currency)
total_after = current_usd_hedged + usd_equivalent
if total_after > usd_pb_limit:
    return {"passed": False, "reason": "USD PB threshold exceeded"}
```

---

### Phase 4: Response Generation

```python
def determine_check_status(available_amount, requested_amount, usd_ok, currency):
    if not usd_ok:
        return {"status": "Fail", "reason": "USD PB limit exceeded"}
    if available_amount >= requested_amount:
        return {"status": "Pass", "allocated_amount": requested_amount}
    elif available_amount > 0:
        return {"status": "Partial", "allocated_amount": available_amount}
    else:
        return {"status": "Fail", "reason": "No available amount"}
```

---

## 6. Special Rules

### Multiple Messages Handling

- If multiple `U` or `I` for same currency on same day → process each, but warn after 2nd.  
- Special conversion logic:  
  - **U → I** on same day → convert original utilization to inception.  
  - **I → U** → treat separately.  

---

## 7. Error Handling

- **System errors:** missing configs, MX API unavailable  
- **Data errors:** invalid field values, stale FX rates  
- **Business errors:** USD PB exceeded, allocation = 0  

Responses:  
- **Pass / Partial / Fail** with structured JSON reason codes.  

---

## 8. Examples

### Example Utilization Request

```json
{
  "msg_uid": "HAWK001",
  "instruction": "U",
  "exposure_currency": "HKD",
  "hedge_amount_order": 5000000
}
```

### Example Utilization Response (Pass)

```json
{
  "msg_uid": "HAWK001",
  "status": "Pass",
  "reason": "Sufficient available amount",
  "available_amount": 8000000,
  "allocated_amount": 5000000,
  "not_allocated_amount": 0,
  "can_proceed": true
}
```

### Example Response (Partial)

```json
{
  "msg_uid": "HAWK002",
  "status": "Partial",
  "reason": "Partial hedge available - insufficient capacity",
  "available_amount": 3000000,
  "allocated_amount": 3000000,
  "not_allocated_amount": 2000000,
  "can_proceed": true
}
```

### Example Response (Fail – Threshold Exceeded)

```json
{
  "msg_uid": "HAWK003",
  "status": "Fail",
  "reason": "USD PB Deposit threshold exceeded",
  "allocated_amount": 0,
  "can_proceed": false
}
```

---

## 9. References
- [hawk-1b.md](hawk-1b.md) – Stage 1B Business Events  
- [hawk-2.md](hawk-2.md) – Hedge Inception  
- [hawk-3.md](hawk-3.md) – GL Booking  
- [hawk-ref.md](hawk-ref.md) – BE Codes & Configs  
- [hawk-master.md](hawk-master.md) – Lifecycle & Glossary  
