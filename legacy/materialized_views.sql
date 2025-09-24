-- =====================================================================
-- HAWK Agent Materialized Views for High-Performance Query Optimization
-- Based on 11 Core User Workflows
-- =====================================================================

-- Drop existing views if they exist
DROP MATERIALIZED VIEW IF EXISTS mv_hedge_instruction_validation_cache CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_available_amounts_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_deal_bookings_by_order CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_usd_pb_capacity_monitor CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_hedge_adjustments_summary CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_entity_currency_config CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_total_hedge_amounts CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_car_hedge_positions CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_maturity_analysis CASCADE;

-- =====================================================================
-- 1. HEDGE INSTRUCTION VALIDATION CACHE (Ultra High-Frequency)
-- Pre-computed validation rules for I, U, R, T instructions
-- Refresh: Every 15 minutes
-- =====================================================================

CREATE MATERIALIZED VIEW mv_hedge_instruction_validation_cache AS
SELECT 
    cc.currency_code,
    cc.currency_type,
    cc.hedging_instruments_available,
    cc.active_flag as currency_active,
    em.entity_id,
    em.entity_name,
    em.car_exemption_flag,
    em.entity_type,
    em.business_unit,
    em.country_code,
    tc.threshold_type,
    tc.warning_level,
    tc.critical_level,
    tc.maximum_limit,
    tc.monitoring_frequency,
    iec.instruction_type,
    iec.event_mapping,
    iec.validation_rules,
    iec.auto_approval_limit,
    CURRENT_TIMESTAMP as cache_updated_at
FROM currency_configuration cc
JOIN entity_master em ON em.currency_code = cc.currency_code 
JOIN threshold_configuration tc ON tc.currency_code = cc.currency_code
LEFT JOIN instruction_event_config iec ON iec.currency_code = cc.currency_code
WHERE cc.active_flag = 'Y' 
  AND em.active_flag = 'Y'
  AND tc.active_flag = 'Y';

-- Index for ultra-fast lookups
CREATE UNIQUE INDEX idx_mv_validation_cache_lookup 
ON mv_hedge_instruction_validation_cache (currency_code, entity_id, instruction_type);

CREATE INDEX idx_mv_validation_cache_currency 
ON mv_hedge_instruction_validation_cache (currency_code);

-- =====================================================================
-- 2. AVAILABLE AMOUNTS SUMMARY (Ultra High-Frequency)
-- Pre-calculated available hedge amounts per entity/currency
-- Refresh: Every 5 minutes
-- =====================================================================

CREATE MATERIALIZED VIEW mv_available_amounts_summary AS
WITH nav_positions AS (
    SELECT 
        pnm.entity_id,
        pnm.currency_code,
        pnm.nav_type,
        pnm.as_of_date,
        SUM(pnm.current_position) as total_sfx_position,
        SUM(pnm.coi_amount) as total_coi_amount,
        SUM(pnm.re_amount) as total_re_amount,
        SUM(pnm.buffer_amount) as total_buffer_amount,
        SUM(pnm.manual_overlay_amount) as total_overlay_amount
    FROM position_nav_master pnm
    WHERE pnm.as_of_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY pnm.entity_id, pnm.currency_code, pnm.nav_type, pnm.as_of_date
),
car_totals AS (
    SELECT 
        cm.entity_id,
        cm.currency_code,
        SUM(cm.car_amount) as total_car_amount
    FROM car_master cm
    WHERE cm.active_flag = 'Y'
    GROUP BY cm.entity_id, cm.currency_code
),
current_hedges AS (
    SELECT 
        hbe.entity_id,
        hi.exposure_currency as currency_code,
        SUM(hi.allocated_notional) as total_hedged_amount
    FROM hedge_instructions hi
    JOIN hedge_business_events hbe ON hi.instruction_id = hbe.instruction_id
    WHERE hi.instruction_status = 'Active'
      AND hbe.stage_2_status = 'Completed'
    GROUP BY hbe.entity_id, hi.exposure_currency
)
SELECT 
    np.entity_id,
    np.currency_code,
    np.nav_type,
    np.as_of_date,
    np.total_sfx_position,
    np.total_coi_amount,
    np.total_re_amount,
    np.total_buffer_amount,
    np.total_overlay_amount,
    COALESCE(ct.total_car_amount, 0) as total_car_amount,
    COALESCE(ch.total_hedged_amount, 0) as total_hedged_amount,
    -- Available Amount Calculation
    (np.total_sfx_position 
     - COALESCE(ct.total_car_amount, 0) 
     + np.total_overlay_amount 
     - np.total_buffer_amount 
     - COALESCE(ch.total_hedged_amount, 0)) as available_to_hedge,
    CURRENT_TIMESTAMP as cache_updated_at
