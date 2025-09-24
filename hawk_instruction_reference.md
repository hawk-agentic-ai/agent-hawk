# HAWK Instruction Reference Guide
## Instruction Types, Prompts, Fields, and Database Dependencies

### Document Overview
This document provides a comprehensive reference for all HAWK instruction types, including example prompts, mandatory field requirements, and database table dependencies that Dify relies on for execution.

---

## Instruction Reference Table

| Instruction Type | Example Prompts | Mandatory Fields | Tables and Values Dify Depends On |
|-----------------|-----------------|------------------|-----------------------------------|
| **Utilization (U)** |  "Execute FX hedge utilization for EUR 10M exposure"<br/> "Process utilization instruction for JPY 500M against COI portfolio"<br/> "Hedge EUR exposure of 15M for revenue protection" |  `MSG_UID` (Unique Message ID)<br/> `Instruction_Type` = 'U'<br/> `Exposure_Currency_Code`<br/> `Notional_Amount`<br/> `Business_Date`<br/> `Entity_Code`<br/> `NAV_Type` (COI/RE) | **Primary Tables:**<br/> `hedge_instructions`<br/> `hedge_business_events`<br/> `entity_allocation_master`<br/> `currency_configuration`<br/><br/>**Key Values:**<br/> Entity allocation amounts from `allocation_amount`<br/> Currency type classification (G3/Non-G3/EM)<br/> Buffer percentages from `buffer_config`<br/> USD PB thresholds from `threshold_config` |
| **Inception (I)** |  "Start hedge inception for USD 25M COI exposure"<br/> "Initialize new hedge position for GBP 8M revenue protection"<br/> "Create inception instruction for CNY 100M subsidiary hedge" |  `MSG_UID`<br/> `Instruction_Type` = 'I'<br/> `Exposure_Currency_Code`<br/> `Notional_Amount`<br/> `Business_Date`<br/> `Entity_Code`<br/> `NAV_Type` (COI/RE)<br/> `Hedge_Start_Date`<br/> `Hedge_End_Date` | **Primary Tables:**<br/> `hedge_instructions`<br/> `hedge_business_events`<br/> `booking_model_config`<br/> `deal_bookings`<br/> `portfolio_assignments`<br/><br/>**Key Values:**<br/> Booking model assignment (A-COI, B-COI, etc.)<br/> Deal sequence configurations<br/> Portfolio routing rules<br/> Currency pair validations |
| **Rollover (R)** |  "Process rollover for existing EUR 12M hedge position"<br/> "Extend maturity for JPY 300M hedge to next quarter"<br/> "Rollover CNY hedge with updated terms and conditions" |  `MSG_UID`<br/> `Instruction_Type` = 'R'<br/> `Exposure_Currency_Code`<br/> `Current_Notional_Amount`<br/> `New_Notional_Amount`<br/> `Original_Hedge_ID`<br/> `New_Maturity_Date`<br/> `Business_Date` | **Primary Tables:**<br/> `hedge_instructions`<br/> `existing_hedge_positions`<br/> `rollover_configurations`<br/> `hedge_amendments`<br/><br/>**Key Values:**<br/> Original hedge position details<br/> Rollover rate adjustments<br/> New term calculations<br/> Amendment approval status |
| **Maturity (M)** |  "Process maturity settlement for USD 20M hedge expiring today"<br/> "Handle natural maturity for EUR 5M revenue hedge"<br/> "Execute maturity closure for TWD 50M subsidiary hedge" |  `MSG_UID`<br/> `Instruction_Type` = 'M'<br/> `Hedge_ID`<br/> `Exposure_Currency_Code`<br/> `Settlement_Amount`<br/> `Maturity_Date`<br/> `Settlement_Method` | **Primary Tables:**<br/> `hedge_instructions`<br/> `existing_hedge_positions`<br/> `maturity_settlements`<br/> `pnl_calculations`<br/><br/>**Key Values:**<br/> Current hedge position values<br/> Settlement rates and amounts<br/> P&L impact calculations<br/> Accounting entries requirements |
| **Amendment (A)** |  "Amend order ORD-2025-011 previous ORD-2025-007 changing notional from 100M to 120M"<br/> "Process amendment ORD-2025-012 previous ORD-2025-008 update maturity date"<br/> "Execute amendment ORD-2025-013 previous ORD-2025-009 modify hedge method to NDF" |  `msg_uid`<br/> `instruction_type` = 'A'<br/> `exposure_currency`<br/> `order_id` **(MANDATORY)**<br/> `previous_order_id` **(MANDATORY)**<br/> `hedge_amount_order`<br/> `hedge_method`<br/> `instruction_date`<br/> `tenor_or_maturity` | **Primary Tables:**<br/> `hedge_instructions`<br/> `hedge_business_events`<br/> `hedge_effectiveness`<br/> `audit_trail`<br/><br/>**Key Values:**<br/> Original hedge parameters<br/> Amendment validation rules<br/> Change tracking requirements<br/> Impact assessment results |
| **Inquiry (Q)** |  "Check status of hedge instruction MSG-I-2025-123456"<br/> "Query available EUR hedging capacity for entity ENT001"<br/> "Status inquiry for all pending orders for CNY currency" |  `msg_uid`<br/> `instruction_type` = 'Q'<br/> `instruction_date`<br/> `order_id` (optional for specific order)<br/> `exposure_currency` (optional for currency-specific)<br/> `request_id` (for tracking) | **Primary Tables:**<br/> `hedge_instructions`<br/> `hedge_business_events`<br/> `allocation_engine`<br/> `audit_trail`<br/><br/>**Key Values:**<br/> Current processing status<br/> Available allocation amounts<br/> Position summaries<br/> System health indicators |
| **Bulk Processing (B)** |  "Process bulk file BATCH-2025-001 containing 25 hedge instructions"<br/> "Execute batch processing for monthly hedge renewal batch"<br/> "Submit bulk inception file with multiple currency instructions" |  `msg_uid`<br/> `instruction_type` = 'B'<br/> `instruction_date`<br/> `request_id` (batch identifier)<br/> `external_trade_id` (file reference)<br/> Processing details in file | **Primary Tables:**<br/> `hedge_instructions`<br/> `audit_trail`<br/> `allocation_engine`<br/> Multiple related tables<br/><br/>**Key Values:**<br/> Batch processing limits<br/> File validation results<br/> Individual instruction status<br/> Consolidated reporting |

