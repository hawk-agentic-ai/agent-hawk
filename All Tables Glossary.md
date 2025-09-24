*

# Supabase Tables \& Views — Agent-Focused Index (v1.0, Exhaustive \& Cross-Verified)

| Table Name (exact) | Table Type (Base/View/Materialized) | Key Purpose / Description (Business Facing) | Key Columns (business/ops facing) | Agent | Stage |
| :-- | :-- | :-- | :-- | :-- | :-- |
| allocation_engine | Base | Entity-currency allocation headroom, output of Stage 1B | allocation_id, request_id, entity_id, currency_code, nav_type, sfx_position | Booking Agent | Stage 1B/2 |
| audit_trail | Base | Operational/audit trail of actions/events across all stages | audit_id, trace_id, transaction_id, msg_uid, stage, process_step | Analytics Agent | Cross-stage |
| buffer_configuration | Base | Buffer rule % per entity/currency, checked in all capacity/headroom/eligibility | buffer_rule_id, entity_id, currency_code, hedging_framework, car_exemption_flag, entity_type | Analytics Agent | Cross-stage |
| capacity_overrides | Base | Capacity overrides per entity/currency for headroom exceptions | override_id, entity_id, currency_code, capacity_override, effective_start, effective_end | Analytics Agent | Cross-stage |
| car_master | Base | Entity-level Capital Adequacy Ratio (CAR) master (buffer calculation) | entity_id, car_ratio, car_effective_from, car_effective_to, status | Allocation Agent | 1A/1B (Eligibility) |
| car_parameters | Base | CAR calculation parameters (method, thresholds) | car_param_id, entity_id, currency_code, car_ratio, method, effective_start | Analytics Agent | Cross-stage |
| car_thresholds | Base | Threshold bounds for CAR tests in headroom logic | threshold_id, entity_id, currency_code, lower_bound, upper_bound, effective_start | Analytics Agent | Cross-stage |
| currency_configuration | Base | All currency-specific rules, matched/proxy flags, PB deposit requirements | currency_code, currency_type, ndf_supported, onshore_symbol, offshore_symbol, pb_deposit_required | Allocation Agent | Stage 1A |
| currency_rate_pairs | Base | Onshore/offshore pair metadata, used in booking and proxy logic | pair_code, base_ccy, quote_ccy, precision, invertible, active_flag | Allocation Agent | Stage 1A |
| currency_rates | Base | Market, spot, historical, prevailing FX rates | from_ccy, to_ccy, rate, as_of_ts, source, is_onshore | Allocation Agent | Stage 1A |
| currency_rates_parsed | View | currency_rates with parsed ccy_from/ccy_to, easier FX analytics | currency_pair, ccy_from, ccy_to, rate_type, rate_value, effective_date | Booking, Analytics | Cross-stage |
| deal_bookings | Base | All booked spot/swap/NDF deals (Stage 2), GL linkage | deal_id, event_id, product_code, trade_ref, near_leg_date, far_leg_date | Booking Agent | Stage 1B/2 |
| deal_bookings_archive | Base | Historical archive for analytics and audit lineage | deal_id, event_id, product_code, trade_ref, near_leg_date, far_leg_date | Analytics Agent | Cross-stage |
| entity_master | Base | Parties/entities registry, structure for eligibility \& reporting | entity_id, entity_name, entity_type, country_code, status, parent_entity_id | Allocation Agent | Stage 1A |
| entity_threshold_configuration | Base | Entity + currency thresholds for escalation and headroom logic | config_id, entity_id, currency_code, threshold_name, threshold_value, effective_start | Analytics Agent | Cross-stage |
| fx_proxy_parameters | Base | Proxy/NDF tuning params per currency/config | proxy_param_id, proxy_ccy, ndf_forward_curve, embedded_spot_flag, usd_funding_required | Booking Agent | Stage 2 |
| gl_be_narrative_templates | Base | BE→GL mapping: standard posting narratives/templates | template_id, be_code, narrative_template, status, effective_start | GL/Posting Agent | Stage 3 |
| gl_coa | Base | Chart of Accounts (master), required for GL/ERP posting logic | account_code, description, segments, active_flag | GL/Posting Agent | Stage 3 |
| gl_entries | Base | GL journal line headers for posting (Stage 3) | entry_id, package_id, be_code, dr_account, cr_account, dr_amount_sgd | GL/Posting Agent | Stage 3 |
| gl_entries_archive | Base | Archive of old entries, supports audits and rollback | entry_id, package_id, be_code, dr_account, cr_account, dr_amount_sgd | Analytics/GL | Stage 3+ |
| gl_entries_detail | Base | Field-level breakdowns of GL line calcs | detail_id, entry_id, field_name, field_value, calc_method, created_at | GL/Posting Agent | Stage 3 |
| gl_journal_lines | Base | Finalized lines for GL export/posting, reflects posting status | journal_id, batch_id, line_seq, account, amount_sgd, currency | GL/Posting Agent | Stage 3 |
| gl_periods | Base | Accounting month control, blocks posting to closed/future periods | period_id, start_date, end_date, is_open | GL/Posting Agent | Stage 3 |
| gl_posting_queue | Base | Queue for batch posting/export handoff to ERP | queue_id, batch_id, status, attempts, last_error_code, last_error_message | GL/Posting Agent | Stage 3 |
| gl_rules | Base | Posting rules-driven DR/CR model per event/model | rule_id, scope (json), lines (json), effective_from, effective_to | GL/Posting Agent | Stage 3 |
| h_stg_mrx_ext | Base | MX integration staging (inbound/outbound) for reconciliation | stg_id, event_id, instruction_id, direction, payload, status | Booking Agent, Ops | Stage 2 |
| hawk_agent_attachments | Base | Agent file storage for audit and reference | attachment_id, file_url, user_id, created_at | All Agents | Any |
| hawk_agent_conversations | Base | LLM/agent conversation transcripts | conversation_id, topic, status, created_by, created_at | All Agents | Any |
| hawk_agent_errors | Base | Errors/failures tracked by agent hosts | error_id, session_id, agent_type, timestamp, error_code, error_message | All Agents | Any |
| hawk_agent_sessions | Base | Session state for agent workflows | session_id, user_id, status, config_snap, created_at | All Agents | Any |
| hawk_hbe_instruction_mismatch | View | Detects mismatches between Stage 1 instruction and actual HBE emitted | event_id, instruction_id, mismatch_type, message, detected_at | Audit/Booking | 1B/2 |
| hedge_be_config | Base | Stage-3 BE codes and mapping to GL | be_code, product_code, event_type, gl_account, narrative_template | GL/Posting Agent | Stage 3 |
| hedge_business_events | Base | Canonical hedge business event store (entity/currency/event) | event_id, instruction_id, entity_id, currency_code, nav_type, model_type | Booking Agent | 1B/2 |
| hedge_effectiveness | Base | Analytical regression and effectiveness analysis | effectiveness_id, event_id, method, result, as_of_date | Analytics | Cross-stage |
| hedge_instructions | Base | Instruction intake (all types: U, I, R, T), feeds further stages | instruction_id, msg_uid, instruction_type, instruction_date, exposure_currency | Allocation Agent | 1A |
| hedge_instructions_archive | Base | Archive for historical instruction records | instruction_id, msg_uid, instruction_type, instruction_date, exposure_currency | Analytics Agent | Cross-stage |
| hedge_instructions_legacy | View | Legacy/compatibility view of instructions pulling deprecated fields | instruction_id, order_id, deprecated_fields* (varies) | Ops/Migration | Any |
| hedge_instruments | Base | Hedge instrument registry (FX/NDF/COH/MT/QD) | instrument_id, instrument_type, ccy_1, ccy_2, status | Allocation/Booking | 1A/2 |
| hedging_framework | Base | Entity/currency method eligibility/config | config_id, entity_id, currency_code, allowed_methods | Allocation Agent | 1A/1B |
| hfm_template_entries | Base | Hyperion Financial Mgmt (HFM) reporting analytic data | entry_id, template_type, reporting_date, blend_rate, comments | Analytics | Any |
| instruction_event_config | Base | Mapping/rules for instruction→event transformation and approval requests | config_id, instruction_type, nav_type, currency_type, model_map, approvals_required | Booking Agent | 1B/2 |
| market_data | Base | External market data feeds for FX/commodities | data_id, feed_type, symbol, value, as_of_ts | Analytics Agent | Cross-stage |
| murex_book_config | Base | Booking/routing config for correct portfolio, product assignment | config_id, model_type, product_code, portfolio_flow, booking_template | Booking Agent | 2 |
| mv_car_latest | Materialized View | Fast snapshot latest CAR per entity for real-time eligibility | entity_id, as_of_date, car_ratio, car_distribution | Allocation/Analytics | 1A/1B |
| mx_discounted_spot | Base | Discounted spot reference trades by currency | mx_id, ccy, spot_rate, discount_flag, as_of_ts | Booking Agent | 2 |
| mx_proxy_hedge_report | Base | Reports on proxy/NDF MX deals (e.g. for TWD/KRW proxy analysis) | report_id, event_id, proxy_ccy, ndf_forward_rate, embedded_spot_rate | Booking Agent + Analytics | 2 |
| overlay_configuration | Base | Overlay logic for position/capacity/manual ops and system flags | overlay_id, entity_id, currency_code, overlay_amount, reason_code, effective_start | Ops/Analytics | Cross-stage |
| portfolio_positions | Base | Aggregated/portfolio-level positions by ccy | portfolio_id, currency_code, position_fc, position_sgd | Analytics Agent | Cross-stage |
| position_nav_master | Base | Entity+currency NAV and FX position history | nav_id, entity_id, currency_code, nav_type, position_fc, position_sgd | Analytics/Alloc | Cross-stage |
| position_nav_master_with_exposure | View | NAV master with exposure ccys (currency_code as exposure_currency) | nav_id, entity_id, exposure_currency, sfx_position, buffer_amount, nav_amount | Allocation, Analytics | 1A/1B |
| prompt_templates | Base | LLM agent prompt config/templates metadata | template_id, template_family, prompt_category, prompt_text, created_at | All Agents | Any |
| proxy_configuration | Base | Proxy/NDF support mapping and rules | config_id, proxy_ccy, mapped_ccy, active_flag | Booking/Analytics | 2 |
| risk_metrics | Base | Risk profile per instruction/event/currency | metric_id, event_id, currency_code, value, metric_type, as_of_ts | Analytics | Cross-stage |
| risk_monitoring | Base | Ongoing risk event/alert log | monitor_id, entity_id, currency_code, risk_flag, status, raised_at | Analytics | Cross-stage |
| stage_bundles | Base | Batch/event/GL package for multi-stage posting or workflow | bundle_id, bundle_type, member_ids, created_at, processed_flag | GL/Posting Agent | 3 |
| stage2_error_log | Base | Error/exception log for MX/booking | error_id, event_id, deal_sequence, error_type, retry_count, resolution_status | Booking Agent/Ops | 2 |
| system_configuration | Base | Global parameter store for features, error flags, runtime config | config_key, config_value, is_active, category | All Agents | Any |
| threshold_configuration | Base | Per-currency regulatory and business thresholds, buffer, PB, etc. | threshold_id, threshold_name, threshold_value, buffer_bps, effective_start | Allocation Agent | 1A |
| trade_history | Base | FX/NDF/SWAP trade execution log for analytics | trade_id, deal_id, ccy, amount_fc, exec_date, book_ref | Analytics | Cross-stage |
| usd_pb_deposit | Base | USD prime brokerage deposit/capacity as-of per entity/currency | deposit_id, entity_id, amount_usd, as_of_date, source | Allocation Agent | 1A |
| v_allocation_waterfall_summary | View | Visualizes allocation priority/order by entity/run (summary) | run_id, entity_id, currency_code, available_amount, allocated_amount | Allocation/Analytics | 1B |
| v_available_amounts_fast | View | Fast lookup for all available headroom per entity/currency | entity_id, entity_name, currency_code, available_amount, buffer_amount, last_updated | Allocation/Analytics | 1A/1B |
| v_available_amounts_test | View | QA/test version of the above for regression, sandboxing | same as v_available_amounts_fast (test data) | DevOps/QA | Any |
| v_ccy_to_usd | View | Real-time ccy→USD rates for PB, headroom, compliance analytics | currency_code, usd_rate, effective_date, rate_type | Allocation/Analytics | 1A |
| v_entity_capacity_complete | View | All-in capacity calc, overlays, buffer, eligibility per entity | entity_id, entity_name, currency_code, total_capacity, overlays_applied | Allocation/Analytics | 1A/1B |
| v_event_acked_deals | View | MX booking recon—actual booked/acked deals by event | event_id, booked_deal_count, missing_deals, mismatch_flags, last_booked_at | Booking Agent | 2 |
| v_event_acked_deals_new | View | Extended version of acked_deals view (richer event context) | event_id, deal_ids[], acked_status, booking_reference | Booking Agent/Analytics | 2/3 |
| v_event_expected_deals | View | All deals expected to book (not just acked) for full recon | event_id, model_type, expected_deal_count, expected_products, expected_portfolios | Booking Agent | 2 |
| v_gl_export_ready | View | All lines ready to export/post in GL | batch_id, journal_count, total_dr_sgd, total_cr_sgd, balanced_flag | GL/Posting Agent | 3 |
| v_hedge_instructions_fast | View | Fast-check for instruction status for live ops | instruction_id, msg_uid, instruction_type, status, currency_code, entity_id, created_at | Allocation Agent, Ops | 1A/1B |
| v_hedge_lifecycle_status | View | Shows lifecycle progress (instruction to event to (Book/GL)) | hedge_id, latest_stage, latest_status, last_event_id, last_deal_id | Analytics Agent, Ops | Any |
| v_hedge_positions_fast | View | Real-time (hedged/unhedged by ccy/entity) for dashboards/analytics | entity_id, currency_code, hedged_amount, unhedged_amount, as_of_date | Allocation/Analytics | 1A/1B |
| v_hi_actionable | View | Filtering actionable/in-flight instructions for agents/ops | instruction_id, entity_id, instruction_type, status, assigned_group, priority | Allocation, Ops, Analytics | 1A/1B |
| v_hi_today | View | All instructions created/modified today—fresh for ops | instruction_id, entity_id, status, date_submitted, last_action | Allocation, Booking, Analytics | 1A/1B |
| v_hstg_inbound_pending | View | MX inbound deals staging queue for booking flow | stg_id, event_id, instruction_id, status, payload, received_at | Booking Agent, Ops | 2 |
| v_hstg_outbound_queue | View | MX outbound deals/instructions staging queue | stg_id, event_id, instruction_id, status, payload, queued_at | Booking Agent, DevOps | 2 |
| v_overlay_alerts | View | Alerts for overlays/headroom across the system | alert_id, entity_id, currency_code, alert_type, message, raised_at | Ops/Analytics | Cross-stage |
| v_overlay_amounts_active | View | All overlays currently active | overlay_id, entity_id, currency_code, overlay_amount, reason, status | Ops, Risk, Analytics | Cross-stage |
| v_stage1a_overlay_lookup | View | Lookup overlays usable at 1A for debugging scenarios | overlay_id, nav_id, buffer_amount, overlay_applied | Allocation/QA | 1A |
| v_stage1a_to_1b_ready | View | Shows which instructions are staged for 1B (promotable to events) | instruction_id, eligibility_flag, reason_code, recommended_model, checks_passed | Allocation Agent, Ops | 1A/1B |
| v_stage2_ready_stage3 | View | Canonical source for GL posting—events fully reconciled and package ready | event_id, package_id, completeness_score, missing_fields, be_code_count, drcr_balance_ok | GL/Posting Agent | 3 |
| v_stage2_stuck | View | Watchlist for stuck/errored bookings; ops triage queue | event_id, error_code, error_message, age_minutes, retries, owner | GL/Posting Agent | 3 |
| v_usd_pb_capacity_check | View | Real-time USD PB capacity/utilization for eligibility/limits | entity_id, capacity_total, capacity_used, capacity_free, alerts, as_of_ts | Alloc/Analytics/Compliance | 1A |
| v_usd_pb_threshold | View | Current configured PB thresholds for all entities/ccy | threshold_name, threshold_value, buffer_bps, effective_start, effective_end | Allocation Agent, Compliance | 1A |
| waterfall_logic_configuration | Base | Entity/currency allocation priority/order | config_id, entity_type, currency_code, priority, rank_weight | Allocation Agent, Analytics | 1B |


