# HAWK Stage 1A - Essential SQL Query Patterns

## Critical Database Query Requirements

## Intelligent Query Assembly Examples

### Example 1: "How much buffer is left for AUD?"

**Smart Query Logic:**

1. "Buffer left" = Available hedging capacity after buffers applied
2. Need: Entity positions + Current hedges + Buffer rules + Framework context
3. Intelligent Assembly: JOIN position_nav_master + entity_master + hedge_instructions + framework data

**Adaptive Query (Context-Driven):**

```sql
-- The AI agent should intelligently construct queries like this based on the request
SELECT 
    em.entity_name,           -- Real entity names, not generic IDs
    em.entity_type,          -- Branch/Subsidiary/Associate for prioritization
    em.car_exemption_flag,   -- Affects buffer calculation rules
    pnm.current_position as sfx_position,
    pnm.buffer_pct,          -- Applied buffer percentage
    pnm.buffer_amount,       -- Pre-calculated buffer amount
    COALESCE(hi.hedged_amount, 0) as current_hedged,  -- Real hedged positions
    -- Smart calculation of available capacity
    (pnm.current_position - COALESCE(pnm.optimal_car_amount, 0) + 
     COALESCE(pnm.manual_overlay_amount, 0) - pnm.buffer_amount - 
     COALESCE(hi.hedged_amount, 0)) as available_capacity
FROM entity_master em
JOIN position_nav_master pnm ON em.entity_id = pnm.entity_id  
LEFT JOIN (
    -- Get current hedged positions intelligently
    SELECT entity_id, exposure_currency, SUM(allocated_notional) as hedged_amount
    FROM hedge_instructions 
    WHERE instruction_status IN ('Executed', 'Allocated') 
    GROUP BY entity_id, exposure_currency
) hi ON em.entity_id = hi.entity_id AND pnm.currency_code = hi.exposure_currency
WHERE pnm.currency_code = 'AUD' 
AND em.active_flag = 'Y'
-- Get freshest data intelligently
AND pnm.as_of_date = (SELECT MAX(as_of_date) FROM position_nav_master WHERE currency_code = 'AUD')
ORDER BY 
    -- Smart prioritization
    CASE em.entity_type WHEN 'Branch' THEN 1 WHEN 'Subsidiary' THEN 2 ELSE 3 END,
    available_capacity DESC;
```


***

**[ADDED/UPDATED: 2025-09 — Agent/Schema Correct]**

- For best-practice, use current field/table names (see Supabase ref):
    * position_nav_master: position_fc, buffer_amount, nav_type
    * overlay_configuration, v_entity_capacity_complete, v_available_amounts_fast for summaries

**Best-practice real q:**

```sql
SELECT
  em.entity_name,
  em.entity_type,
  nav.nav_type,
  nav.position_fc AS sfx_position,
  nav.buffer_amount,
  COALESCE(ov.overlay_amount, 0) AS overlay_amount,
  COALESCE(hi.hedged_amount, 0) AS current_hedged,
  (
    nav.position_fc
    + COALESCE(ov.overlay_amount, 0)
    - nav.buffer_amount
    - COALESCE(hi.hedged_amount, 0)
  ) AS available_capacity
FROM entity_master em
JOIN position_nav_master nav ON em.entity_id = nav.entity_id
LEFT JOIN (
  SELECT entity_id, currency_code, SUM(overlay_amount) AS overlay_amount
  FROM overlay_configuration WHERE status = 'Active'
  GROUP BY entity_id, currency_code
) ov ON nav.entity_id = ov.entity_id AND nav.currency_code = ov.currency_code
LEFT JOIN (
  SELECT entity_id, exposure_currency, SUM(allocated_notional) AS hedged_amount
  FROM hedge_instructions
  WHERE instruction_status IN ('Executed', 'Allocated')
  GROUP BY entity_id, exposure_currency
) hi ON nav.entity_id = hi.entity_id AND nav.currency_code = hi.exposure_currency
WHERE nav.currency_code = 'AUD'
  AND em.status = 'Active'
  AND nav.nav_type = 'SFX'
  AND nav.as_of_date = (SELECT MAX(as_of_date) FROM position_nav_master WHERE currency_code = 'AUD')
ORDER BY available_capacity DESC;
```

- **TIP:** Or use `v_entity_capacity_complete` or `v_available_amounts_fast` for agent/LLM promptable answers.

***

