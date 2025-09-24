# HAWK-REF: Full Reference Codes, Configurations & Onboarding Library

## 🎯 Purpose

The **HAWK-REF** document is the **complete reference library** of the HAWK ecosystem.  
It consolidates **all configuration tables, BE Codes, onboarding guides, GL maps, schema references, portfolio definitions, error codes, and troubleshooting materials**.  

Together with **HAWK-MASTER**, this forms the backbone of the documentation:  
- **MASTER = Lifecycle Blueprint**  
- **REF = Configuration & Codes Library**  

---

## 📑 BE Config Onboarding (GLGEN Process)

Reference: [Onboarding to GL GEN](Onboarding%20to%20GL%20GEN_%20IPE1_BE_Config%20268d65bd558d80d3adcce06a44f5b950.md)  
Reference: [User Guide](User%20Guide%20268d65bd558d8089a0dad98fe131f4ca.md)

**Workflow:**  
1. **Maker** creates or uploads new BE Config via template.  
2. **Validation** checks → errors highlighted before submission.  
3. **Checker** reviews configs → approve, reject, or rework.  
4. Once approved → Config becomes **Active** and available to GLGEN.  

**Parameters Maintained:**  
- Country, System, BE Code, Description, Product Code, Channel  
- Event Type (DR/CR), Ledger, Business Unit, Profit Center, Affiliate  
- FX Flag, Resident, GST, Chartfield2 (Customer Owner)  
- Narrations (1–7)  
- COA Conversion flag (7.5 → 8.4 mappings)  

---

## 🗂️ BE Codes (Complete Samples)

Reference: [BE Codes Sample](BE%20Codes%20Sample%20268d65bd558d80d2ba6fd3d0fa626e1f.md)

### Hedge Inception – COI (Capital/Others Investment)

| BE Code | Event | Currency | GL Account | Narrative |  
|---------|-------|----------|------------|-----------|  
| SG_HAWK_DR_UHDCOIINCEP_TMU | Inception DR | HKD/AUD/EUR | 21001000 | COI Inception |  
| SG_HAWK_CR_UHDCOICNYINCEP_TMU | Inception CR | CNY | 21001100 | COI Inception – CNY |  
| SG_HAWK_DR_UHDCOIPROXY_TMU | Inception DR | KRW/TWD | 21001300 | COI Inception – Proxy |  

### Hedge Inception – RE (Revenue Earnings)

| BE Code | Event | Currency | GL Account | Narrative |  
|---------|-------|----------|------------|-----------|  
| SG_HAWK_DR_UHDREINCEP_TMU | Inception DR | HKD/AUD/EUR | 21001000 | RE Inception |  
| SG_HAWK_CR_UHDRECNYINCEP_TMU | Inception CR | CNY | 21001100 | RE Inception – CNY |  
| SG_HAWK_DR_UHDREPROXY_TMU | Inception DR | KRW/TWD | 21001300 | RE Inception – Proxy |  

### Hedge Lifecycle – Other BE Codes

| BE Code | Description | GL Account | Narrative |  
|---------|-------------|------------|-----------|  
| SG_HAWK_DR_FXPLTOCFHRESERVEFCTRFXGAIN | Reclass FXPL to CFH | 33231008 | To reclass swap pt to reserves |  
| SG_HAWK_CR_HEDGEINCFXDIFFGAIN_BR | Hedge Inception Diff FX Gain | 20183000 | Reclass FX Invst cost |  

*(Full mapping available in BE Codes Sample file)*  

---

## 🛠️ GL Maps (Accounts, Narratives, Affiliates, Profit Centers)

**Accounts & Narratives (Stage 3 examples)**【42†source】:  

| Account | Usage | Example Narrative |  
|---------|-------|-------------------|  
| 15001000 | Rate Differential (BS3) | "COI Hedge Inception | HKD | 10,000,000 | SGD 150,000 differential" |  
| 21001000 | Investment Tracking (COI) | "COI Inception" |  
| 21001100 | CNY Investment Account | "COI CNY Inception" |  
| 21001300 | Proxy Investment Account | "COI Proxy Inception" |  
| 33201001 | CFH Reserve | "To reclass hedge reserve" |  
| 55401015 | FX P&L | "FX Gain/Loss Posting" |  

