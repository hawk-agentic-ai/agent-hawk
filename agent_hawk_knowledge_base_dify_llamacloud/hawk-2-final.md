# HAWK Stage 2: MX Booking Engine (hawk-2.md)

**Document Scope:** Stage 2 (Hedge Inception Booking in MX) — Complete Coverage  
**Stage Boundaries:** Input = Stage 1B approved hedge business events → Stage 2 deal booking in MX → Stage 3 GL package output  
**Purpose:** Source of truth for automation (Dify agent knowledge base + engineering reference).

---

## 1. 🎯 Overview & Scope

Stage 2 converts **approved hedge business events** (from Stage 1B allocation) into **Murex deal bookings**.  
It ensures consistent booking across portfolios, applies historical vs prevailing rate logic, and prepares a **GL package** for Stage 3.

### Boundaries

```json
{
  "input": "Approved hedge_business_events + allocation_engine outputs",
  "process": "Classify model, book deals, route through portfolios, apply historical vs prevailing rate calculations, prepare proxy/NDF handling",
  "output": "deal_bookings (executed), gl_package_id (handoff to Stage 3), audit trail",
  "does_not_do": ["Final GL postings", "Daily reclassifications", "External reporting"]
}
```

### Entry Preconditions
- `hedge_business_events.stage_2_status = 'Pending'`
- `allocation_engine.finalized = true`
- `currency_configuration.active_flag = true`
- `murex_book_config.active_flag = true`
- Rates available in `currency_rates` for both historical & prevailing
- Murex connectivity via `h_stg_mrx_ext` staging table

---

## 2. 📊 Model Assignment & Decision Matrix

### Classification Logic

```json
{
  "nav_type": ["COI", "RE"],
  "currency_type": ["Matched", "Mismatched", "Proxy"],
  "decision": "Assign one of six booking models"
}
```

### Model Matrix

| Model | NAV | Currency Type | Deals | Complexity | Example |
|-------|-----|---------------|-------|------------|---------|
| A-COI | COI | Matched (HKD, AUD, EUR) | 6 | ⭐⭐ | Direct FX Swap |
| B-COI | COI | Mismatched (CNY) | 10 | ⭐⭐⭐ | Onshore/Offshore split |
| C-COI | COI | Proxy (KRW, TWD) | 10 | ⭐⭐⭐⭐ | NDF + funding |
| A-RE  | RE  | Matched (HKD, AUD, EUR) | 3 | ⭐ | Revenue swap |
| B-RE  | RE  | Mismatched (CNY) | 3 | ⭐⭐ | Offshore execution |
| C-RE  | RE  | Proxy (KRW, TWD) | 5 | ⭐⭐⭐ | NDF revenue hedge |

---

## 3. 🏦 Portfolio Routing

### COI Models

```
External → CO_FX → UHDIC → INSTC → HDGIC
```

### RE Models

```
External → UHDRE → INSTC → HDGRE
```

### Special Portfolios
- **TREASURY_BU**: mismatched CNY differential handling
- **FUNDING_DESK**: proxy/NDF USD funding
- **MBS_BU**: consolidation

---

## 4. 💰 Booking Models (with worked examples)

### 4.1 Model A-COI (Matched: HKD, AUD, EUR)
- Deals: 6
- Logic: Historical vs prevailing rate differential
- Example: 10,000,000 HKD → Hist 0.1600 vs Prev 0.1750 = 150,000 SGD impact

**Deal Sequence**
1. External FX Spot (prevailing)
2. Internal near leg mirror
3. Internal historical leg
4. Internal INSTC swap
5. Transfer out
6. Final hedge in HDGIC

```sql
SELECT blended_historical_rate, prevailing_rate
FROM currency_rates
WHERE currency_pair = 'HKD/SGD'
ORDER BY effective_date DESC LIMIT 1;
```

---

### 4.2 Model B-COI (Mismatched: CNY)
- Deals: 10
- Logic: Offshore execution + onshore internal booking + spread hedge
- Example: 50,000,000 CNY → Offshore 0.1900, Onshore 0.1880, Hist 0.1850 = 100,000 SGD spread

**Deal Highlights**
- Offshore swap legs
- Onshore mirror
- Differential hedges
- INSTC internal swaps
- Final hedge in HDGIC

```sql
SELECT offshore_rate, onshore_rate, (offshore_rate - onshore_rate) AS spread
FROM currency_rate_pairs WHERE base_currency='CNY' AND quote_currency='SGD';
```

---

### 4.3 Model C-COI (Proxy: KRW, TWD)
- Deals: 10
- Logic: Use NDF + USD proxy + LNBR funding
- Example: 12B KRW @ 1250 + USD/SGD 1.35 → 9.6M USD → 12.96M SGD

**Deal Highlights**
- External USD/SGD funding
- Internal NDF KRW/USD
- Embedded spot extraction
- LNBR funding
- Historical adjustment
- Final hedge HDGIC

---

### 4.4 Model A-RE (Matched)
- Deals: 3
- Logic: Close dummy UHDRE (historical), create HDGRE (prevailing)
- Example: 5,000,000 AUD → Hist 0.9200 vs Prev 0.9500 = 150,000 SGD adj

---

