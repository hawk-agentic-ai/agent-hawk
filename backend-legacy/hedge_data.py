from collections import defaultdict
from datetime import date
from app.services.supabase_client import get_supabase

def fetch_complete_hedge_data(
    instruction_type: str,
    exposure_currency: str,
    hedge_method: str,
    hedge_amount_order: float,
    order_id: str = None,
    nav_type: str = None,
    currency_type: str = None,
    reference_hedge_id: str = None
):
    """
    Optimized function to fetch data based on the instruction type.
    
    - 'U' fetches only Stage 1A data.
    - 'I' fetches data for the full pipeline (1A, 1B, 2).
    - 'R' and 'T' fetches data for Stage 1B and Stage 2.
    """
    supabase = get_supabase()
    today = date.today().isoformat()
    
    fetched_data = {}

    try:
        # --- Step 1: Core Entity and Position Data Queries (Needed for all types) ---
        entities_query = (
            supabase.table("entity_master")
            .select("*, currency_configuration!inner(currency_type)")
            .eq("currency_code", exposure_currency)
        )
        if currency_type:
            entities_query = entities_query.eq("currency_configuration.currency_type", currency_type)

        positions_query = (
            supabase.table("position_nav_master")
            .select("*")
            .eq("currency_code", exposure_currency)
        )
        if nav_type:
            positions_query = positions_query.eq("nav_type", nav_type)
        
        entities = entities_query.execute()
        positions = positions_query.execute()
        fetched_data["entities_rows"] = getattr(entities, "data", []) or []
        fetched_data["positions_rows"] = getattr(positions, "data", []) or []
        entity_ids = {e["entity_id"] for e in fetched_data["entities_rows"]} or {
            p["entity_id"] for p in fetched_data["positions_rows"]
        }
        
        # --- Step 2: Fetch data based on Instruction Type for efficiency ---
        if instruction_type in ["I", "U"]:
            # For new hedges or checks, focus is on Stage 1A
            fetched_data["buffer_config_rows"] = supabase.table("buffer_configuration").select("*").eq("currency_code", exposure_currency).eq("active_flag", "Y").execute().data or []
            fetched_data["waterfall_config_rows"] = supabase.table("waterfall_logic_configuration").select("*").eq("active_flag", "Y").order("waterfall_type").order("priority_level").execute().data or []
            fetched_data["hedging_framework_rows"] = supabase.table("hedging_framework").select("*").eq("currency_code", exposure_currency).eq("active_flag", "Y").execute().data or []
            fetched_data["allocations_rows"] = supabase.table("allocation_engine").select("*").eq("currency_code", exposure_currency).order("created_date", desc=True).limit(100).execute().data or []
            fetched_data["car_master_rows"] = supabase.table("car_master").select("*").eq("currency_code", exposure_currency).order("reporting_date", desc=True).limit(10).execute().data or []
            fetched_data["system_config_rows"] = supabase.table("system_configuration").select("*").eq("active_flag", "Y").execute().data or []
            fetched_data["currency_config_rows"] = supabase.table("currency_configuration").select("*").or_(f"currency_code.eq.{exposure_currency},proxy_currency.eq.{exposure_currency}").execute().data or []
            fetched_data["currency_rates_rows"] = supabase.table("currency_rates").select("*").or_(f"currency_pair.eq.{exposure_currency}SGD,currency_pair.eq.SGD{exposure_currency}").order("effective_date", desc=True).limit(20).execute().data or []
            fetched_data["usd_pb_rows"] = supabase.table("usd_pb_deposit").select("*").order("measurement_date", desc=True).limit(10).execute().data or []
            
            if instruction_type == "I":
                # Only for Inception, fetch data for the full pipeline
                fetched_data["overlay_config_rows"] = supabase.table("overlay_configuration").select("*").eq("currency_code", exposure_currency).eq("active_flag", "Y").execute().data or []
                fetched_data["hedge_instructions_rows"] = supabase.table("hedge_instructions").select("*").eq("exposure_currency", exposure_currency).order("instruction_date", desc=True).limit(50).execute().data or []
                fetched_data["booking_model_config_rows"] = supabase.table("instruction_event_config").select("*").eq("instruction_event", "Initiation").eq("status", 1).execute().data or []
                fetched_data["murex_books_rows"] = supabase.table("murex_book_config").select("*").eq("active_flag", True).execute().data or []
                fetched_data["hedge_instruments_rows"] = supabase.table("hedge_instruments").select("*").eq("active_flag", "Y").lte("effective_date", today).order("effective_date", desc=True).limit(20).execute().data or []
                fetched_data["hedge_effectiveness_rows"] = supabase.table("hedge_effectiveness").select("*").eq("currency_code", exposure_currency).order("measurement_date", desc=True).limit(10).execute().data or []
                fetched_data["risk_monitoring_rows"] = supabase.table("risk_monitoring").select("*").eq("currency_code", exposure_currency).eq("resolution_status", "Open").order("measurement_timestamp", desc=True).limit(10).execute().data or []
                fetched_data["proxy_config_rows"] = supabase.table("proxy_configuration").select("*").eq("exposure_currency", exposure_currency).eq("active_flag", "Y").order("effective_date", desc=True).execute().data or []
            
        elif instruction_type in ["R", "T"]:
            # For Rollover/Termination, focus is on Stage 1B and Stage 2
            
            # Stage 1B data for existing hedges
            hedge_events_q = supabase.table("hedge_business_events").select("*").eq("exposure_currency", exposure_currency)
            if reference_hedge_id:
                hedge_events_q = hedge_events_q.eq("event_id", reference_hedge_id)
            fetched_data["hedge_events_rows"] = hedge_events_q.order("trade_date", desc=True).limit(50).execute().data or []
            
            # Reallocation and compliance data from previous allocations
            fetched_data["allocations_rows"] = supabase.table("allocation_engine").select("*").eq("currency_code", exposure_currency).order("created_date", desc=True).limit(100).execute().data or []
            fetched_data["waterfall_config_rows"] = supabase.table("waterfall_logic_configuration").select("*").eq("active_flag", "Y").order("waterfall_type").order("priority_level").execute().data or []
            fetched_data["car_master_rows"] = supabase.table("car_master").select("*").eq("currency_code", exposure_currency).order("reporting_date", desc=True).limit(10).execute().data or []
            
            # Stage 2 data for new bookings (rollover creates a new deal) or terminations
            fetched_data["booking_model_config_rows"] = supabase.table("instruction_event_config").select("*").eq("instruction_event", "Initiation").eq("status", 1).execute().data or []
            fetched_data["murex_books_rows"] = supabase.table("murex_book_config").select("*").eq("active_flag", True).execute().data or []
            fetched_data["hedge_instruments_rows"] = supabase.table("hedge_instruments").select("*").eq("active_flag", "Y").lte("effective_date", today).order("effective_date", desc=True).limit(20).execute().data or []
            fetched_data["hedge_effectiveness_rows"] = supabase.table("hedge_effectiveness").select("*").eq("currency_code", exposure_currency).order("measurement_date", desc=True).limit(10).execute().data or []

            # Additional rates for potential proxy/mismatched scenarios
            fetched_data["currency_rates_rows"] = supabase.table("currency_rates").select("*").or_(f"currency_pair.eq.{exposure_currency}SGD,currency_pair.eq.SGD{exposure_currency}").order("effective_date", desc=True).limit(20).execute().data or []
            fetched_data["proxy_config_rows"] = supabase.table("proxy_configuration").select("*").eq("exposure_currency", exposure_currency).eq("active_flag", "Y").order("effective_date", desc=True).execute().data or []
            
            fetched_data["system_config_rows"] = supabase.table("system_configuration").select("*").eq("active_flag", "Y").execute().data or []
            fetched_data["risk_monitoring_rows"] = supabase.table("risk_monitoring").select("*").eq("currency_code", exposure_currency).eq("resolution_status", "Open").order("measurement_timestamp", desc=True).limit(10).execute().data or []
        
        # --- Step 3: Data Processing and Structuring ---
        entity_info_lookup = {e.get("entity_id"): e for e in fetched_data.get("entities_rows", []) if e.get("entity_id")}
        allocation_lookup = defaultdict(list)
        for alloc in fetched_data.get("allocations_rows", []):
            eid = alloc.get("entity_id")
            if eid: allocation_lookup[eid].append(alloc)
        
        hedge_relationships = defaultdict(list)
        for event in fetched_data.get("hedge_events_rows", []):
            eid = event.get("entity_id")
            if eid: hedge_relationships[eid].append(event)
        
        framework_rules = {rule.get("entity_id"): rule for rule in fetched_data.get("hedging_framework_rows", [])}
        buffer_rules = {br.get("entity_id"): br for br in fetched_data.get("buffer_config_rows", [])}
        car_data = {car.get("entity_id"): car for car in fetched_data.get("car_master_rows", [])}
        
        grouped_entities = defaultdict(list)
        for pos in fetched_data.get("positions_rows", []):
            eid = pos.get("entity_id")
            if not eid: continue

            # Get the latest allocation for this entity
            latest_allocation = allocation_lookup.get(eid, [])[0] if allocation_lookup.get(eid) else {}

            # Placeholder for calculations, replace with actual logic
            computed_total_nav = float(pos.get("current_position", 0) or 0)
            optimal_car_amount = 0.0
            manual_overlay = 0.0
            
            hedging_state = calculate_complete_hedging_state(
                position=pos,
                allocation=latest_allocation,
                hedge_relationships=hedge_relationships.get(eid, []),
                framework_rule=framework_rules.get(eid, {}),
                buffer_rule=buffer_rules.get(eid, {}),
                car_info=car_data.get(eid, {})
            )
            
            grouped_entities[eid].append({
                "nav_type": pos.get("nav_type", ""),
                "current_position": pos.get("current_position", 0),
                "computed_total_nav": computed_total_nav,
                "optimal_car_amount": optimal_car_amount,
                "buffer_percentage": buffer_rules.get(eid, {}).get("buffer_percentage", 0),
                "buffer_amount": hedging_state.get("buffer_amount", 0.0),
                "manual_overlay": manual_overlay,
                "allocation_status": latest_allocation.get("allocation_status", "Not_Allocated"),
                "hedging_state": hedging_state,
                "allocation_data": allocation_lookup.get(eid, []),
                "hedge_relationships": hedge_relationships.get(eid, []),
                "framework_rule": framework_rules.get(eid, {}),
                "buffer_rule": buffer_rules.get(eid, {}),
                "car_data": car_data.get(eid, {})
            })
            
        entity_groups = []
        for eid, navs in grouped_entities.items():
            entity = entity_info_lookup.get(eid, {})
            entity_groups.append({
                "entity_id": eid,
                "entity_name": entity.get("entity_name", ""),
                "entity_type": entity.get("entity_type", ""),
                "exposure_currency": entity.get("currency_code", ""),
                "currency_type": entity.get("currency_configuration", {}).get("currency_type") if isinstance(entity.get("currency_configuration"), dict) else (entity.get("currency_configuration", [{}])[0].get("currency_type") if isinstance(entity.get("currency_configuration"), list) and entity.get("currency_configuration") else None),
                "car_exemption": entity.get("car_exemption_flag", ""),
                "parent_child_nav_link": False,  # Placeholder, add logic if needed
                "positions": navs
            })
            
        usd_pb_threshold = fetched_data.get("threshold_configuration", {}).get("warning_level", 150000) if "threshold_configuration" in fetched_data else 150000
        usd_pb_check = {
            "total_usd_equivalent": sum(float(row.get("total_usd_deposits", 0) or 0) for row in fetched_data.get("usd_pb_rows", [])),
            "threshold": usd_pb_threshold,
            "status": "PASS" if sum(float(row.get("total_usd_deposits", 0) or 0) for row in fetched_data.get("usd_pb_rows", [])) <= usd_pb_threshold else "FAIL",
        }

        # Convert the defaultdict to a list of all events
        all_hedge_events = [event for events_list in hedge_relationships.values() for event in events_list]

        return {
            "entity_groups": entity_groups,
            "stage_1a_config": {
                "buffer_configuration": fetched_data.get("buffer_config_rows", []),
                "waterfall_logic": {"opening": [w for w in fetched_data.get("waterfall_config_rows", []) if w.get("waterfall_type") == "Opening"], "closing": [w for w in fetched_data.get("waterfall_config_rows", []) if w.get("waterfall_type") == "Closing"]},
                "overlay_configuration": fetched_data.get("overlay_config_rows", []),
                "hedging_framework": fetched_data.get("hedging_framework_rows", []),
                "system_configuration": fetched_data.get("system_config_rows", []),
                "threshold_configuration": {"usd_pb_threshold": usd_pb_threshold, "usd_pb_check": usd_pb_check}
            },
            "stage_1b_data": {
                "current_allocations": fetched_data.get("allocations_rows", []),
                "hedge_instructions_history": fetched_data.get("hedge_instructions_rows", []),
                "active_hedge_events": all_hedge_events, # Changed from dict to list
                "car_master_data": fetched_data.get("car_master_rows", [])
            },
            "stage_2_config": {
                "booking_model_config": fetched_data.get("booking_model_config_rows", []),
                "murex_books": fetched_data.get("murex_books_rows", []),
                "hedge_instruments": fetched_data.get("hedge_instruments_rows", []),
                "hedge_effectiveness": fetched_data.get("hedge_effectiveness_rows", [])
            },
            "risk_monitoring": fetched_data.get("risk_monitoring_rows", []),
            "currency_configuration": fetched_data.get("currency_config_rows", []),
            "currency_rates": fetched_data.get("currency_rates_rows", []),
            "proxy_configuration": fetched_data.get("proxy_config_rows", []),
            "additional_rates": fetched_data.get("additional_rates_rows", [])
        }

    except Exception as e:
        return {"status": "error", "message": str(e), "body": {}}