FROM nav_positions np
LEFT JOIN car_totals ct ON np.entity_id = ct.entity_id AND np.currency_code = ct.currency_code
LEFT JOIN current_hedges ch ON np.entity_id = ch.entity_id AND np.currency_code = ch.currency_code
ORDER BY np.entity_id, np.currency_code, np.as_of_date DESC;

-- Indexes for high-speed lookups
CREATE INDEX idx_mv_available_amounts_entity_currency 
ON mv_available_amounts_summary (entity_id, currency_code);

CREATE INDEX idx_mv_available_amounts_date 
ON mv_available_amounts_summary (as_of_date DESC);

-- =====================================================================
-- 3. DEAL BOOKINGS BY ORDER (High-Frequency)
-- Pre-joined deal booking data for order tracking
-- Refresh: Every 10 minutes
-- =====================================================================

CREATE MATERIALIZED VIEW mv_deal_bookings_by_order AS
SELECT 
    hi.order_id,
    hi.sub_order_id,
    hi.instruction_type,
    hi.exposure_currency,
    hi.hedge_amount_order,
    hi.instruction_status,
    hi.check_status,
    hi.acknowledgement_status,
    hi.created_date as instruction_created,
    hbe.event_id,
    hbe.stage_2_status,
    hbe.event_type,
    hbe.entity_id,
    db.deal_booking_id,
    db.deal_sequence,
    db.deal_status,
    db.deal_type,
    db.sell_currency,
    db.buy_currency,
    db.sell_amount,
    db.buy_amount,
    db.fx_rate,
    db.trade_date,
    db.value_date,
    db.maturity_date,
    db.counterparty,
    db.portfolio,
    db.booking_reference,
    db.internal_reference,
    db.external_reference,
    db.system,
    db.product_type,
    -- Deal summary flags
    CASE WHEN db.deal_status = 'Completed' THEN 1 ELSE 0 END as deal_completed,
    CASE WHEN hbe.stage_2_status = 'Completed' THEN 1 ELSE 0 END as stage2_completed,
    CURRENT_TIMESTAMP as cache_updated_at
FROM hedge_instructions hi
JOIN hedge_business_events hbe ON hi.instruction_id = hbe.instruction_id
JOIN deal_bookings db ON hbe.event_id = db.event_id
WHERE hi.instruction_status IN ('Active', 'Pending', 'Processing')
ORDER BY hi.order_id, hi.sub_order_id, db.deal_sequence;

-- Indexes for order lookup
CREATE INDEX idx_mv_deal_bookings_order_lookup 
ON mv_deal_bookings_by_order (order_id, sub_order_id);

CREATE INDEX idx_mv_deal_bookings_status 
ON mv_deal_bookings_by_order (deal_status, stage_2_status);

-- =====================================================================
-- 4. USD PB CAPACITY MONITORING (Medium-Frequency)
-- Real-time threshold monitoring for USD PB deposits
-- Refresh: Every 30 minutes
-- =====================================================================