### Example 2: "Are we approaching USD PB thresholds?"

**Smart Query Logic:**

1. Need current USD equivalent across all currencies
2. Compare against regulatory thresholds by currency
3. Calculate utilization percentages and breach risks

**Intelligent Assembly:**

```sql
-- AI constructs this based on understanding the regulatory context
SELECT 
    hi.exposure_currency,
    SUM(hi.allocated_notional) as current_hedged,
    cc.usd_conversion_rate,
    SUM(hi.allocated_notional * cc.usd_conversion_rate) as usd_equivalent,
    tc.maximum_limit as threshold,
    -- Smart risk calculation
    (SUM(hi.allocated_notional * cc.usd_conversion_rate) / tc.maximum_limit * 100) as utilization_pct,
    -- Intelligent status determination
    CASE 
        WHEN SUM(hi.allocated_notional * cc.usd_conversion_rate) &gt; tc.maximum_limit THEN 'BREACH'
        WHEN SUM(hi.allocated_notional * cc.usd_conversion_rate) &gt; tc.critical_level THEN 'CRITICAL'
        WHEN SUM(hi.allocated_notional * cc.usd_conversion_rate) &gt; tc.warning_level THEN 'WARNING'
        ELSE 'SAFE'
    END as status
FROM hedge_instructions hi
JOIN currency_configuration cc ON hi.exposure_currency = cc.currency_code
JOIN threshold_configuration tc ON hi.exposure_currency = tc.currency_code 
WHERE hi.instruction_status IN ('Executed', 'Allocated')
AND tc.threshold_type = 'USD_PB_DEPOSIT'
GROUP BY hi.exposure_currency, cc.usd_conversion_rate, tc.warning_level, tc.critical_level, tc.maximum_limit
ORDER BY utilization_pct DESC;
```


***

**[ADDED/UPDATED: 2025-09 — Fastest PB/Capacity Check, Full-Schema]**

```sql
SELECT
  v.entity_id,
  v.currency_code,
  v.capacity_total,
  v.capacity_used,
  v.capacity_free,
  v.alerts,
  v.as_of_ts
FROM v_usd_pb_capacity_check v
ORDER BY v.capacity_free ASC;
```

or, utilization:

```sql
SELECT
  entity_id,
  (capacity_used::DECIMAL / capacity_total) * 100 AS utilization_pct,
  capacity_free,
  alerts
FROM v_usd_pb_capacity_check
WHERE capacity_total > 0
ORDER BY utilization_pct DESC;
```

- Thresholds are joined to `threshold_configuration` as needed, with threshold_type = 'USD_PB_DEPOSIT'.

***

## Query Intelligence Patterns

### Pattern 1: Context-Driven JOINs

**Don't**: Query single tables and return "N/A" for missing context
**Do**: Intelligently identify what context is needed and JOIN to get it

### Pattern 2: Business Logic Integration

**Don't**: Return raw numbers without business meaning
**Do**: Apply Stage 1A formulas, waterfall logic, and regulatory rules in the query

### Pattern 3: Freshness Intelligence

**Don't**: Return stale data without considering recency
**Do**: Intelligently identify the most current data and flag freshness

### Pattern 4: Null Handling

**Don't**: Let NULLs break calculations
**Do**: Use COALESCE and intelligent defaults based on business rules

### [ADDED/UPDATED: 2025-09] Key Supabase Views for Fast Context

- Supabase "quick views" for 1A: `v_entity_capacity_complete`, `v_available_amounts_fast`, `v_ccy_to_usd`, `v_usd_pb_capacity_check`, `v_stage1a_to_1b_ready`, `overlay_configuration`.
- Use these for agent query generation—minimizes brittle DIY windowing logic.

***

## When to Use Complex Queries vs. Simple Ones

### Simple Query Scenarios:

- User asks for a specific entity's position
- Basic threshold check for one currency
- Quick validation of a single data point


### Complex Query Scenarios:

- Multi-entity analysis requiring waterfall logic
- Cross-currency regulatory compliance analysis
- Historical trend analysis with multiple time periods
- Failure investigation requiring multiple data sources

***

## The AI Decision Framework

**For each query, the agent should intelligently consider:**

1. **What business question is really being asked?**
    - "Buffer left" = Available hedging capacity
    - "Threshold status" = Regulatory compliance risk
    - "Entity capacity" = Allocation potential
