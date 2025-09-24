# HAWK-MASTER: End-to-End Lifecycle Blueprint

## 🎯 Purpose

The **HAWK-MASTER** document serves as the **central playbook** for the HAWK hedge accounting engine.  
It consolidates all **universal concepts, lifecycle logic, and integration rules** across **Stage 1A → Stage 3**, with clear orchestration notes for Supabase, Dify, Murex, and GLGEN.

---

## 🔄 Lifecycle Summary: Stage 1A → 3

### Stage 1A – Pre-Utilization Check
Reference: [HAWK Stage 1A Documentation](HAWK%20Stage%201A%20Complete%20End-to-End%20Flow%20Documentati%20257d65bd558d806fa933ffcb6ae82317.md)

Definition: “Pre-trade utilization check – applicable for new hedges only.”

- Formula: `Unhedged = SFX Position – CAR + Overlay – (SFX × Buffer%) – Hedged Position`
- Outputs: PASS / PARTIAL / FAIL utilization result

---

### Stage 1B – Hedge Business Event Processing
Reference: [HAWK Stage 1B Documentation](HAWK%20Stage%201B%20Complete%20End-to-End%20Flow%20Documentati%2025ad65bd558d80218fe7c5aa66cd219e.md)

Definition: “Receives hedge business events – applicable for all hedge lifecycle events.”

- Handles: Rollover (R), Termination (T), Existing Inception (I)
- Formula: `Outstanding = Original Hedge – ∑(Terminations) – ∑(Partial Rollovers)`

---

### Stage 2 – Hedge Inception / MX Booking
Reference: [HAWK Stage 2 Documentation](HAWK%20Stage%202%20Hedge%20Inception%20Complete%20Guide%2025ad65bd558d8089979de2e8606ba5e3.md)

Definition: “Converts approved hedge events into actual Murex (MX) bookings.”

- Uses booking models (A-COI, B-COI, C-COI; A-RE, B-RE, C-RE)
- Portfolio flow: External → CO FX → UHDIC → INSTC → HDGIC

---

### Stage 3 – GL Booking
Reference: [HAWK Stage 3 Documentation](Stage%203%20GL%20Booking%20Complete%20Guide%2026bd65bd558d81deb2b3fbd6e60e1d6d.md)

Definition: “Transforms Stage 2 GL package into auditable ledger entries.”

- Consumes GL package → maps to BE Config via SGen
- Constructs debit/credit lines, narratives, profit center, affiliate details

---

## ⚖️ Shared Rules & Principles

- **CAR Hedge Lens:** Hedge only beyond CAR amount
- **Buffer Logic:** Apply buffer% (default 5%) on SFX
- **Hedge Accounting:** Prevailing vs Historical → P&L or FCTR
- **Proxy Handling:** Offshore vs Onshore spread and NDF logic

---

## 📊 Quick Reference Tables

### Instruction Routing

| Instruction | Scenario | Stage |
|-------------|----------|-------|
| U | Utilization | 1A |
| I | Inception (New) | 1A |
| I | Inception (Existing) | 1B |
| R | Rollover | 1B |
| T | Termination | 1B |

### Booking Models

| Model | NAV | Currency | Deals | Complexity |
|-------|-----|----------|-------|------------|
| A-COI | COI | Matched (HKD/AUD/EUR) | 6 | ⭐⭐ |
| B-COI | COI | Mismatched (CNY) | 10 | ⭐⭐⭐ |
| C-COI | COI | Proxy (KRW/TWD) | 10 | ⭐⭐⭐⭐ |
| A-RE  | RE  | Matched | 3 | ⭐ |
| B-RE  | RE  | Mismatched | 3 | ⭐⭐ |
| C-RE  | RE  | Proxy | 5 | ⭐⭐⭐ |

---

## 📚 Glossary

- **COI** – Capital/Others Investment  
- **RE** – Revenue Earnings  
- **NAV** – Net Asset Value  
- **BE** – Business Event  
- **MX** – Murex trading system  
- **GLGEN / SGen** – General Ledger Generator  
- **FCTR** – Foreign Currency Translation Reserve  
- **CFH** – Cash Flow Hedge  
- **CAR** – Capital Adequacy Ratio  
- **SFX** – FX Swap position  
- **UHDIC / INSTC / HDGIC** – Internal hedge portfolios  

---

## ✅ Audit & Monitoring

- Supabase: hedge_instructions, allocation_engine, audit_trail  
- Dify: orchestration, routing, validation  
- Murex: deal booking, proxy reports  
- GLGEN: posting, BE Config mapping, audit trail  

---

## 🔍 Conclusion

The **HAWK-MASTER** is the unifying blueprint connecting all stages.  
It provides the **rules, orchestration, and universal decision logic**.  
Stage-specific docs offer the technical detail, but HAWK-MASTER ensures **big-picture clarity**.