CREATE MATERIALIZED VIEW mv_usd_pb_capacity_monitor AS
WITH daily_deposits AS (
    SELECT 
        upd.entity_id,
        upd.measurement_date,
        upd.currency_code,
        SUM(upd.total_usd_pb_deposits) as total_deposits,
        AVG(upd.current_hedge_exposure) as avg_hedge_exposure,
        SUM(upd.pending_hedge_requests) as total_pending,
        AVG(upd.available_capacity) as avg_available_capacity,
        MAX(upd.threshold_warning) as warning_threshold,
        MAX(upd.threshold_critical) as critical_threshold,
        MAX(upd.threshold_maximum) as maximum_threshold,
        MAX(upd.breach_status) as current_breach_status,
        MAX(upd.utilization_percentage) as max_utilization,
        COUNT(*) as deposit_records
    FROM usd_pb_deposit upd
    WHERE upd.measurement_date >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY upd.entity_id, upd.measurement_date, upd.currency_code
)
SELECT 
    dd.entity_id,
    dd.measurement_date,
    dd.currency_code,
    dd.total_deposits,
    dd.avg_hedge_exposure,
    dd.total_pending,
    dd.avg_available_capacity,
    dd.warning_threshold,
    dd.critical_threshold,
    dd.maximum_threshold,
    dd.current_breach_status,
    dd.max_utilization,
    -- Capacity analysis
    (dd.maximum_threshold - dd.total_deposits) as remaining_capacity,
    CASE 
        WHEN dd.total_deposits >= dd.maximum_threshold THEN 'BREACH'
        WHEN dd.total_deposits >= dd.critical_threshold THEN 'CRITICAL'
        WHEN dd.total_deposits >= dd.warning_threshold THEN 'WARNING'
        ELSE 'NORMAL'
    END as threshold_status,
    -- Trend analysis (requires window functions)
    LAG(dd.total_deposits) OVER (PARTITION BY dd.entity_id ORDER BY dd.measurement_date) as prev_day_deposits,
    dd.total_deposits - LAG(dd.total_deposits) OVER (PARTITION BY dd.entity_id ORDER BY dd.measurement_date) as daily_change,
    CURRENT_TIMESTAMP as cache_updated_at
FROM daily_deposits dd
ORDER BY dd.entity_id, dd.measurement_date DESC;

-- Index for capacity monitoring
CREATE INDEX idx_mv_usd_pb_capacity_entity_date 
ON mv_usd_pb_capacity_monitor (entity_id, measurement_date DESC);

CREATE INDEX idx_mv_usd_pb_capacity_status 
ON mv_usd_pb_capacity_monitor (threshold_status, current_breach_status);

-- =====================================================================
-- 5. HEDGE ADJUSTMENTS SUMMARY (High-Frequency)
-- Pre-aggregated GL hedge adjustment entries by currency
-- Refresh: Every 60 minutes
-- =====================================================================

CREATE MATERIALIZED VIEW mv_hedge_adjustments_summary AS
WITH adjustment_entries AS (
    SELECT 
        gl.entity_id,
        gl.currency_code,
        gl.posting_date,
        gl.entry_type,
        gl.source_field as adjustment_type,
        gl.amount_sgd,
        gl.debit_account,
        gl.credit_account,
        CASE WHEN gl.amount_sgd > 0 THEN gl.amount_sgd ELSE 0 END as debit_amount,
        CASE WHEN gl.amount_sgd < 0 THEN ABS(gl.amount_sgd) ELSE 0 END as credit_amount
    FROM gl_entries gl
    WHERE gl.entry_type = 'HEDGE_ADJUSTMENT'
      AND gl.posting_date >= CURRENT_DATE - INTERVAL '90 days'
)
SELECT 
    ae.entity_id,
    ae.currency_code,
    ae.posting_date,
    ae.adjustment_type,
    COUNT(*) as total_entries,
    SUM(ae.debit_amount) as total_debits,
    SUM(ae.credit_amount) as total_credits,
    SUM(ae.amount_sgd) as net_adjustment,
    -- Monthly aggregation
    DATE_TRUNC('month', ae.posting_date) as adjustment_month,
    AVG(ae.amount_sgd) as avg_adjustment_amount,
    MIN(ae.posting_date) as first_adjustment_date,
    MAX(ae.posting_date) as last_adjustment_date,
    CURRENT_TIMESTAMP as cache_updated_at