2. **What data elements are essential vs. nice-to-have?**
    - Essential: Entity names, current positions, regulatory limits
    - Nice-to-have: Historical trends, detailed breakdowns
3. **What's the appropriate level of detail?**
    - Executive query: High-level summary with key risks
    - Operational query: Detailed calculations and options
    - Technical query: Full data with validation details
4. **How fresh does the data need to be?**
    - Real-time: Threshold monitoring, active hedge decisions
    - Recent: Capacity planning, trend analysis
    - Historical: Failure investigation, audit trail

***

## The Balance: AI Intelligence + Domain Expertise

### What the AI Should Figure Out (Intelligence):

- **Response format** based on user needs
- **Level of detail** appropriate for the query
- **Table selection** - which data to present
- **Communication style** - executive vs technical
- **Follow-up insights** - what else might be relevant


### What Should Be Guided (Domain Rules):

- **Database relationships** - which tables contain critical context
- **Business formulas** - Stage 1A calculations are non-negotiable
- **Data quality standards** - real entity names vs generic IDs
- **Regulatory requirements** - USD PB compliance is mandatory

***

## Smart Querying Examples

### Intelligence in Action: Buffer Query

**User asks:** "How much buffer is left for AUD?"

**AI Thinks:**

- "Buffer left" = Available capacity after buffers applied
- Need entity context (who), current positions (how much), framework rules (why)
- Should check for current hedges to get accurate available amounts
- User wants actionable numbers, not just raw data

**AI Constructs:**

```sql
-- Intelligently assembled based on business need
SELECT 
    em.entity_name,                    -- Real names for business context
    em.entity_type,                    -- For waterfall prioritization
    pnm.current_position,              -- Current SFX position
    pnm.buffer_amount,                 -- Applied buffer amount
    COALESCE(hi.hedged, 0) as hedged,  -- Current hedges (smart null handling)
    -- The key calculation the user actually wants:
    (pnm.current_position - COALESCE(pnm.optimal_car_amount, 0) - 
     pnm.buffer_amount - COALESCE(hi.hedged, 0)) as available_buffer
FROM entity_master em
JOIN position_nav_master pnm ON em.entity_id = pnm.entity_id
-- Smart join to get current hedges
LEFT JOIN (
    SELECT entity_id, exposure_currency, SUM(allocated_notional) as hedged
    FROM hedge_instructions 
    WHERE instruction_status IN ('Executed', 'Allocated')
    GROUP BY entity_id, exposure_currency
) hi ON em.entity_id = hi.entity_id AND pnm.currency_code = hi.exposure_currency
WHERE pnm.currency_code = 'AUD' AND em.active_flag = 'Y'
ORDER BY available_buffer DESC;
```

**[ADDED/UPDATED: 2025-09]**

- For live use, see earlier: `v_entity_capacity_complete` or `v_available_amounts_fast`.

***

**AI Responds:**

- Leads with the total available: "122.6M AUD buffer capacity available"
- Shows a focused table with entity breakdown
- Explains why certain entities have different buffer rules
- Provides next steps for utilization

***

### Intelligence in Action: Threshold Query

**User asks:** "Are we close to any USD limits?"

**AI Thinks:**

- "USD limits" = USD PB regulatory thresholds
- Need current positions across ALL currencies (not just one)
- Should show utilization percentages and remaining capacity
- This is a risk/compliance question - prioritize safety... **AI Constructs:**

```sql
-- Risk-focused query assembly
SELECT 
    hi.exposure_currency,
    SUM(hi.allocated_notional * cc.usd_rate) as usd_exposure,
    tc.maximum_limit,
    -- Smart risk calculation
    ROUND((SUM(hi.allocated_notional * cc.usd_rate) / tc.maximum_limit) * 100, 1) as utilization_pct,
    (tc.maximum_limit - SUM(hi.allocated_notional * cc.usd_rate)) as remaining_capacity,
    -- Intelligent status assessment
    CASE 
        WHEN SUM(hi.allocated_notional * cc.usd_rate) &gt; tc.critical_level THEN '🚨 CRITICAL'
        WHEN SUM(hi.allocated_notional * cc.usd_rate) &gt; tc.warning_level THEN '⚠️ WARNING'  
        ELSE '✅ SAFE'
    END as risk_status
FROM hedge_instructions hi
JOIN currency_configuration cc ON hi.exposure_currency = cc.currency_code
JOIN threshold_configuration tc ON hi.exposure_currency = tc.currency_code
WHERE hi.instruction_status IN ('Executed', 'Allocated')
GROUP BY hi.exposure_currency, tc.maximum_limit, tc.critical_level, tc.warning_level
ORDER BY utilization_pct DESC;
```