**Profit Center & Affiliates:**  
- PC Codes: `99001`, `99002` (mapped via BE Config)  
- Affiliate Codes: derived from entity master (branch, subsidiary, associate)  

---

## 🏦 Portfolio Definitions

**Investment Portfolios (COI):**  
- **CO FX** → Corporate FX holding account (external trades)  
- **UHDIC** → Historical investment tracking (blended rates)  
- **INSTC** → Internal trading coordination (FX swaps)  
- **HDGIC** → Final hedge investment portfolio  

**Revenue Portfolios (RE):**  
- **UHDRE** → Revenue tracking at blended rates  
- **INSTC** → Internal trading coordination  
- **HDGRE** → Final revenue hedge portfolio  

**Special Portfolios (Complex models):**  
- **TREASURY_BU** → Used for offshore/onshore spread management (CNY)  
- **FUNDING_DESK** → Proxy currency NDF funding desk (KRW/TWD)  

---

## 🗄️ Schema Reference (Stage 1A → 3)

### Stage 1A – Pre-Utilization【38†source】  
- **hedge_instructions** → Incoming FPM instructions  
- **allocation_engine** → Hedge apportionment & available amounts  
- **entity_master** → Entity hierarchy, CAR flags  
- **threshold_configuration** → USD PB deposit limits  
- **buffer_configuration** → Buffer % rules  

### Stage 1B – Hedge Business Events【39†source】  
- **hedge_business_events** → Hedge lifecycle events (R, T, I)  
- **rollover_configuration** → Rollover rules  
- **termination_configuration** → Termination rules  
- **hedge_relationship_master** → Active hedge registry  

### Stage 2 – Murex Booking【40†source】【41†source】  
- **deal_bookings** → All MX deals booked by HAWK  
- **mx_proxy_hedge_report** → Daily proxy output for GL reclass  
- **murex_book_config** → Book routing & mapping  

### Stage 3 – GL Booking【42†source】  
- **hedge_gl_packages** → GL packages from Stage 2  
- **hedge_gl_entries** → Journal entries (DR/CR)  
- **hedge_gl_entries_detail** → Field-level audit trail  
- **hedge_be_config** → BE code mapping & GL config  
- **hedge_audit_trail** → Audit log of posting events  

---

## 📚 Appendices

### Error Codes (Consolidated)  

- **Stage 1A** → `MISSING_REQUIRED_FIELDS`, `INVALID_FIELD_FORMAT`, `USD_PB_LIMIT_EXCEEDED`  
- **Stage 1B** → `NO_HEDGE_FOUND`, `ROLLOVER_INVALID`, `TERMINATION_FAILED`  
- **Stage 2** → `MX_BOOKING_ERROR`, `PROXY_RATE_MISSING`, `PORTFOLIO_NOT_ACCESSIBLE`  
- **Stage 3** → `CFG_NOT_ACTIVE`, `GL_TIMEOUT`, `AMOUNT_MISMATCH`, `NARRATIVE_ERROR`  

### Payload Samples  

**Instruction (Stage 1A):**  
```json
{
  "msg_uid": "HAWK001",
  "instruction": "I",
  "exposure_currency": "HKD",
  "hedge_method": "COH",
  "order_id": "ORD123",
  "sub_order_id": "SUB456"
}
```  

**GL Package (Stage 3):**  
```json
{
  "package_id": "PKG001",
  "event_id": "EVT123",
  "model_type": "A-COI",
  "entries": [
    {"seq": 1, "dr_account": "15001000", "cr_account": "21001000", "amount_sgd": 150000}
  ]
}
```  

### Troubleshooting Table  

| Issue | Stage | Resolution |  
|-------|-------|------------|  
| Missing BE Config | 3 | Check BE Code active in SGen |  
| Allocation mismatch | 1A/1B | Validate buffer & waterfall configs |  
| Proxy booking fail | 2 | Ensure NDF rate & funding available |  
| GL timeout | 3 | Retry post, escalate if >3 retries |  

---

## ✅ Conclusion

The **HAWK-REF** is the **definitive configuration reference** for the HAWK platform.  
It ensures every hedge lifecycle event maps to correct **GL entries, accounts, and narratives** while maintaining full traceability across Supabase, Dify, Murex, and GLGEN.  

With **HAWK-MASTER (blueprint)** + **HAWK-REF (reference library)**, the documentation set is complete.  