FROM adjustment_entries ae
GROUP BY ae.entity_id, ae.currency_code, ae.posting_date, ae.adjustment_type
ORDER BY ae.entity_id, ae.currency_code, ae.posting_date DESC;

-- Index for hedge adjustments lookup
CREATE INDEX idx_mv_hedge_adjustments_currency_date 
ON mv_hedge_adjustments_summary (currency_code, posting_date DESC);

CREATE INDEX idx_mv_hedge_adjustments_entity 
ON mv_hedge_adjustments_summary (entity_id, adjustment_month DESC);

-- =====================================================================
-- 6. ENTITY CURRENCY CONFIGURATION CACHE (High-Frequency)
-- Pre-computed entity configuration by currency
-- Refresh: Every 4 hours
-- =====================================================================

CREATE MATERIALIZED VIEW mv_entity_currency_config AS
SELECT 
    em.entity_id,
    em.entity_name,
    em.entity_type,
    em.currency_code,
    em.business_unit,
    em.country_code,
    em.region,
    em.car_exemption_flag,
    em.regulatory_classification,
    cc.currency_type,
    cc.hedging_instruments_available,
    cc.threshold_monitoring_enabled,
    cc.auto_hedging_enabled,
    cc.risk_weight_category,
    hf.framework_name,
    hf.hedge_accounting_method,
    hf.effectiveness_testing_method,
    hf.documentation_requirements,
    -- Configuration flags
    CASE WHEN em.car_exemption_flag = 'Y' THEN true ELSE false END as is_car_exempt,
    CASE WHEN cc.auto_hedging_enabled = 'Y' THEN true ELSE false END as auto_hedge_allowed,
    CASE WHEN cc.threshold_monitoring_enabled = 'Y' THEN true ELSE false END as threshold_monitoring,
    CURRENT_TIMESTAMP as cache_updated_at
FROM entity_master em
JOIN currency_configuration cc ON em.currency_code = cc.currency_code
LEFT JOIN hedging_framework hf ON cc.framework_id = hf.framework_id
WHERE em.active_flag = 'Y' 
  AND cc.active_flag = 'Y'
ORDER BY em.entity_id, em.currency_code;

-- Index for entity-currency lookups
CREATE UNIQUE INDEX idx_mv_entity_currency_lookup 
ON mv_entity_currency_config (entity_id, currency_code);

CREATE INDEX idx_mv_entity_currency_config_currency 
ON mv_entity_currency_config (currency_code);

-- =====================================================================
-- 7. TOTAL HEDGE AMOUNTS BY CURRENCY (Medium-Frequency)
-- Pre-aggregated hedge totals for dashboard reporting
-- Refresh: Every 20 minutes
-- =====================================================================

CREATE MATERIALIZED VIEW mv_total_hedge_amounts AS
WITH active_hedges AS (
    SELECT 
        hi.exposure_currency as currency_code,
        hbe.entity_id,
        hi.instruction_type,
        hi.hedge_method,
        SUM(hi.allocated_notional) as total_notional,
        SUM(hi.response_notional) as total_response,
        COUNT(*) as hedge_count,
        MIN(hi.instruction_date) as first_hedge_date,
        MAX(hi.instruction_date) as last_hedge_date
    FROM hedge_instructions hi
    JOIN hedge_business_events hbe ON hi.instruction_id = hbe.instruction_id
    WHERE hi.instruction_status = 'Active'
      AND hbe.stage_2_status = 'Completed'
    GROUP BY hi.exposure_currency, hbe.entity_id, hi.instruction_type, hi.hedge_method
),
maturity_analysis AS (
    SELECT 
        db.buy_currency as currency_code,
        hbe.entity_id,
        COUNT(*) as deals_by_maturity,
        SUM(db.buy_amount) as total_amount_by_maturity,
        DATE_TRUNC('month', db.maturity_date) as maturity_month
    FROM deal_bookings db
    JOIN hedge_business_events hbe ON db.event_id = hbe.event_id
    WHERE db.deal_status = 'Active'
      AND db.maturity_date >= CURRENT_DATE
    GROUP BY db.buy_currency, hbe.entity_id, DATE_TRUNC('month', db.maturity_date)
)
SELECT 
    ah.currency_code,
    ah.entity_id,
    ah.instruction_type,
    ah.hedge_method,
    ah.total_notional,
    ah.total_response,
    ah.hedge_count,
    ah.first_hedge_date,
    ah.last_hedge_date,
    -- Maturity breakdown
    COALESCE(ma.deals_by_maturity, 0) as deals_maturing,
    COALESCE(ma.total_amount_by_maturity, 0) as amount_maturing,
    ma.maturity_month,
    -- Hedge utilization
    ROUND((ah.total_notional / NULLIF(ah.total_response, 0)) * 100, 2) as utilization_percentage,
    CURRENT_TIMESTAMP as cache_updated_at