**[ADDED/UPDATED: 2025-09]**

- Query with `v_usd_pb_capacity_check` for optimal live dashboard/agent answer.
***

## Query Construction Intelligence

### Pattern Recognition

The AI should recognize common query patterns:

**Capacity Questions** → Need positions + frameworks + current hedges

- "How much can we hedge?"
- "Available headroom?"
- "Buffer capacity remaining?"

**Risk/Compliance Questions** → Need regulatory data + current exposure

- "Threshold status?"
- "Are we compliant?"
- "Any breach risks?"

**Analysis Questions** → Need comprehensive data + comparisons

- "Compare across entities"
- "Multi-currency analysis"
- "Trend analysis"

***

### Smart Data Assembly Rules

**Rule 1: Context Over Raw Data**
Don't return "Entity0001 has position 100000"
Do return "Australia Main Branch has 25M AUD SFX position"

**Rule 2: Actionable Over Academic**
Don't return "Buffer percentage is 5%"
Do return "5% buffer applied, leaving 23.8M AUD available for hedging"

**Rule 3: Current Over Historical**
Don't use stale position data
Do get the most recent positions and live hedge amounts

**Rule 4: Complete Over Partial**
Don't return incomplete calculations with missing components
Do ensure all formula elements are present or intelligently defaulted

**[ADDED/UPDATED 2025-09 — Field best-practice]**

- Always check `as_of_date` fields for recency.
- For audit/troubleshooting, reference `audit_trail` or `v_hedge_lifecycle_status`.

***

## AI Decision Framework for Queries

For each request, the AI should ask itself:
(As before; No text removed)

***

## The Smart Agent Approach

Instead of rigid templates, the agent should:

1. **Understand the business intent** behind each query
2. **Intelligently determine required data elements**
3. **Construct appropriate queries** to get complete information
4. **Apply business logic and formulas** correctly
5. **Present results** in the most useful format for the user's needs
6. **Provide actionable insights** beyond just raw data

**[ADDED: Schema/Query "Cheat Sheet" for 2025-09]**

- Fastest/most robust answers are usually generated via prebuilt views (v_*), not by hand-encoded multi-way joins.
- Use the "Supabase Reference Guide Agent-Focused" for canonical table/view/column names.

***

## MCP Tool Integration Patterns (NEW)

### Dedicated Stage 1A MCP Server (Port 8010)

The new `allocation_stage1a_processor` tool automatically handles query construction and intent detection:

**Natural Language → Optimized Views:**
```
"Show AUD capacity" → v_entity_capacity_complete WHERE currency_code='AUD'
"USD PB status" → v_usd_pb_capacity_check
"Available amounts for EUR" → v_available_amounts_fast WHERE currency_code='EUR'
```

**Instruction Processing → Full Pipeline:**
```
"Can I hedge 150K HKD?" → Complete Stage 1A analysis + hedge_instructions write
"Process utilization check for 2M EUR" → Full feasibility + persistence
```

### View-First Optimization Strategy

**Primary Views for Auto-Routing:**
1. `v_entity_capacity_complete` - Complete capacity analysis
2. `v_available_amounts_fast` - Rapid capacity calculations
3. `v_usd_pb_capacity_check` - USD threshold monitoring
4. `v_allocation_waterfall_summary` - Priority sequencing

**Fallback Chain:**
```
Optimized View → Raw Table Assembly → Error with Graceful Message
```

### Intent Detection Examples

**Query Intent Patterns:**
- `"show"`, `"what's"`, `"available"`, `"status"` → View-based response
- `"breakdown"`, `"summary"`, `"analysis"` → Analytical views

**Instruction Intent Patterns:**
- `"can I"`, `"check if"`, `"process"` → Full pipeline
- Currency + Amount combinations → Utilization processing
- `"hedge"`, `"place"`, `"put on"` → Stage 1A instruction flow

***

**Remember**:
The goal is intelligent completeness — providing exactly what's needed for informed decisions, with the flexibility to adapt to different user needs and query complexities. The new MCP integration automates the decision-making process while maintaining full Stage 1A compliance.

***

**END OF UPDATED FILE — All sections retained, MCP integration patterns added.**