---

## Field Validation Matrix by Instruction Type

### Critical Field Dependencies

| Field Category | Utilization (U) | Inception (I) | Rollover (R) | Maturity (M) | Early Term (E) | Amendment (A) | Inquiry (Q) | Bulk (B) |
|----------------|-----------------|---------------|--------------|--------------|----------------|---------------|-------------|----------|
| **Message Identification** | `MSG_UID`<br/>`Trace_ID` | `MSG_UID`<br/>`Trace_ID` | `MSG_UID`<br/>`Trace_ID`<br/>`Original_MSG_UID` | `MSG_UID`<br/>`Trace_ID`<br/>`Hedge_ID` | `MSG_UID`<br/>`Trace_ID`<br/>`Hedge_ID` | `MSG_UID`<br/>`Trace_ID`<br/>`Hedge_ID` | `MSG_UID`<br/>`Query_ID` | `MSG_UID`<br/>`Batch_ID` |
| **Currency & Amount** | `Exposure_Currency_Code`<br/>`Notional_Amount` | `Exposure_Currency_Code`<br/>`Notional_Amount` | `Exposure_Currency_Code`<br/>`Current_Notional`<br/>`New_Notional` | `Exposure_Currency_Code`<br/>`Settlement_Amount` | `Exposure_Currency_Code`<br/>`Termination_Amount` | `Exposure_Currency_Code`<br/>`Amendment_Amount` | `Exposure_Currency_Code` (optional) | Multiple currencies supported |
| **Date Parameters** | `Business_Date`<br/>`Value_Date` | `Business_Date`<br/>`Hedge_Start_Date`<br/>`Hedge_End_Date` | `Business_Date`<br/>`Rollover_Date`<br/>`New_Maturity_Date` | `Business_Date`<br/>`Maturity_Date`<br/>`Settlement_Date` | `Business_Date`<br/>`Termination_Date`<br/>`Value_Date` | `Business_Date`<br/>`Amendment_Date`<br/>`Effective_Date` | `Business_Date`<br/>`Query_Date` | `Business_Date`<br/>`Batch_Date` |
| **Entity Information** | `Entity_Code`<br/>`NAV_Type`<br/>`Portfolio_Code` | `Entity_Code`<br/>`NAV_Type`<br/>`Portfolio_Code` | `Entity_Code`<br/>`Portfolio_Code` | `Entity_Code`<br/>`Portfolio_Code` | `Entity_Code`<br/>`Portfolio_Code` | `Entity_Code`<br/>`New_Entity_Code` | `Entity_Code` (optional) | Multiple entities supported |