FROM active_hedges ah
LEFT JOIN maturity_analysis ma ON ah.currency_code = ma.currency_code 
                               AND ah.entity_id = ma.entity_id
ORDER BY ah.currency_code, ah.entity_id, ah.hedge_method;

-- Index for total hedge amounts
CREATE INDEX idx_mv_total_hedge_amounts_currency 
ON mv_total_hedge_amounts (currency_code, entity_id);

CREATE INDEX idx_mv_total_hedge_amounts_maturity 
ON mv_total_hedge_amounts (maturity_month);

-- =====================================================================
-- 8. CAR HEDGE POSITIONS (Medium-Frequency)  
-- Optimal CAR hedge calculations and current positions
-- Refresh: Every 2 hours
-- =====================================================================

CREATE MATERIALIZED VIEW mv_car_hedge_positions AS
WITH car_positions AS (
    SELECT 
        cm.entity_id,
        cm.currency_code,
        cm.car_amount,
        cm.optimal_car_amount,
        cm.car_utilization_percentage,
        cm.last_calculation_date,
        pnm.current_position as nav_position,
        pnm.coi_amount,
        pnm.re_amount
    FROM car_master cm
    LEFT JOIN position_nav_master pnm ON cm.entity_id = pnm.entity_id 
                                      AND cm.currency_code = pnm.currency_code
                                      AND pnm.as_of_date = CURRENT_DATE
    WHERE cm.active_flag = 'Y'
),
hedge_coverage AS (
    SELECT 
        hbe.entity_id,
        hi.exposure_currency as currency_code,
        SUM(CASE WHEN hi.hedge_method = 'CAR' THEN hi.allocated_notional ELSE 0 END) as car_hedged_amount,
        SUM(hi.allocated_notional) as total_hedged_amount
    FROM hedge_instructions hi
    JOIN hedge_business_events hbe ON hi.instruction_id = hbe.instruction_id
    WHERE hi.instruction_status = 'Active'
      AND hbe.stage_2_status = 'Completed'
    GROUP BY hbe.entity_id, hi.exposure_currency
)
SELECT 
    cp.entity_id,
    cp.currency_code,
    cp.car_amount,
    cp.optimal_car_amount,
    cp.car_utilization_percentage,
    cp.nav_position,
    cp.coi_amount,
    cp.re_amount,
    COALESCE(hc.car_hedged_amount, 0) as car_hedged_amount,
    COALESCE(hc.total_hedged_amount, 0) as total_hedged_amount,
    -- Calculations
    (cp.optimal_car_amount - COALESCE(hc.car_hedged_amount, 0)) as car_hedge_gap,
    (cp.nav_position - COALESCE(hc.total_hedged_amount, 0)) as unhedged_amount,
    ROUND((COALESCE(hc.car_hedged_amount, 0) / NULLIF(cp.optimal_car_amount, 0)) * 100, 2) as car_hedge_coverage_pct,
    CASE 
        WHEN cp.optimal_car_amount - COALESCE(hc.car_hedged_amount, 0) > 1000000 THEN 'HIGH'
        WHEN cp.optimal_car_amount - COALESCE(hc.car_hedged_amount, 0) > 100000 THEN 'MEDIUM'
        ELSE 'LOW'
    END as hedge_gap_priority,
    CURRENT_TIMESTAMP as cache_updated_at
