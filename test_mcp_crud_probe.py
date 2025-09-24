import os
import asyncio
import json
from datetime import datetime

os.environ.setdefault("PYTHONUNBUFFERED", "1")

from shared.hedge_processor import hedge_processor


async def main():
    print("== MCP CRUD Probe ==")
    await hedge_processor.initialize()

    summary = {"select": None, "write_instruction": None, "amend_instruction": None,
               "insert_allocation": None, "amend_allocation": None, "insert_event": None}

    # 1) SELECT probe
    sel = await hedge_processor.query_supabase_direct(
        table_name="entity_master",
        operation="select",
        limit=1
    )
    print("SELECT entity_master ->", json.dumps(sel, indent=2, default=str)[:500])
    summary["select"] = sel.get("status")

    # Pick a valid entity_id for FK-safe inserts
    entity_id_fk = None
    try:
        if sel.get("status") == "success" and sel.get("records"):
            entity_id_fk = (sel.get("data") or [{}])[0].get("entity_id")
    except Exception:
        entity_id_fk = None

    # Stop early if DB not connected
    if sel.get("status") != "success":
        print("Supabase connection not available; aborting write tests.")
        await hedge_processor.cleanup()
        return

    # 2) WRITE inception via process_hedge_prompt (ensure uniqueness via msg_uid)
    poc_msg_uid = f"POC_{int(datetime.now().timestamp())}"
    write = await hedge_processor.universal_prompt_processor(
        user_prompt="Create a new USD hedge for 1M",
        currency="USD",
        amount=1_000_000,
        operation_type="write",
        write_data={
            "target_table": "hedge_instructions",
            "msg_uid": poc_msg_uid,
            "order_id": f"ORD_{poc_msg_uid}"
        }
    )
    print("WRITE hedge_instructions ->", json.dumps(write, indent=2, default=str)[:500])
    wi = (write.get("write_results") or {}).get("details", {}).get("hedge_instructions")
    instruction_id = wi.get("instruction_id") if wi else None
    summary["write_instruction"] = "ok" if instruction_id else "missing_id"

    # 3) AMEND instruction
    if instruction_id:
        amend = await hedge_processor.universal_prompt_processor(
            user_prompt="Amend instruction amount",
            operation_type="amend",
            instruction_id=instruction_id,
            write_data={"hedge_amount_order": 1100000}
        )
        print("AMEND hedge_instructions ->", json.dumps(amend, indent=2, default=str)[:500])
        summary["amend_instruction"] = amend.get("status") or (amend.get("write_results") or {}).get("status")

    # 4) INSERT allocation via direct tool
    alloc_id = f"ALLOC_POC_{int(datetime.now().timestamp())}"
    ins_alloc = await hedge_processor.query_supabase_direct(
        table_name="allocation_engine",
        operation="insert",
        data={
            "allocation_id": alloc_id,
            "request_id": f"REQ_{alloc_id}",
            "entity_id": entity_id_fk,
            "currency_code": "USD",
            "nav_type": "COI",
            "sfx_position": 150000,
            "hedge_amount_allocation": 12345,
        }
    )
    print("INSERT allocation_engine ->", json.dumps(ins_alloc, indent=2, default=str)[:500])
    summary["insert_allocation"] = ins_alloc.get("status")

    # 5) AMEND allocation via process_hedge_prompt
    amend_alloc = await hedge_processor.universal_prompt_processor(
        user_prompt="Amend allocation status",
        operation_type="amend",
        write_data={
            "target_table": "allocation_engine",
            "allocation_id": alloc_id,
            "status": "Completed",
            "amount": 99999
        }
    )
    print("AMEND allocation_engine ->", json.dumps(amend_alloc, indent=2, default=str)[:500])
    summary["amend_allocation"] = amend_alloc.get("status") or (amend_alloc.get("write_results") or {}).get("status")

    # 6) INSERT hedge_business_events explicitly (link to instruction if available)
    # Ensure we have a valid instruction_id for event creation
    if not instruction_id:
        latest = await hedge_processor.query_supabase_direct(
            table_name="hedge_instructions",
            operation="select",
            limit=1,
            order_by='-created_date'
        )
        if latest.get("status") == "success" and latest.get("records"):
            instruction_id = (latest.get("data") or [{}])[0].get("instruction_id")

    evt = await hedge_processor.universal_prompt_processor(
        user_prompt="Create event",
        operation_type="write",
        write_data={
            "target_table": "hedge_business_events",
            "instruction_id": instruction_id,
            "event_status": "Pending",
            "business_event_type": "Initiation"
        }
    )
    print("INSERT hedge_business_events ->", json.dumps(evt, indent=2, default=str)[:500])
    summary["insert_event"] = evt.get("status") or (evt.get("write_results") or {}).get("status")

    print("\n== Summary ==\n", json.dumps(summary, indent=2, default=str))

    await hedge_processor.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