def calculate_complete_hedging_state(position, allocation, hedge_relationships, framework_rule, buffer_rule, car_info):
    """Calculates comprehensive hedging state for an entity position"""
    current_position = float(position.get("current_position", 0) or 0)
    hedged_position = float(allocation.get("hedged_position", 0) or 0)
    
    # Placeholder calculations for new required fields
    available_for_hedging = max(0, current_position - hedged_position)
    calculated_available_amount = available_for_hedging # Simplified, can be more complex
    car_amount_distribution = 0.0 # Placeholder
    manual_overlay_amount = 0.0 # Placeholder
    framework_compliance = "Compliant" # Placeholder
    last_allocation_date = allocation.get("created_date")
    waterfall_priority = 1 # Placeholder
    allocation_sequence = 1 # Placeholder
    allocation_status = allocation.get("allocation_status", "Not_Allocated")
    buffer_percentage = buffer_rule.get("buffer_percentage", 0)
    buffer_amount = (current_position * (buffer_percentage / 100)) if current_position > 0 else 0.0

    if current_position > 0:
        hedge_utilization_pct = (hedged_position / current_position) * 100.0
    else:
        hedge_utilization_pct = 0.0

    if hedged_position >= current_position:
        hedging_status = "Fully_Hedged"
    elif hedged_position > 0:
        hedging_status = "Partially_Hedged"
    else:
        hedging_status = "Available"

    return {
        "already_hedged_amount": hedged_position,
        "hedge_utilization_pct": round(hedge_utilization_pct, 2),
        "hedging_status": hedging_status,
        "framework_type": framework_rule.get("framework_type", "Not_Defined"),
        "buffer_percentage": buffer_percentage,
        "car_exemption_flag": framework_rule.get("car_exemption_flag", "N"),
        "active_hedge_count": len(hedge_relationships),
        "total_hedge_notional": sum(float(h.get("notional_amount", 0) or 0) for h in hedge_relationships),
        "available_for_hedging": available_for_hedging,
        "calculated_available_amount": calculated_available_amount,
        "car_amount_distribution": car_amount_distribution,
        "manual_overlay_amount": manual_overlay_amount,
        "framework_compliance": framework_compliance,
        "last_allocation_date": last_allocation_date,
        "waterfall_priority": waterfall_priority,
        "allocation_sequence": allocation_sequence,
        "allocation_status": allocation_status,
        "buffer_amount": buffer_amount
    }