FROM car_positions cp
LEFT JOIN hedge_coverage hc ON cp.entity_id = hc.entity_id 
                            AND cp.currency_code = hc.currency_code
ORDER BY cp.entity_id, cp.currency_code;

-- Index for CAR hedge positions
CREATE INDEX idx_mv_car_hedge_positions_entity 
ON mv_car_hedge_positions (entity_id, currency_code);

CREATE INDEX idx_mv_car_hedge_positions_gap 
ON mv_car_hedge_positions (hedge_gap_priority, car_hedge_gap DESC);

-- =====================================================================
-- 9. MATURITY ANALYSIS (Lower-Frequency)
-- Hedge maturity analysis for rolling hedge planning
-- Refresh: Every 4 hours
-- =====================================================================

CREATE MATERIALIZED VIEW mv_maturity_analysis AS
WITH maturity_buckets AS (
    SELECT 
        db.buy_currency as currency_code,
        hbe.entity_id,
        db.maturity_date,
        db.buy_amount,
        CASE 
            WHEN db.maturity_date <= CURRENT_DATE + INTERVAL '30 days' THEN '0-30 days'
            WHEN db.maturity_date <= CURRENT_DATE + INTERVAL '90 days' THEN '31-90 days'
            WHEN db.maturity_date <= CURRENT_DATE + INTERVAL '180 days' THEN '91-180 days'
            WHEN db.maturity_date <= CURRENT_DATE + INTERVAL '365 days' THEN '181-365 days'
            ELSE 'Over 1 year'
        END as maturity_bucket,
        DATE_TRUNC('month', db.maturity_date) as maturity_month,
        EXTRACT(YEAR FROM db.maturity_date) as maturity_year
    FROM deal_bookings db
    JOIN hedge_business_events hbe ON db.event_id = hbe.event_id
    JOIN hedge_instructions hi ON hbe.instruction_id = hi.instruction_id
    WHERE db.deal_status = 'Active'
      AND db.maturity_date >= CURRENT_DATE
      AND hi.instruction_status = 'Active'
)
SELECT 
    mb.currency_code,
    mb.entity_id,
    mb.maturity_bucket,
    mb.maturity_month,
    mb.maturity_year,
    COUNT(*) as deal_count,
    SUM(mb.buy_amount) as total_amount,
    AVG(mb.buy_amount) as avg_deal_size,
    MIN(mb.maturity_date) as earliest_maturity,
    MAX(mb.maturity_date) as latest_maturity,
    -- Rolling analysis
    SUM(SUM(mb.buy_amount)) OVER (
        PARTITION BY mb.currency_code, mb.entity_id 
        ORDER BY mb.maturity_month 
        ROWS UNBOUNDED PRECEDING
    ) as cumulative_amount,
    -- Priority scoring for rolling
    CASE 
        WHEN mb.maturity_bucket = '0-30 days' THEN 5
        WHEN mb.maturity_bucket = '31-90 days' THEN 4
        WHEN mb.maturity_bucket = '91-180 days' THEN 3
        WHEN mb.maturity_bucket = '181-365 days' THEN 2
        ELSE 1
    END as rolling_priority,
    CURRENT_TIMESTAMP as cache_updated_at
FROM maturity_buckets mb
GROUP BY mb.currency_code, mb.entity_id, mb.maturity_bucket, mb.maturity_month, mb.maturity_year
ORDER BY mb.currency_code, mb.entity_id, mb.maturity_month;

-- Index for maturity analysis
CREATE INDEX idx_mv_maturity_analysis_currency_bucket 
ON mv_maturity_analysis (currency_code, maturity_bucket);

CREATE INDEX idx_mv_maturity_analysis_priority 
ON mv_maturity_analysis (rolling_priority DESC, total_amount DESC);

-- =====================================================================
-- REFRESH SCHEDULE SETUP (PostgreSQL Cron Extension)
-- =====================================================================

