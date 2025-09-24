# Project Progress Log — MCP Tools + Filtering + Health (2025-09-17)

Timestamp: 2025-09-17T02:45Z
Author: Codex CLI Agent

## Summary
- Resolved Dify↔MCP integration issues (path, CORS, auth header) and added robust health probes.
- Fixed currency filtering behavior for MCP tool flows by merging tool args into extractor params and adding filters to `threshold_configuration` and `currency_rates`.
- Introduced response caps to prevent oversized payloads and added a v2 MCP server with stage aliasing and safer defaults.
- Identified production blocker: Supabase 401 due to invalid/expired service role key.

## Key Findings
- Wrong path and missing `Authorization` header in Nginx initially blocked JSON‑RPC; fixed by forwarding header and supporting `/mcp/` alias.
- Dify tool errors ("no tool named …") traced to handshake failures and tool not attached/enabled for the specific agent.
- Stage mismatch: client sent `stage_mode: "stage_1a"` (invalid). Server accepts `"auto"|"1A"|"2"|"3"`.
- Agent role/report type mismatch: only `allocation|booking|unified` supported.
- Supabase errors: `401 Invalid API key` for all direct queries; health previously reported "connected" because it only verified client initialization, not query.

## Changes Made
- MCP server (production) improvements
  - `hedge-agent/mcp_server_production.py`
    - Added GET `/` JSON health payload; added `/health` and `/health/db` real DB probe.
    - Expanded CORS to include `GET/HEAD/OPTIONS`.
    - Added `/mcp/` path aliases for POST/GET.
- Lightweight server banner
  - `hedge-agent/dify_compatible_mcp_server.py`: Updated endpoint note to root path.
- Tool arg → filter merge + table filters
  - `hedge-agent/shared/hedge_processor.py`: merge `currency/entity_id/nav_type/amount` into `extracted_params` before extraction.
  - `hedge-agent/shared/data_extractor.py`: apply currency filters to `threshold_configuration (currency_code)` and `currency_rates (from_currency|to_currency)`; existing filters preserved for other tables.
- Response caps in processor
  - `hedge-agent/shared/hedge_processor.py`: accept `max_rows/max_kb` and cap per-table list sizes; annotate metadata.
- Diagnostic utilities
  - `hedge-agent/tools/test_currency_filters.py`: verifies extractor applies currency filters (mocked Supabase).
  - `hedge-agent/tools/test_processor_caps.py`: verifies processor row caps.
- MCP server v2 (additive option)
  - `hedge-agent/mcp_server_production v2.py` (new variant):
    - Stage alias map (accepts `stage_1a` → `1A`).
    - Prompt-intelligent defaults for Stage 1A reads; size guards (`max_rows/max_kb`).
    - Unified health with DB probe; `/mcp/` aliases; stricter init gating.

## How To Verify (Cloud)
- Health and DB probe:
  - `GET https://<host>/mcp/health` → shows masked key + probe status.
  - `GET https://<host>/mcp/health/db` → must return `{ "status": "ok", ... }`. If error contains `Invalid API key`, rotate `SUPABASE_SERVICE_ROLE_KEY` and restart.
- Dify External Tool:
  - URL: `https://<host>/mcp/`
  - Headers: `Authorization: Bearer <DIFY_TOOL_TOKEN>`, `Content-Type: application/json`
  - Attach + enable for each agent.
- Filter proof (bypass cache):
  - `query_supabase_data` select `currency_rates` with `from_currency=eq.HKD`, `to_currency=eq.USD`, `order_by=-effective_date`, `limit=1`, `use_cache=false`.
  - `query_supabase_data` select `threshold_configuration` with `currency_code=eq.HKD`, `limit=50`, `use_cache=false`.
- Stage‑1A read with caps:
  - `process_hedge_prompt` with `stage_mode="1A"`, `operation_type="read"`, `currency=<CCY>`, `amount=<num>`, `use_cache=false`, `output_format="json"`, `max_rows=100`.

## Outstanding Items
- Supabase key: rotate and update `SUPABASE_SERVICE_ROLE_KEY` on the server; restart MCP.
- Schema variance: if `currency_rates` uses `currency_pair`, adjust extractor to filter `currency_pair='CCYUSD'` (and reverse) + correct date column.
- Optional: extend extractor to enforce `max_rows` at query time (not just post‑process), and adopt v2 server in place of current app.

## Timeline (UTC)
- 2025‑09‑16: Identified Dify tool handshake and Nginx header forwarding issues; added aliases and CORS changes.
- 2025‑09‑16: Diagnosed Supabase 401; added `/health/db` probe; confirmed key issue.
- 2025‑09‑16/17: Merged tool args → extractor params; added filters for thresholds/rates; introduced processor caps; added tests.
- 2025‑09‑17: Prepared `mcp_server_production v2.py` with stage aliasing and caps.

## Next Steps
- [ ] Update service role key; restart MCP; confirm `/mcp/health/db` is OK.
- [ ] Re‑test currency‑filtered selects with `use_cache=false`.
- [ ] Decide on adopting v2 server; if yes, deploy and point Nginx to it.
- [ ] Optionally enforce caps at query level in extractor for large tables.