### 4.5 Model B-RE (Mismatched: CNY)
- Deals: 3
- Logic: Offshore execution, onshore booking
- Example: Offshore 0.1900 vs Onshore 0.1880

---

### 4.6 Model C-RE (Proxy: KRW/TWD)
- Deals: 5
- Logic: NDF + embedded spot + LNBR funding
- Example: 150M TWD → NDF 31.50 → 4.76M USD

---

## 5. ⚙️ Database Integration & Field Mappings

### Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| hedge_business_events | Event lifecycle | event_id, assigned_booking_model, portfolio_routing, stage_2_status, gl_package_id |
| hedge_instructions | Instruction lineage | instruction_id, msg_uid, instruction_type, hedge_amount_order |
| allocation_engine | Stage 1B apportionment | allocation_id, request_id, entity_id, currency_code, hedge_amount_allocation |
| entity_master | Entity metadata | entity_id, entity_name, murex_comment, murex_issuer |
| currency_configuration | Currency classification | currency_code, currency_type, proxy_currency, hedge_accounting_eligible |
| currency_rates | FX rates | currency_pair, rate_type, rate_value, effective_date |
| currency_rate_pairs | Onshore/Offshore | base_currency, onshore_rate, offshore_rate |
| murex_book_config | Routing | murex_book_code, portfolio, tps_outbound, transformations |
| deal_bookings | Stage 2 execution | deal_booking_id, event_id, deal_sequence, deal_type, portfolio, fx_rate, external_reference, booking_reference |
| mx_proxy_hedge_report | Proxy/NDF detail | event_id, report_date, near_leg_structure, far_leg_structure, lnbr_leg_details |
| h_stg_mrx_ext | Staging payloads | stg_id, event_id, instruction_id, direction, payload, status, ack_at |
| audit_trail | Changes | audit_id, event_id, table_name, field_name, old_value, new_value |
| stage2_error_log | NOKs | error_id, event_id, deal_sequence, error_type, retry_count, resolution_status |
| gl_entries | Stage 3 header | gl_entry_id, event_id, debit_account, credit_account, amount_sgd |
| gl_entries_detail | Stage 3 detail | detail_id, gl_entry_id, account_code, amount |

---

## 6. 🚨 Error Handling & Monitoring

| Error Type | Example | Handling |
|------------|---------|----------|
| Data Missing | No prevailing rate in `currency_rates` | Log to `stage2_error_log`, NOK |
| Config Error | Book code inactive in `murex_book_config` | Escalate Treasury BU |
| System Error | MX timeout via `h_stg_mrx_ext` | Retry 3x, then NOK |
| Business Error | Unsupported model assignment | NOK, manual booking |
| Reconciliation Gap | Expected vs acked mismatch | View `v_stage2_stuck` |

---

## 7. 🔄 Reconciliation to Stage 3

### Reconciler Logic
1. Inbound ACK (`h_stg_mrx_ext.direction='INBOUND' and status='ACK'`) updates `deal_bookings.external_reference` and `booking_reference`.  
2. If all expected deals acked, update `hedge_business_events.stage_2_status='Completed'`, assign `gl_package_id`, flip `event_status='Booked'`.  
3. Stage 3 picks up events from `v_stage2_ready_stage3`.

```sql
CREATE OR REPLACE VIEW v_stage2_ready_stage3 AS
SELECT h.event_id, h.assigned_booking_model, h.gl_package_id, h.stage_2_completion_time
FROM hedge_business_events h
JOIN v_event_expected_deals e USING (event_id)
JOIN v_event_acked_deals a USING (event_id)
WHERE a.acked_deals >= e.expected_deals
  AND h.stage_2_status = 'Completed'
  AND h.event_status = 'Booked';
```

---

## 8. 🧮 Worked Examples (Summary)

- A-COI: 10M HKD → 150K SGD adj
- B-COI: 50M CNY → 100K SGD spread
- C-COI: 12B KRW → 12.96M SGD equiv
- A-RE: 5M AUD → 150K SGD adj
- B-RE: 50M CNY offshore vs onshore diff
- C-RE: 150M TWD → 4.76M USD equiv

---

## 9. ✅ Stage 2 → Stage 3 GL Handoff

At Stage 2 completion, a GL package is produced:

```json
{
  "gl_package_id": "PKG-20250911-HKD-001",
  "event_id": "EVT-HKD-001",
  "model_type": "A-COI",
  "deals": [ { "deal_seq":1, "portfolio":"CO_FX", "fx_rate":0.1750 } ],
  "rates_used": {"historical":0.1600,"prevailing":0.1750},
  "status": "Completed"
}
```

Stage 3 consumes this package, generates `gl_entries` and `gl_entries_detail` using BE-to-GL config mappings.

---

## 10. 📚 Glossary

- **COI**: Capital-Others-Investment  
- **RE**: Revenue-Earnings  
- **UHDIC / UHDRE**: Historical portfolios  
- **HDGIC / HDGRE**: Final hedge portfolios  
- **INSTC**: Internal Swap Coordination portfolio  
- **NDF**: Non-Deliverable Forward  
- **LNBR**: Funding package for proxy models  
- **TREASURY_BU**: Treasury counterparty unit  
- **GL Package**: JSON handoff contract to Stage 3

---

*Generated on 2025-09-11 12:21:44*