-- Enable pg_cron if available
-- CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Ultra high-frequency refreshes (every 5 minutes)
-- SELECT cron.schedule('refresh_hedge_validation', '*/5 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hedge_instruction_validation_cache;');
-- SELECT cron.schedule('refresh_available_amounts', '*/5 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_available_amounts_summary;');

-- High-frequency refreshes (every 10-15 minutes)
-- SELECT cron.schedule('refresh_deal_bookings', '*/10 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_deal_bookings_by_order;');
-- SELECT cron.schedule('refresh_total_hedge_amounts', '*/20 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_total_hedge_amounts;');

-- Medium-frequency refreshes (every 30-60 minutes)
-- SELECT cron.schedule('refresh_usd_pb_capacity', '*/30 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_usd_pb_capacity_monitor;');
-- SELECT cron.schedule('refresh_hedge_adjustments', '0 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hedge_adjustments_summary;');

-- Lower-frequency refreshes (every 2-4 hours)
-- SELECT cron.schedule('refresh_car_hedge_positions', '0 */2 * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_car_hedge_positions;');
-- SELECT cron.schedule('refresh_entity_currency_config', '0 */4 * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_entity_currency_config;');
-- SELECT cron.schedule('refresh_maturity_analysis', '0 */4 * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY mv_maturity_analysis;');

-- =====================================================================
-- MANUAL REFRESH FUNCTIONS FOR IMMEDIATE UPDATES
-- =====================================================================

CREATE OR REPLACE FUNCTION refresh_critical_caches()
RETURNS TEXT AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hedge_instruction_validation_cache;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_available_amounts_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_deal_bookings_by_order;
    
    RETURN 'Critical caches refreshed successfully at ' || CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION refresh_all_hawk_caches()
RETURNS TEXT AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hedge_instruction_validation_cache;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_available_amounts_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_deal_bookings_by_order;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_usd_pb_capacity_monitor;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_hedge_adjustments_summary;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_entity_currency_config;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_total_hedge_amounts;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_car_hedge_positions;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_maturity_analysis;
    
    RETURN 'All HAWK materialized views refreshed successfully at ' || CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- PERFORMANCE MONITORING
-- =====================================================================

CREATE OR REPLACE VIEW v_materialized_view_stats AS
SELECT 
    schemaname,
    matviewname,
    matviewowner,
    tablespace,
    hasindexes,
    ispopulated,
    definition
FROM pg_matviews 
WHERE matviewname LIKE 'mv_%'
ORDER BY matviewname;

-- Comments for documentation
COMMENT ON MATERIALIZED VIEW mv_hedge_instruction_validation_cache IS 'Ultra high-frequency cache for hedge instruction validation (refresh every 5 min)';
COMMENT ON MATERIALIZED VIEW mv_available_amounts_summary IS 'Ultra high-frequency cache for available hedge amount calculations (refresh every 5 min)';
COMMENT ON MATERIALIZED VIEW mv_deal_bookings_by_order IS 'High-frequency cache for deal booking lookups by order ID (refresh every 10 min)';
COMMENT ON MATERIALIZED VIEW mv_usd_pb_capacity_monitor IS 'Medium-frequency cache for USD PB deposit capacity monitoring (refresh every 30 min)';
COMMENT ON MATERIALIZED VIEW mv_hedge_adjustments_summary IS 'High-frequency cache for GL hedge adjustment analysis (refresh every 60 min)';
COMMENT ON MATERIALIZED VIEW mv_entity_currency_config IS 'Configuration cache for entity-currency lookup (refresh every 4 hours)';
COMMENT ON MATERIALIZED VIEW mv_total_hedge_amounts IS 'Medium-frequency cache for total hedge amount reporting (refresh every 20 min)';
COMMENT ON MATERIALIZED VIEW mv_car_hedge_positions IS 'Medium-frequency cache for CAR hedge position analysis (refresh every 2 hours)';
COMMENT ON MATERIALIZED VIEW mv_maturity_analysis IS 'Lower-frequency cache for hedge maturity and rolling analysis (refresh every 4 hours)';

-- Initial population of all materialized views
SELECT refresh_all_hawk_caches();