import asyncio
import json
import sys
from typing import Optional

import httpx


BACKEND_URL = "http://localhost:8004"


async def stream_prompt(
    user_prompt: str,
    template_category: Optional[str] = None,
    currency: Optional[str] = None,
    amount: Optional[float] = None,
    transaction_date: Optional[str] = None,
):
    url = f"{BACKEND_URL}/hawk-agent/process-prompt"
    payload = {
        "user_prompt": user_prompt,
        "template_category": template_category,
        "currency": currency,
        "amount": amount,
        "transaction_date": transaction_date,
        "use_cache": True,
    }
    # Remove None entries for cleanliness
    payload = {k: v for k, v in payload.items() if v is not None}

    print("POST", url)
    print("Payload:", json.dumps(payload))

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
        ) as resp:
            print("Status:", resp.status_code)
            if resp.status_code != 200:
                print("Body:", await resp.aread())
                return

            print("--- Streaming ---")
            async for line in resp.aiter_lines():
                if not line:
                    continue
                print(line)


async def get_status():
    url = f"{BACKEND_URL}/system/status"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url)
        print("GET", url, r.status_code)
        print(r.text)


async def main():
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        await get_status()
        return

    # Default sample: HKD utilization
    await stream_prompt(
        user_prompt="Check HKD hedge capacity",
        template_category="hedge_accounting",
        currency="HKD",
        amount=50000,
        transaction_date="2025-09-04",
    )


if __name__ == "__main__":
    asyncio.run(main())

