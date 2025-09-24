# Direct CRUD Cheatsheet (Aligned to HAWK KB)

Purpose: Let MCP tool `query_supabase_data` perform reliable CRUD without hardcoding. Fields below reflect KB docs and the constraints observed during live tests.

Notes
- Use a valid `entity_id` from `entity_master` to satisfy FKs.
- Include a unique `msg_uid` on new instructions to avoid duplicate fingerprints on retries.
- Status columns often have CHECK constraints — use allowed values configured in your DB.
- Timestamps default in DB when possible; provide only when needed.

Stage 1A (Pre‑Utilization)
- `hedge_instructions` (INSERT, UPDATE)
  - Required (insert): `instruction_type` (I/U/R/T), `instruction_date` (YYYY‑MM‑DD), `exposure_currency`, `hedge_amount_order`, `hedge_method` (e.g., COH)
  - Recommended: `msg_uid` (unique id), `order_id`
  - Status: if provided, must pass DB check (e.g., Received/Created/Amended/Completed per your schema)
- Lookups (SELECT): `entity_master`, `position_nav_master`, `buffer_configuration`, `threshold_configuration`, `currency_rates`, `hedging_framework`

Stage 1B (Allocation & Events)
- `allocation_engine` (INSERT, UPDATE)
  - Required (insert): `allocation_id`, `request_id`, `entity_id`, `currency_code`, `nav_type`, `hedge_amount_allocation`, `sfx_position`
  - Defaults (DB): `calculation_date`, `executed_date`, `created_date` — ensure defaults are set in DB
  - Status (update): `allocation_status` must be one of allowed values per DB constraint
- `hedge_business_events` (INSERT, UPDATE)
  - Required (insert): `instruction_id`, `business_event_type` (e.g., Initiation/Rollover/Termination), `event_status` (e.g., Pending/Approved)
  - Optional: `notional_amount`, `nav_type`, `currency_type`, `hedging_instrument`, `accounting_method`, `trade_date`

Stage 2 (Booking)
- `deal_bookings` (INSERT, UPDATE)
  - Required (insert): `booking_id`, `instruction_id` (or `event_id`), `portfolio_code`, `notional_amount`, `currency`, `booking_status`
  - Optional: `value_date`, `maturity_date`, `murex_deal_id`
- `h_stg_mrx_ext` (INSERT)
  - Required: `message_id`, (`instruction_id` or `booking_id`), `message_type` (e.g., BOOKING_REQUEST), `message_status` (e.g., QUEUED), `message_payload` (JSON text)

Stage 3 (GL Posting)
- `hedge_gl_packages` (INSERT, UPDATE)
  - Required (insert): `package_id`, `instruction_id` (or `event_id`), `booking_id`, `package_status` (e.g., DRAFT), `gl_date`, `currency`
- `hedge_gl_entries` (INSERT)
  - Required: `entry_id`, `package_id`, `instruction_id`, `account_code`, `entry_type` (DEBIT/CREDIT), `debit_amount` or `credit_amount`, `currency`
  - Optional: `narrative`, `business_unit`, `profit_center`

Examples (query_supabase_data)
- SELECT
  - `{ "table_name": "entity_master", "operation": "select", "limit": 1 }`
- INSERT hedge_instructions
  - `{ "table_name": "hedge_instructions", "operation": "insert", "data": { "instruction_type": "I", "instruction_date": "2025-09-15", "exposure_currency": "USD", "hedge_amount_order": 1000000, "hedge_method": "COH", "msg_uid": "POC_123" } }`
- INSERT allocation_engine (FK‑safe + sfx)
  - `{ "table_name": "allocation_engine", "operation": "insert", "data": { "allocation_id": "ALLOC_POC_1", "request_id": "REQ_ALLOC_POC_1", "entity_id": "ENTITY0001", "currency_code": "USD", "nav_type": "COI", "sfx_position": 150000, "hedge_amount_allocation": 12345 } }`
- INSERT hedge_business_events
  - `{ "table_name": "hedge_business_events", "operation": "insert", "data": { "instruction_id": "INST_...", "business_event_type": "Initiation", "event_status": "Pending" } }`

Troubleshooting
- Duplicate instruction: add a unique `msg_uid` per request.
- NOT NULL violations in allocation_engine: ensure DB defaults exist or provide fields (`sfx_position`, `calculation_date`, `executed_date`).
- Status check errors: use a value allowed by your DB constraint or adjust the CHECK list in DB.

