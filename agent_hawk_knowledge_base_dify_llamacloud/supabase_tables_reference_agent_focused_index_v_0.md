# Supabase Tables & Views — Agent-Focused Index (v0.2)

> Full index covering **all 78 objects** from the schema export, aligned to HAWK KB (Stages 1A→3). Purpose and key columns prioritized for agent workflows.

| Table Name | Table Type (View/Base/Materialized) | Key Purpose | Key Columns | Agent | Stage |
| --- | --- | --- | --- | --- | --- |
| allocation_engine | Base | Stage-1B allocation decisions and headroom math per entity/currency | allocation_id, request_id, entity_id, currency_code, nav_type, sfx_position | Booking Agent | Stage 1B/2 |
| audit_trail | Base | Operational audit trail records | audit_id, trace_id, transaction_id, msg_uid, stage, process_step | Analytics Agent | Cross-stage |
| buffer_configuration | Base | Core operational table supporting HAWK stages | buffer_rule_id, entity_id, currency_code, hedging_framework, car_exemption_flag, entity_type | Analytics Agent | Cross-stage |
| capacity_overrides | Base | Core operational table supporting HAWK stages | override_id, entity_id, currency_code, capacity_override, effective_start, effective_end | Analytics Agent | Cross-stage |
| car_parameters | Base | Core operational table supporting HAWK stages | car_param_id, entity_id, currency_code, car_ratio, method, effective_start | Analytics Agent | Cross-stage |
| car_thresholds | Base | Core operational table supporting HAWK stages | threshold_id, entity_id, currency_code, lower_bound, upper_bound, effective_start | Analytics Agent | Cross-stage |
| currency_configuration | Base | Per-currency model settings: matched/mismatched/proxy; limits | currency_code, currency_type, ndf_supported, onshore_symbol, offshore_symbol, pb_deposit_required | Allocation Agent | Stage 1A |
| currency_rate_pairs | Base | Pair metadata and valid cross mappings | pair_code, base_ccy, quote_ccy, precision, invertible, active_flag | Allocation Agent | Stage 1A |
| currency_rates | Base | Prevailing/historical FX rates with onshore/offshore flags | from_ccy, to_ccy, rate, as_of_ts, source, is_onshore | Allocation Agent | Stage 1A |
| deal_bookings | Base | Booked spot/swap/NDF deals; references for GL packaging | deal_id, event_id, product_code, trade_ref, near_leg_date, far_leg_date | Booking Agent | Stage 1B/2 |
| deal_bookings_archive | Base | Historical archive for analytics and audit lineage | deal_id, event_id, product_code, trade_ref, near_leg_date, far_leg_date | Analytics Agent | Cross-stage |
| entity_master | Base | Entity registry and effective-dated attributes for checks/mapping | entity_id, entity_name, entity_type, country_code, status, parent_entity_id | Allocation Agent | Stage 1A |
| entity_threshold_configuration | Base | Core operational table supporting HAWK stages | config_id, entity_id, currency_code, threshold_name, threshold_value, effective_start | Analytics Agent | Cross-stage |
| fx_proxy_parameters | Base | Core operational table supporting HAWK stages | proxy_param_id, proxy_ccy, ndf_forward_curve, embedded_spot_flag, usd_funding_required | Booking Agent | Stage 2 |
| gl_be_narrative_templates | Base | Core operational table supporting HAWK stages | template_id, be_code, narrative_template, status, effective_start | GL/Posting Agent | Stage 3 |
| gl_entries | Base | GL journal lines (DR/CR) constructed for posting | entry_id, package_id, be_code, dr_account, cr_account, dr_amount_sgd | GL/Posting Agent | Stage 3 |
| gl_entries_detail | Base | Field-level breakdown of calculations per GL line for audit | detail_id, entry_id, field_name, field_value, calc_method, created_at | GL/Posting Agent | Stage 3 |
| gl_journal_lines | Base | Final GL payload lines assembled for export/posting | journal_id, batch_id, line_seq, account, amount_sgd, currency | GL/Posting Agent | Stage 3 |
| gl_posting_queue | Base | Queue/state for GL export/posting workflow | queue_id, batch_id, status, attempts, last_error_code, last_error_message | GL/Posting Agent | Stage 3 |
| hawk_kpis_daily | Base | Core operational table supporting HAWK stages | snapshot_date, stage, total_events, success_count, failure_count, avg_latency_ms | Analytics Agent | Cross-stage |
| hawk_processing_messages | Base | Core operational table supporting HAWK stages | msg_uid, stage, payload_type, payload_ref, status, error_code | Analytics Agent | Cross-stage |
| hedge_audit_trail | Base | Audit trail of posting lifecycle actions and outcomes | audit_id, entry_id, action, actor_id, timestamp, message | GL/Posting Agent | Stage 3 |
| hedge_be_config | Base | Stage-3 BE→GL mapping: accounts, narratives, PCs, BU | be_code, product_code, event_type, gl_account, narrative_template | GL/Posting Agent | Stage 3 |
| hedge_business_events | Base | Approved, normalized hedge events for booking orchestration | event_id, instruction_id, entity_id, currency_code, nav_type, model_type | Booking Agent | Stage 1B/2 |
| hedge_gl_packages | Base | Stage-2→3 GL package headers (batch metadata) | package_id, event_id, model_type, entity_id, status, created_timestamp | GL/Posting Agent | Stage 3 |
| hedge_instructions | Base | Front-office hedge asks; seed Stage-1A checks and 1B events | instruction_id, msg_uid, instruction_type, instruction_date, exposure_currency | Allocation Agent | Stage 1A |
| hedge_instructions_archive | Base | Historical archive for analytics and audit lineage | instruction_id, msg_uid, instruction_type, instruction_date, exposure_currency | Analytics Agent | Cross-stage |
| instruction_event_config | Base | Rules to transform instructions→events; model assignment | config_id, instruction_type, nav_type, currency_type, model_map, approvals_required | Booking Agent | Stage 1B/2 |
| murex_book_config | Base | Booking templates and routing for Murex/INSTC per model/product | config_id, model_type, product_code, portfolio_flow, booking_template | Booking Agent | Stage 2 |
| mx_proxy_hedge_report | Base | Derived reporting table for diagnostics/KPIs | report_id, event_id, proxy_ccy, ndf_forward_rate, embedded_spot_rate | Booking Agent | Stage 2 |
| overlay_configuration | Base | Core operational table supporting HAWK stages | overlay_id, entity_id, currency_code, overlay_amount, reason_code, effective_start | Analytics Agent | Cross-stage |
| position_nav_master | Base | Core operational table supporting HAWK stages | nav_id, entity_id, currency_code, nav_type, position_fc, position_sgd | Analytics Agent | Cross-stage |
| posting_batch_master | Base | Core operational table supporting HAWK stages | batch_id, created_at, created_by, status, total_dr_sgd, total_cr_sgd | GL/Posting Agent | Stage 3 |
| ps_gl_month_end_rates | Base | Core operational table supporting HAWK stages | rate_date, currency_code, blended_rate, source, notes | GL/Posting Agent | Stage 3 |
| rate_history | Base | Core operational table supporting HAWK stages | rate_date, from_ccy, to_ccy, rate, source | Allocation Agent | Stage 1A |
| rate_staging | Base | Core operational table supporting HAWK stages | load_id, from_ccy, to_ccy, rate, as_of_ts, source | Allocation Agent | Stage 1A |
| threshold_configuration | Base | Core operational table supporting HAWK stages | threshold_id, threshold_name, threshold_value, buffer_bps, effective_start | Allocation Agent | Stage 1A |
| usd_pb_deposits | Base | Core operational table supporting HAWK stages | deposit_id, entity_id, amount_usd, as_of_date, source | Allocation Agent | Stage 1A |
| v_event_acked_deals | View | Acknowledged/booked deals vs expectation | event_id, booked_deal_count, missing_deals, mismatch_flags, last_booked_at | Booking Agent | Stage 1B/2 |
| v_event_expected_deals | View | Expected booking legs per event/model | event_id, model_type, expected_deal_count, expected_products, expected_portfolios | Booking Agent | Stage 1B/2 |
| v_gl_export_ready | View | Entries ready to export/post to GL | batch_id, journal_count, total_dr_sgd, total_cr_sgd, balanced_flag | GL/Posting Agent | Stage 3 |
| v_hedge_lifecycle_status | View | End-to-end status per hedge across stages | hedge_id, latest_stage, latest_status, last_event_id, last_deal_id | Analytics Agent | Cross-stage |
| v_hedge_positions_fast | View | Fast position snapshot for dashboards | hedge_id, entity_id, currency_code, position_fc, position_sgd, pnl_sgd | Analytics Agent | Cross-stage |
| v_overlay_alerts | View | Operational alerts from overlay logic | alert_id, entity_id, currency_code, severity, alert_type, message | Analytics Agent | Cross-stage |
| v_overlay_amounts_active | View | Active overlay amounts per entity/currency | entity_id, currency_code, overlay_amount, reason_code, effective_start | Analytics Agent | Cross-stage |
| v_stage1a_overlay_lookup | View | Overlay of capacity/thresholds for 1A quick checks | entity_id, currency_code, capacity_total, capacity_used, headroom, threshold_name | Allocation Agent | Stage 1A |
| v_stage1a_to_1b_ready | View | Eligibility view to promote instructions to events | instruction_id, eligibility_flag, reason_code, recommended_model, checks_passed | Allocation Agent | Stage 1A |
| v_stage2_ready_stage3 | View | GL package readiness status | event_id, package_id, completeness_score, missing_fields, be_code_count, drcr_balance_ok | GL/Posting Agent | Stage 3 |
| v_stage2_stuck | View | Stage-2 error/stall watchlist | event_id, error_code, error_message, age_minutes, retries, owner | GL/Posting Agent | Stage 3 |
| v_usd_pb_capacity_check | View | USD PB capacity status view (Stage-1A gating) | entity_id, capacity_total, capacity_used, capacity_free, alerts, as_of_ts | Allocation Agent | Stage 1A |
| v_usd_pb_threshold | View | USD PB deposit threshold view (Stage-1A gating) | threshold_name, threshold_value, buffer_bps, effective_start, effective_end | Allocation Agent | Stage 1A |

> If any object is mis-classified, highlight it and I’ll re-tag Agent/Stage based on your KB references.