---

## Database Dependency Details

### Core Configuration Tables

#### 1. Entity Allocation Master
```sql
Table: entity_allocation_master
Key Fields Dify Depends On:
 entity_code (Primary identifier)
 exposure_currency (Currency classification)
 nav_type (COI/RE designation)
 allocation_amount (Available hedge capacity)
 buffer_percentage (Risk buffer allocation)
 hedging_framework (Fully_Hedge/Excess_CAR)
 car_exemption_flag (Y/N buffer trigger)
```

#### 2. Currency Configuration
```sql
Table: currency_configuration
Key Fields Dify Depends On:
 currency_code (ISO currency identifier)
 currency_type (G3/Non-G3/Emerging_Market)
 base_currency_pair (USD, SGD cross rates)
 trading_hours (Market availability)
 settlement_days (T+0, T+1, T+2)
 minimum_deal_amount (Threshold validation)
```

#### 3. Booking Model Configuration
```sql
Table: booking_model_config
Key Fields Dify Depends On:
 model_code (A-COI, B-COI, C-COI, A-RE, B-RE, C-RE)
 currency_type (Model assignment logic)
 nav_type (COI/RE classification)
 deal_count (Expected number of deals)
 portfolio_sequence (Deal routing logic)
 validation_rules (Business rule enforcement)
```

#### 4. Threshold Configuration Master
```sql
Table: threshold_config_master
Key Fields Dify Depends On:
 entity_code (Threshold ownership)
 threshold_type (USD_PB_Deposit, CAR_Limit)
 threshold_amount (Validation limit)
 currency_code (Threshold currency)
 warning_percentage (Early warning trigger)
 breach_action (Auto-reject/Manual review)
```

### Transaction Processing Tables

#### 5. Hedge Instructions (Primary Transaction Table)
```sql
Table: hedge_instructions
Key Fields Dify Uses:
 instruction_id (Unique transaction ID)
 msg_uid (External reference)
 instruction_type (U/I/R/M/E/A/Q/B)
 exposure_currency (Currency validation)
 notional_amount (Amount processing)
 entity_code (Allocation lookup)
 business_date (Processing date)
 processing_status (Workflow state)
```

#### 6. Hedge Business Events
```sql
Table: hedge_business_events
Key Fields Dify Monitors:
 event_id (Event tracking)
 instruction_id (Parent instruction)
 business_event_type (Utilization/Inception)
 assigned_booking_model (Model determination)
 stage_1a_status (Assessment result)
 stage_2_status (Booking result)
 apportionment_result (Allocation outcome)
```

---

## Dify Execution Dependencies

### Real-Time Data Requirements

#### 1. **For Utilization Instructions**
Dify requires immediate access to:
- Current allocation amounts from `entity_allocation_master`
- Real-time USD PB balances from `threshold_config_master`
- Buffer calculations from `buffer_allocation_rules`
- Existing hedge positions from `existing_hedge_positions`

#### 2. **For Inception Instructions**  
Dify requires immediate access to:
- Booking model assignments from `booking_model_config`
- Portfolio routing rules from `portfolio_assignments`
- Deal sequence templates from `deal_sequence_master`
- Currency pair validations from `currency_configuration`

#### 3. **For All Instruction Types**
Dify requires immediate access to:
- Field validation rules from `validation_framework`
- Processing status tracking in `hedge_business_events`
- Audit trail requirements from `audit_trail_config`
- Response templates from `response_message_templates`

### Critical Performance Dependencies

| Operation | Required Response Time | Database Tables Accessed | Key Performance Factors |
|-----------|----------------------|---------------------------|------------------------|
| **Field Validation** | <500ms | `validation_framework`, `currency_configuration` | Indexed lookups, cached reference data |
| **Allocation Assessment** | <1000ms | `entity_allocation_master`, `threshold_config_master` | Real-time balance checks, buffer calculations |
| **Model Assignment** | <200ms | `booking_model_config`, `currency_configuration` | Rule-based logic, configuration caching |
| **Status Updates** | <100ms | `hedge_business_events`, `processing_status_log` | Optimized inserts, minimal locking |

---

## ** Complete Instruction Processing Sub-Stages**

### **Stage 1A: Universal 8-Step Processing (All Instructions)**

Every instruction (U, I, R, T, A, Q, B) follows this exact sequence:

| Step | Process | Utilization (U) | Inception (I) | Rollover (R) | Termination (T) |
|------|---------|-----------------|---------------|--------------|-----------------|
| **1** | **Instruction Receipt** |  Trace ID assigned |  Trace ID assigned |  Trace ID assigned |  Trace ID assigned |
| **2** | **Multiple Records Check** |  Warn duplicates |  Handle UI conversion |  Validate sequence |  Validate sequence |  
| **3** | **Field Validation** |  Currency, Date |  All mandatory fields |  All mandatory fields |  All mandatory fields |
| **4** | **Release Scope Check** |  Supported version |  Supported version |  Supported version |  Supported version |
| **5** | ** USD PB Check** |  **6 sub-steps** |  **6 sub-steps** |  **6 sub-steps** |  **6 sub-steps** |
| **6** | **Pre-Utilization Engine** |  Capacity calculation |  Allocation assessment |  Position validation |  Settlement check |
| **7** | **Type-Specific Branch** |  **END with response** |  Continue to Step 8 |  Continue to Step 8 |  Continue to Step 8 |
| **8** | **Apportionment Engine** |  **Skipped** |  Allocation feasibility |  Rollover feasibility |  Termination impact |

### **Stage 1A Completion Points:**

- **Utilization ('U')**: Ends at Step 7 with capacity response
- **All Other Types**: Complete full 8-step process before Stage 2 progression

## Instruction Reference Table

From the `hedge_instruments` table, **FX Instruments** are:

### **Available Instrument Types:**
1. **FX_Swap** - Primary instrument for most scenarios
2. **NDF** - Non-Deliverable Forward for proxy currencies  
3. **Forward** - Basic FX forward contracts
4. **Option** - FX options for complex hedging
5. **Cross_Currency_Swap** - Multi-currency hedging

### **Key Selection Fields:**
- `instrument_type` - The actual instrument classification
- `currency_pair` - Supported currency combinations
- `currency_classification` - Matched/Mismatched/Proxy logic
- `nav_type_applicable` - COI/RE applicability
- `accounting_method_supported` - COH/Fair_Value support
- `settlement_type` - Physical/Cash_Settled
- `minimum_notional` / `maximum_notional` - Amount limits

### **NAV Type** (From `hedge_business_events.nav_type`):
- **COI** - Capital-Others-Investment
- **RE** - Revenue-Earnings
- **MANDATORY for Inception instructions**

**Updated Logic:**
- **U (Utilization)**: Currency + Date (Amount optional for limit checking)
- **I (Inception)**: Needs `order_id`, `hedge_amount_order`, `hedge_method`, `NAV_type`, FX Instrument
- **R,T (Rollover/Termination)**: Needs `order_id`, `previous_order_id`, `hedge_amount_order`, `hedge_method`

---

## Configuration Management for Dify

### Environment-Specific Dependencies

| Environment | Configuration Source | Critical Settings |
|-------------|---------------------|------------------|
| **Development** | `dev_config_master` | Mock external systems, reduced thresholds |
| **Testing** | `test_config_master` | Full validation enabled, test data isolation |
| **Production** | `prod_config_master` | Live thresholds, full audit trail, real-time monitoring |

### Dynamic Configuration Updates

Dify must monitor these tables for real-time configuration changes:
- `threshold_config_master` (Updated limits)
- `entity_allocation_master` (Capacity changes)
- `currency_configuration` (Market hours, holidays)
- `booking_model_config` (Model rule updates)

---

**Document Control**
- **Version**: 1.0
- **Created**: September 2025
- **Target Audience**: Dify Integration Team, HAWK Developers
- **Update Frequency**: As system requirements evolve
- **Dependencies**: HAWK Database Schema v2.1, API Specification v1.3